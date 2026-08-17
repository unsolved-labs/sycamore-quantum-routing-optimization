# Canonical claim — R005

For the frozen public Q-Synth benchmark
`Benchmarks/SAT-24/VQE/vqe_8_4_10_100.qasm` at commit
`95a820e16ac578289ea692ce8665afb48788892d`, and for the frozen 54-node
undirected Sycamore coupling graph in `benchmark.json`, `route.json` defines a
valid layout/routing construction using exactly **13 inserted SWAP gates**.

Under the frozen model:

- the initial placement is the injective mapping stored in `route.json`;
- every inserted SWAP is on a hardware edge;
- every source CX is executed exactly once on adjacent physical qubits;
- source operations obey the ordinary per-logical-qubit program-order DAG;
- operations on disjoint logical qubits may interleave;
- all 65 source `u(...)` gates are reinserted with their symbolic OpenQASM
  parameter expressions unchanged;
- the complete mapped circuit is exactly equivalent to the source circuit
  modulo the reported initial/final logical-to-physical placement;
- the mapped circuit has native instruction-DAG depth 110 under
  `compute_qasm_depth.py`.

Shaik and van de Pol, SAT 2024, Table 3 report the corresponding `vqe(8/71)`
Sycamore row with Q-Synth2 timing out and TB-OLSQ2 returning 16 SWAPs at
reported depth 111. Relative to that specific published comparison point, this
construction uses 3 fewer inserted SWAPs, a reduction of **18.75%**.

## Non-claims

This release does **not** establish:

- global optimality of 13 SWAPs;
- nonexistence of a 12-SWAP route;
- that the paper's depth-111 value and this repository's depth-110 value were
  computed by an identical depth implementation, because the exact published
  16-SWAP routed artifact is not included here;
- hardware fidelity, latency, energy, calibration-aware, or noise improvement;
- superiority over every unpublished, later, or differently normalized routing
  result;
- independent external specialist review. That status remains pending.
