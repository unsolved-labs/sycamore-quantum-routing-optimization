# R005 — Sycamore quantum routing optimization

**Unsolved Labs Research Release R005**

An explicit **13-SWAP** layout for the public Q-Synth `vqe_8_4_10_100`
benchmark on the frozen 54-qubit Sycamore coupling graph.

## Result

Shaik and van de Pol, SAT 2024, Table 3 report the `vqe(8/71)` instance on
Sycamore with Q-Synth2 timing out and TB-OLSQ2 returning **16 SWAPs** at
reported depth **111**.

This release provides:

- an explicit route using **13 inserted SWAPs**;
- all **71 source CX gates**, each executed once on an allowed hardware edge;
- all **65 source single-qubit `u(...)` gates**, reinserted with their source
  parameter expressions preserved **symbolically**;
- **39** added CX gates under the standard 3-CX SWAP decomposition, versus
  48 for 16 SWAPs;
- a deterministic native instruction-DAG depth of **110** under the included
  ASAP depth checker.

The principal comparison is therefore **16 → 13 SWAPs**, a reduction of 3
SWAPs or **18.75%** relative to that published comparison point.

This repository does **not** prove that 13 SWAPs is globally optimal, and it
does not prove that a 12-SWAP route is impossible.

## Verification

The correctness oracle for the complete routed circuit is now exact and does
not evaluate gate angles numerically:

```bash
python verify.py
python verify_exact_qasm_equivalence.py
python verify_linear_equivalence.py
python compute_qasm_depth.py original_vqe_8_4_10_100.qasm mapped_route.qasm
```

The exact full-circuit checker tracks the logical state carried by each
physical wire through the 13 SWAPs. Every mapped `u(...)` must be the next
source operation on that logical qubit with the **same symbolic parameter
expressions**; every mapped CX must be the next source operation on both
logical endpoint queues, with the same control/target direction and an edge
of the frozen Sycamore graph. All 136 source operations must be consumed
exactly once. This proves circuit equivalence modulo the reported initial and
final logical-to-physical placements under the frozen dependency model.

Expected headline output includes:

```text
VERIFIED
SWAPs: 13
EXACT_SYMBOLIC_EQUIVALENCE_VERIFIED
LINEAR_EQUIVALENCE_VERIFIED
```

A separate NumPy simulation remains as a **secondary regression check**, not
as the proof of circuit equivalence:

```bash
python -m pip install -r requirements.txt
python build_and_verify_full_qasm.py route.json
```

That command deterministically regenerates `mapped_route.qasm`, runs the exact
checker, then compares the source and routed circuits numerically on all 256
logical computational-basis inputs.

## Manuscript

- [LaTeX source](manuscript/r005_sycamore_routing.tex)
- [PDF](manuscript/r005_sycamore_routing.pdf)
- [Bibliography](manuscript/references.bib)

The manuscript gives the frozen model, construction statement, exact
equivalence argument, independent checks, provenance, limitations, and
reproduction procedure.

## Files

- `CLAIM.md` — canonical public claim and non-claims
- `CLAIM_BOUNDARY.md` — detailed frozen assumptions and scope
- `STATEMENT_AUDIT.md` — public claim → manuscript → checker crosswalk
- `SOURCE_AUDIT.md` — pinned Q-Synth source and published comparison
- `VERIFICATION.md` — trust boundary and clean-checkout reproduction
- `route.json` — explicit 13-SWAP route and logical-CX schedule
- `mapped_route.qasm` — exact symbolic mapped circuit
- `benchmark.json` — frozen source-circuit and Sycamore graph specification
- `original_vqe_8_4_10_100.qasm` — pinned source benchmark
- `verify.py` — source-derived routing/dependency verifier
- `verify_exact_qasm_equivalence.py` — exact complete-circuit checker
- `verify_linear_equivalence.py` — independent exact GF(2) CX+SWAP checker
- `build_and_verify_full_qasm.py` — exact QASM regeneration + numerical regression
- `compute_qasm_depth.py` — deterministic ASAP depth calculation
- `verification-report.json` — machine-readable release summary

## Provenance

Primary paper:

I. Shaik and J. van de Pol, *Optimal Layout Synthesis for Deep Quantum
Circuits on NISQ Processors with 100+ Qubits*, SAT 2024,
DOI `10.4230/LIPIcs.SAT.2024.26`.

Pinned benchmark source:

- repository: `irfansha/Q-Synth`
- commit: `95a820e16ac578289ea692ce8665afb48788892d`
- path: `Benchmarks/SAT-24/VQE/vqe_8_4_10_100.qasm`
- Git blob SHA-1: `cdcb957d2c8f9a9f25fa5a530b80d8b6e7bd8af5`

See `SOURCE_AUDIT.md` for the comparison boundary.

## Scope and status

This is a public AI-generated research release from Unsolved Labs. The
repository separates the generated construction from the exact verification
artifacts used to establish the stated claim.

The release establishes a replayable 13-SWAP construction for the frozen
benchmark and coupling graph. It does not establish a global 13-SWAP lower
bound, hardware-level fidelity improvement, or calibration-aware performance.

Independent external specialist review is **pending**.
