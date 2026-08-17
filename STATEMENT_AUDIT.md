# Statement audit

This file maps each public R005 statement to the manuscript and the concrete
machine check that supports it.

| Public statement | Manuscript location | Machine evidence | Status |
|---|---|---|---|
| Frozen source is Q-Synth `vqe_8_4_10_100.qasm` at the pinned commit/blob | Sec. 2, 7 | `verify.py`; `build_and_verify_full_qasm.py` Git-blob check | exact |
| Source contains 8 logical qubits, 65 `u` gates, 71 CX gates | Sec. 2 | source parsers in `verify_exact_qasm_equivalence.py` and build script | exact |
| Route uses 13 inserted SWAPs | Thm. 1; Sec. 3 | `verify.py`; exact checker; `route.json` | exact |
| Every SWAP is a frozen hardware edge | Thm. 1 | `verify.py`; exact checker | exact |
| Every source CX executes exactly once on adjacent physical sites | Thm. 1 | `verify.py`; exact checker | exact |
| Ordinary per-logical-qubit source dependencies are preserved | Thm. 1; Sec. 4 | `verify.py`; `verify_exact_qasm_equivalence.py` | exact |
| All source `u(...)` expressions are preserved symbolically | Thm. 2; Sec. 4 | `verify_exact_qasm_equivalence.py`; deterministic QASM regeneration | exact |
| Complete mapped circuit equals the source modulo initial/final placement | Thm. 2; Sec. 4 | exact symbolic dependency replay | exact under frozen routing semantics |
| CX+SWAP linear skeleton has no ancillary garbage | Sec. 5 | `verify_linear_equivalence.py` | exact GF(2) cross-check |
| Numerical full-circuit replay agrees on all 256 logical basis inputs | Sec. 5 | `build_and_verify_full_qasm.py` | secondary floating-point regression |
| Mapped native instruction-DAG depth is 110 | Sec. 3, 5 | `compute_qasm_depth.py` | exact for the included depth definition |
| SAT 2024 Table 3 reports TB-OLSQ2 16 SWAPs / depth 111 and Q-Synth2 timeout | Sec. 1, 7 | primary-paper source audit | published-source fact |
| 13 is 18.75% fewer SWAPs than 16; 39 vs 48 added CX under 3-CX decomposition | Sec. 3 | arithmetic + verified swap count | exact |
| 13 is globally optimal | nowhere | no lower-bound certificate exists | **not claimed** |
| No 12-SWAP route exists | nowhere | no UNSAT certificate exists | **not claimed** |
| Hardware fidelity/calibration performance improves | nowhere | no hardware experiment | **not claimed** |
| Independent external specialist review | status only | no public review artifact tied to this release | **pending** |

## Statement identity rule

If README, manuscript, release page, or metadata wording changes, re-run this
audit manually and update the table. No public summary may turn the explicit
13-SWAP construction into a global optimum claim without a new lower-bound
certificate.
