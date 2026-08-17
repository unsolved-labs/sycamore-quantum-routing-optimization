# Frozen claim boundary

## Instance

- Logical source: `original_vqe_8_4_10_100.qasm`.
- Pinned Q-Synth commit: `95a820e16ac578289ea692ce8665afb48788892d`.
- Source path: `Benchmarks/SAT-24/VQE/vqe_8_4_10_100.qasm`.
- Source Git blob SHA-1: `cdcb957d2c8f9a9f25fa5a530b80d8b6e7bd8af5`.
- Source circuit: 8 logical qubits, 65 single-qubit `u` gates, 71 `cx` gates.
- Hardware: the 54-node undirected Sycamore coupling graph frozen in
  `benchmark.json`.

## Routing model

1. The initial placement maps the eight logical qubits injectively to physical
   vertices as recorded in `route.json`.
2. A logical `cx` executes only when its current physical endpoints are
   adjacent in the frozen coupling graph.
3. Source operations preserve ordinary per-logical-qubit program order.
   Operations on disjoint logical qubits may interleave.
4. A SWAP is inserted only on a hardware edge. Unoccupied physical vertices may
   act as routing ancillas.
5. Only a SWAP changes the logical-to-physical placement.
6. The optimization quantity reported by this release is inserted SWAP count.
7. The model does not use bridge gates, teleportation, measurement, qubit
   reuse, calibration weights, or relaxed CNOT commutation rules.

## Frozen comparison baseline

Shaik and van de Pol, SAT 2024, Table 3 (`vqe(8/71)`, Sycamore) report:

- Q-Synth2: timeout;
- TB-OLSQ2: 16 SWAPs, depth 111.

The canonical DOI is `10.4230/LIPIcs.SAT.2024.26`.

This release compares against that specific published point. It does not treat
16 as a proved lower bound, because the Q-Synth2 run timed out and TB-OLSQ2 is
reported as near-optimal rather than as an optimality certificate for this row.

## Claims established

- `route.json` is a valid route using exactly 13 inserted SWAPs.
- Every SWAP is on a frozen Sycamore edge.
- Every logical CX executes on adjacent physical sites and all 71 CX operations
  execute exactly once.
- The `benchmark.json` CX list is checked against the pinned source QASM rather
  than trusted independently.
- Ordinary per-logical-qubit source order is preserved.
- `mapped_route.qasm` preserves every source `u(...)` parameter expression
  symbolically; no floating-point conversion is used to construct the mapped
  artifact.
- `verify_exact_qasm_equivalence.py` consumes all 136 source operations exactly
  once while tracking the logical state through the SWAPs, giving an exact
  complete-circuit equivalence check modulo final placement.
- `verify_linear_equivalence.py` independently checks the CX+SWAP skeleton over
  GF(2), including ancillary garbage.
- The NumPy full-unitary calculation is a secondary numerical regression on all
  256 logical computational-basis inputs; it is not the correctness oracle.
- The emitted mapped circuit has native instruction-DAG depth 110 under
  `compute_qasm_depth.py`.
- Relative to the frozen 16-SWAP comparison point, the construction reduces
  inserted SWAPs by 3 (18.75%) and the corresponding 3-CX SWAP overhead from
  48 to 39 CX gates.

## Claims not established

- Global optimality of 13 SWAPs on all 54 Sycamore vertices.
- Nonexistence of a 12-SWAP route.
- Identity between the repository's depth checker and the implementation used
  to produce the paper's depth-111 entry, absent the exact baseline routed
  artifact.
- Hardware-level fidelity, wall-clock latency, energy, or calibration-aware
  improvement.
- Independent external specialist review. Review status remains pending.
