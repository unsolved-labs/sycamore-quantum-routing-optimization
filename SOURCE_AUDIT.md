# Source and comparison audit

## Primary publication

Irfansha Shaik and Jaco van de Pol,
*Optimal Layout Synthesis for Deep Quantum Circuits on NISQ Processors with
100+ Qubits*, 27th International Conference on Theory and Applications of
Satisfiability Testing (SAT 2024), LIPIcs 305, Article 26.

- DOI: `10.4230/LIPIcs.SAT.2024.26`
- arXiv: `2403.11598`
- public software repository: `irfansha/Q-Synth`

The paper defines layout synthesis as an initial logical-to-physical placement
plus inserted SWAPs that permit dependent two-qubit gates to execute on
connected physical qubits. Gates that are independent in the circuit
dependency DAG may be scheduled in either order.

## Published comparison point

Table 3, Experiment 2, reports for `vqe(8/71)` on Sycamore (54 qubits):

| method | SWAPs | depth |
|---|---:|---:|
| Q-Synth2 | timeout | timeout |
| TB-OLSQ2 | 16 | 111 |

The paper describes Q-Synth2 as SWAP-optimal when it solves an instance and
TB-OLSQ2 as near-optimal. Because Q-Synth2 times out on this particular
Sycamore row, **the paper does not provide a 16-SWAP optimality certificate for
this row**. R005 therefore uses 16 only as a frozen published comparison point.

## Pinned benchmark source

R005 freezes the source circuit to:

- repository: `irfansha/Q-Synth`
- commit: `95a820e16ac578289ea692ce8665afb48788892d`
- path: `Benchmarks/SAT-24/VQE/vqe_8_4_10_100.qasm`
- Git blob SHA-1: `cdcb957d2c8f9a9f25fa5a530b80d8b6e7bd8af5`

`original_vqe_8_4_10_100.qasm` is checked against that blob SHA before
verification.

## Pinned Sycamore topology source

At the same Q-Synth commit, the public command-line interface identifies the
`sycamore` platform as a 54-qubit Google Sycamore topology. The exact coupling
map is defined in:

- repository: `irfansha/Q-Synth`
- commit: `95a820e16ac578289ea692ce8665afb48788892d`
- path: `src/qsynth/LayoutSynthesis/architecture.py`
- Git blob SHA-1: `72e4729523db7d58bd4a2658399da590f83d1049`
- platform branch: `platform == "sycamore"`
- physical qubits: 54
- undirected edges before bidirectional expansion: 88

`source_sycamore_edges.json` is a frozen local transcription of that exact
88-edge list. `verify.py` requires the set of edges in `benchmark.json` to
match the frozen source snapshot exactly before it checks the route.

This removes an earlier provenance ambiguity: `benchmark.json` is no longer an
unreferenced hardware definition. It is verified against the same pinned
Q-Synth code base that supplies the logical benchmark.

## Frozen hardware model

`benchmark.json` remains the release's canonical 54-vertex, 88-edge undirected
coupling graph used by all route/equivalence checks, but its edge set must match
`source_sycamore_edges.json` exactly.

The public comparison is meaningful only under compatible routing semantics.
This release does not claim equivalence to variants using bridges, relaxed
commutation, teleportation, measurement, qubit reuse, calibration weighting,
or another coupling graph.

## Depth comparison boundary

The repository deterministically reports native instruction-DAG depth 110 for
`mapped_route.qasm` with `compute_qasm_depth.py`. The SAT 2024 paper reports
depth 111 for the TB-OLSQ2 16-SWAP row.

The exact 16-SWAP routed circuit used to obtain the table entry is not frozen
in this repository. Consequently R005 treats the depth numbers as contextual
rather than claiming an independently reproduced one-unit depth improvement
under byte-identical tooling. The load-bearing result is the explicit
16-to-13 SWAP comparison.
