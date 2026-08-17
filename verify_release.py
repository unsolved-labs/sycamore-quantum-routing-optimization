#!/usr/bin/env python3
"""One-command verifier for the frozen R005 release.

Default mode is dependency-free and runs all load-bearing exact checks.
Pass --with-numerical after installing requirements.txt to additionally run the
secondary NumPy full-unitary regression and deterministic QASM regeneration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def run(script: str, *args: str) -> None:
    print(f"\n==> {script} {' '.join(args)}".rstrip(), flush=True)
    subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--with-numerical",
        action="store_true",
        help="also run the secondary NumPy all-basis unitary regression",
    )
    args = parser.parse_args()

    run("verify.py")
    run("verify_exact_qasm_equivalence.py")
    run("verify_linear_equivalence.py")
    run(
        "compute_qasm_depth.py",
        "original_vqe_8_4_10_100.qasm",
        "mapped_route.qasm",
    )

    depth = json.loads((ROOT / "depth_metrics.json").read_text())
    assert depth[0]["native_instruction_depth"] == 102
    assert depth[1]["native_instruction_depth"] == 110
    assert depth[1]["swap"] == 13
    assert depth[1]["cx"] == 71

    exact = json.loads((ROOT / "exact_equivalence_report.json").read_text())
    assert exact["status"] == "PASS"
    assert exact["floating_point_used_in_correctness_oracle"] is False

    release = json.loads((ROOT / "verification-report.json").read_text())
    assert release["status"] == "PASS"
    assert release["claim"]["swap_count"] == 13
    assert release["claim"]["global_optimality_claimed"] is False
    assert release["verification"]["logical_program_matches_pinned_qasm"] == "PASS"
    assert release["verification"]["hardware_graph_matches_pinned_qsynth_sycamore"] == "PASS"
    assert release["verification"]["exact_symbolic_full_circuit"] == "PASS"
    assert release["review_status"] == "pending"

    if args.with_numerical:
        run("build_and_verify_full_qasm.py", "route.json")
        numerical = json.loads((ROOT / "full_unitary_route.json").read_text())
        assert numerical["exact_full_circuit_status"] == "PASS"
        assert numerical["mapped_swaps"] == 13
        assert numerical["all_logical_basis_inputs_numerically_checked"] == 256
        assert numerical["max_absolute_amplitude_error"] < 2e-13

    print("\nR005_RELEASE_VERIFIED")
    print("exact correctness oracle: PASS")
    print("source QASM identity: PASS")
    print("Q-Synth Sycamore topology identity: PASS")
    print("13-SWAP route: PASS")
    print("exact full-circuit symbolic equivalence: PASS")
    print("GF(2) independent cross-check: PASS")
    print("native mapped depth 110: PASS")
    print("global 13-SWAP optimality: NOT CLAIMED")
    print("external specialist review: PENDING")
    if args.with_numerical:
        print("secondary all-basis numerical regression: PASS")


if __name__ == "__main__":
    main()
