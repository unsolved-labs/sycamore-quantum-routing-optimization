# Frozen claim boundary

## Instance

- Logical source: `original_vqe_8_4_10_100.qasm`.
- Pinned Q-Synth commit: `95a820e16ac578289ea692ce8665afb48788892d`.
- Source path: `Benchmarks/SAT-24/VQE/vqe_8_4_10_100.qasm`.
- Source Git blob SHA-1: `cdcb957d2c8f9a9f25fa5a530b80d8b6e7bd8af5`.
- Source circuit: 8 logical qubits, 65 single-qubit `u` gates, 71 `cx` gates.
- Hardware: the 54-node undirected Sycamore coupling graph frozen in `benchmark.json`.

## Routing model

1. The initial placement maps the eight logical qubits injectively to physical vertices.
2. A logical `cx` executes only when its two current physical locations are adjacent in the frozen coupling graph.
3. Logical `cx` operations preserve ordinary per-logical-qubit source order. Operations on disjoint logical qubits may interleave.
4. A SWAP is inserted only on a hardware edge. Unoccupied physical vertices are permitted as ancillas.
5. The objective reported by this release is inserted SWAP count.
6. The model does not use bridge gates, teleportation, measurement, qubit reuse, calibration weights, or relaxed CNOT commutation rules.

## Frozen comparison baseline

Shaik and van de Pol, SAT 2024, Table 3 reports the `vqe(8/71)` Sycamore instance with Q-Synth2 timing out and TB-OLSQ2 returning 16 SWAPs at depth 111.

This release compares against that specific published point. It does not claim that 16 SWAPs was the global best-known value in every unpublished or later system before this release.

## Claims established

- `route.json` is a valid route using exactly 13 inserted SWAPs.
- Every SWAP is on a frozen Sycamore edge.
- Every logical CX executes on adjacent physical sites and all 71 CX operations execute exactly once.
- Ordinary per-logical-qubit source order is preserved.
- The routed CX+SWAP skeleton has exactly the same GF(2) linear transformation as the source CX skeleton, with no nonzero ancillary garbage.
- Reinserted source single-qubit gates and the routed circuit agree on all 256 logical computational-basis inputs to floating-point roundoff in the included full-unitary checker.
- The emitted mapped circuit has native instruction-DAG depth 110 under `compute_qasm_depth.py`.
- Relative to the frozen 16-SWAP comparison point, the construction reduces inserted SWAPs by 3, or 18.75%, and reduces the corresponding 3-CX SWAP overhead from 48 to 39 CX gates.

## Claims not established

- Global optimality of 13 SWAPs on all 54 Sycamore vertices.
- Nonexistence of a 12-SWAP route.
- Hardware-level fidelity, wall-clock latency, energy, or calibration-aware improvement.
- A QCEC/Qiskit replay of the final circuit.
- Independent specialist review. Review status is pending.
