# Verification and trust boundary

## Clean-checkout verification

Python 3.12 is used in CI.

The dependency-free correctness checks are:

```bash
python verify.py
python verify_exact_qasm_equivalence.py
python verify_linear_equivalence.py
python compute_qasm_depth.py original_vqe_8_4_10_100.qasm mapped_route.qasm
```

To regenerate the exact mapped QASM and run the secondary numerical unitary
regression:

```bash
python -m pip install -r requirements.txt
python build_and_verify_full_qasm.py route.json
```

The expected exact-checker headlines are:

```text
VERIFIED
EXACT_SYMBOLIC_EQUIVALENCE_VERIFIED
LINEAR_EQUIVALENCE_VERIFIED
```

## Authoritative correctness layers

### 1. Source/provenance check

`verify.py` and the build script compute the Git blob SHA-1 of
`original_vqe_8_4_10_100.qasm` and require
`cdcb957d2c8f9a9f25fa5a530b80d8b6e7bd8af5`.

`verify.py` derives the 71 ordered CX pairs from that source QASM and checks
that `benchmark.json` contains the same sequence. `benchmark.json` is therefore
not an unchecked alternate source of the logical CX program.

The hardware graph receives the same treatment. `source_sycamore_edges.json`
freezes Q-Synth's `platform == "sycamore"` edge list from
`src/qsynth/LayoutSynthesis/architecture.py` at the same repository commit;
the source file's Git blob SHA-1 is
`72e4729523db7d58bd4a2658399da590f83d1049`. `verify.py` requires the
54-vertex/88-edge set in `benchmark.json` to equal that pinned source snapshot
exactly before checking any route step.

### 2. Route-certificate check

`verify.py` independently reconstructs the ordinary per-logical-qubit CX
dependency DAG and greedily executes every currently ready/adjacent source CX
between the stored SWAP phases. The reconstructed schedule must equal
`route.json` exactly.

This proves the stored 13-SWAP route is legal for the pinned Q-Synth benchmark
and Sycamore topology under the frozen routing model.

### 3. Exact complete-circuit check

`verify_exact_qasm_equivalence.py` is the load-bearing full-circuit checker.

It never evaluates a gate angle. Instead it:

1. parses all source `u(...)` and CX operations;
2. builds one source-operation queue per logical qubit;
3. tracks which logical state is carried by each physical wire through every
   inserted SWAP;
4. requires each mapped `u(...)` to be the next source operation on that logical
   qubit with the same symbolic parameter expression;
5. requires each mapped CX to be simultaneously next on both source endpoint
   queues, with the same control/target direction;
6. checks every mapped CX/SWAP is a frozen hardware edge;
7. consumes all 136 source operations exactly once;
8. checks the mapped SWAP sequence and routed CX order against `route.json`;
9. checks the final logical-to-physical placement.

The invariant is that after each mapped operation, every occupied physical wire
contains exactly the logical state indicated by the tracked placement, with
the same source operations already applied on each logical wire. SWAPs only
change the placement relation. Gates on disjoint logical wires commute because
they act on disjoint tensor factors, so any interleaving consistent with all
per-logical queues represents the same source circuit. Thus the final mapped
circuit is exactly the source circuit embedded under the final placement.

No floating-point operation is part of this correctness oracle.

### 4. Independent GF(2) cross-check

`verify_linear_equivalence.py` independently interprets the CX+SWAP skeleton as
a linear transformation over GF(2) and checks equality with the source CX
skeleton, including zero ancillary garbage. This does not by itself cover
arbitrary single-qubit gates; it is an independent structural cross-check.

### 5. Numerical full-unitary regression

`build_and_verify_full_qasm.py` additionally evaluates the frozen parameter
expressions in double precision and compares all 256 logical
computational-basis columns on the nine active physical nodes.

This is intentionally **secondary**. It is useful for regression testing but
is not required for the exact equivalence theorem.

## Deterministic artifact regeneration

`build_and_verify_full_qasm.py` reconstructs `mapped_route.qasm` from the pinned
source, `route.json`, and `benchmark.json`. It writes the original source angle
expressions verbatim rather than serializing floating-point approximations.

CI regenerates the file and requires a clean `git diff`.

## Trust boundary

Trusted:

- Python interpreter semantics for the small dependency-free exact checkers;
- the committed checker source after ordinary code review;
- the two frozen public-source snapshots: the source QASM and Q-Synth Sycamore edge list;
- standard mathematical semantics of OpenQASM `u`, CX, and SWAP operations;
- the published comparison fact taken from the cited SAT 2024 paper.

Not trusted as correctness oracles:

- the stochastic/beam search that discovered the route;
- AI generation;
- floating-point unitary simulation;
- `benchmark.json`'s CX list without source-QASM comparison;
- `benchmark.json`'s hardware edges without Q-Synth topology comparison;
- the published 16-SWAP row as an optimality lower bound;
- uncommitted local state or network services.

## Formalization decision

A Lean formalization is not currently required for the load-bearing finite
claim because the certificate is a short concrete operation trace and the
exact checker has a smaller, directly auditable trust surface. A future Lean
formalization could prove the general queue/placement invariant or verify a
serialized certificate, but the release must not describe the current Python
checker as a Lean proof.

## Review status

Independent external specialist review remains **pending**.
