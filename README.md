# R005 — Sycamore quantum routing optimization

**Unsolved Labs Research Release R005**

An explicit 13-SWAP layout for the public Q-Synth `vqe_8_4_10_100` benchmark on the 54-qubit Sycamore coupling graph.

## Result

Published comparison point from Shaik and van de Pol, SAT 2024, Table 3:

- circuit: `vqe(8/71)` on Sycamore (54 qubits)
- Q-Synth2: timeout
- TB-OLSQ2: **16 SWAPs**, depth **111**

Released route:

- **13 SWAPs**
- 71 logical CX gates preserved
- 39 added CX gates under the standard 3-CX SWAP decomposition, versus 48 for 16 SWAPs
- **18.75% fewer inserted SWAPs** than the published 16-SWAP comparison point
- native instruction-DAG depth **110** under the included ASAP depth checker

The main release claim is the explicit 16 → 13 SWAP improvement. It does **not** claim that 13 SWAPs are globally optimal on all 54 Sycamore vertices.

## Reproduce

The principal structural and exact GF(2) checks use only Python's standard library:

```bash
python verify.py
python verify_linear_equivalence.py
python compute_qasm_depth.py original_vqe_8_4_10_100.qasm mapped_route.qasm
```

Expected headline output includes:

```text
VERIFIED
SWAPs: 13
added CX at 3 per SWAP: 39
LINEAR_EQUIVALENCE_VERIFIED
```

For a full numerical unitary comparison on all 256 logical computational-basis inputs:

```bash
python -m pip install numpy
python build_and_verify_full_qasm.py route.json
```

The verifier first checks that the source QASM has Git blob SHA-1
`cdcb957d2c8f9a9f25fa5a530b80d8b6e7bd8af5`, matching the pinned Q-Synth source file.

## Files

- `route.json` — explicit 13-SWAP route and logical-CX schedule
- `mapped_route.qasm` — complete mapped circuit with source single-qubit gates reinserted
- `benchmark.json` — frozen source-circuit and Sycamore coupling specification
- `original_vqe_8_4_10_100.qasm` — pinned source benchmark
- `verify.py` — independent routing/dependency verifier
- `verify_linear_equivalence.py` — exact GF(2) CX+SWAP equivalence verifier
- `build_and_verify_full_qasm.py` — full source-QASM reinsertion and all-basis numerical unitary check
- `compute_qasm_depth.py` — deterministic ASAP depth calculation
- `verification-report.json` — machine-readable claim and verification summary
- `CLAIM_BOUNDARY.md` — frozen assumptions and limitations

## Baseline

Primary paper:

I. Shaik and J. van de Pol, *Optimal Layout Synthesis for Deep Quantum Circuits on NISQ Processors with 100+ Qubits*, SAT 2024 / arXiv:2403.11598.

Table 3 reports `vqe(8/71)` on Sycamore with Q-Synth2 timing out and TB-OLSQ2 returning 16 SWAPs at depth 111.

Pinned benchmark source:

- repository: `irfansha/Q-Synth`
- commit: `95a820e16ac578289ea692ce8665afb48788892d`
- path: `Benchmarks/SAT-24/VQE/vqe_8_4_10_100.qasm`

## Claim boundary

This repository establishes a replayable 13-SWAP construction for the frozen benchmark and hardware graph. It does not establish a global lower bound of 13, a hardware-level fidelity improvement, or calibration-aware performance. See `CLAIM_BOUNDARY.md`.
