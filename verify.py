#!/usr/bin/env python3
"""Dependency-free verifier for the frozen R005 route certificate.

The logical CX sequence is derived directly from the pinned source QASM and the
hardware graph is compared against a frozen snapshot of Q-Synth's `sycamore`
platform definition before the route certificate is checked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

EXPECTED_SOURCE_GIT_BLOB_SHA1 = "cdcb957d2c8f9a9f25fa5a530b80d8b6e7bd8af5"
EXPECTED_TOPOLOGY_GIT_BLOB_SHA1 = "72e4729523db7d58bd4a2658399da590f83d1049"
EXPECTED_QSYNTH_COMMIT = "95a820e16ac578289ea692ce8665afb48788892d"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def source_cx_pairs(path: Path) -> list[tuple[int, int]]:
    data = path.read_bytes()
    actual = git_blob_sha(data)
    assert actual == EXPECTED_SOURCE_GIT_BLOB_SHA1, (
        f"source QASM blob mismatch: {actual}"
    )
    cx_re = re.compile(r"^cx q\[(\d+)\],q\[(\d+)\];$")
    pairs: list[tuple[int, int]] = []
    for raw in data.decode().splitlines():
        line = raw.strip()
        m = cx_re.match(line)
        if m:
            pairs.append((int(m.group(1)), int(m.group(2))))
    assert len(pairs) == 71
    return pairs


def source_topology(root: Path) -> set[frozenset[int]]:
    record = json.loads((root / "source_sycamore_edges.json").read_text())
    assert record["source_repository"] == "irfansha/Q-Synth"
    assert record["source_commit"] == EXPECTED_QSYNTH_COMMIT
    assert record["source_path"] == "src/qsynth/LayoutSynthesis/architecture.py"
    assert record["source_git_blob_sha1"] == EXPECTED_TOPOLOGY_GIT_BLOB_SHA1
    assert record["platform"] == "sycamore"
    assert record["physical_qubits"] == 54
    assert record["edge_count"] == 88
    edges = {frozenset(edge) for edge in record["undirected_edges"]}
    assert len(edges) == 88
    return edges


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("route", nargs="?", default="route.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    benchmark = json.loads((root / "benchmark.json").read_text())
    route = json.loads((root / args.route).read_text())

    gates = source_cx_pairs(root / "original_vqe_8_4_10_100.qasm")
    benchmark_gates = [tuple(x) for x in benchmark["cx_gates"]]
    assert gates == benchmark_gates, (
        "benchmark.json CX list differs from the pinned source QASM"
    )

    edge_set = {frozenset(x) for x in benchmark["hardware_edges"]}
    source_edge_set = source_topology(root)
    assert edge_set == source_edge_set, (
        "benchmark.json hardware graph differs from the pinned Q-Synth "
        "sycamore topology snapshot"
    )
    assert benchmark["physical_qubits"] == 54

    mapping = {
        int(k): int(v) for k, v in route["initial_mapping"].items()
    }
    assert set(mapping) == set(range(benchmark["logical_qubits"]))
    assert len(set(mapping.values())) == len(mapping)

    last = [None] * benchmark["logical_qubits"]
    predecessors: list[set[int]] = []
    for i, (a, b) in enumerate(gates):
        pred: set[int] = set()
        if last[a] is not None:
            pred.add(last[a])
        if last[b] is not None:
            pred.add(last[b])
        predecessors.append(pred)
        last[a] = last[b] = i

    done: set[int] = set()
    reconstructed: list[list[int]] = []

    def closure() -> list[int]:
        newly_executed: list[int] = []
        changed = True
        while changed:
            changed = False
            for i, (a, b) in enumerate(gates):
                if i in done or not predecessors[i].issubset(done):
                    continue
                if frozenset((mapping[a], mapping[b])) in edge_set:
                    done.add(i)
                    newly_executed.append(i + 1)
                    changed = True
        return newly_executed

    reconstructed.append(closure())
    for step, (u, v) in enumerate(route["swaps"], 1):
        assert frozenset((u, v)) in edge_set, (
            f"illegal SWAP {step}: {(u, v)}"
        )
        logical_u = next(
            (q for q, p in mapping.items() if p == u), None
        )
        logical_v = next(
            (q for q, p in mapping.items() if p == v), None
        )
        if logical_u is not None:
            mapping[logical_u] = v
        if logical_v is not None:
            mapping[logical_v] = u
        assert len(set(mapping.values())) == len(mapping)
        reconstructed.append(closure())

    assert len(done) == len(gates), (
        f"only {len(done)}/{len(gates)} CX gates routed"
    )
    claimed = [
        phase["executed_cx_1_based"] for phase in route["schedule"]
    ]
    assert reconstructed == claimed, (
        "stored schedule does not match reconstructed schedule"
    )
    assert len(route["swaps"]) == route["swap_count"] == 13

    print("VERIFIED")
    print("source QASM Git blob:", EXPECTED_SOURCE_GIT_BLOB_SHA1)
    print("source CX list matches benchmark.json:", len(gates))
    print("Sycamore topology matches pinned Q-Synth source:", len(edge_set))
    print("topology source Git blob:", EXPECTED_TOPOLOGY_GIT_BLOB_SHA1)
    print("route:", route["id"])
    print("CX gates:", len(gates))
    print("SWAPs:", len(route["swaps"]))
    print("added CX at 3 per SWAP:", 3 * len(route["swaps"]))
    print(
        "final mapping:",
        " ".join(f"q{q}->p{mapping[q]}" for q in sorted(mapping)),
    )


if __name__ == "__main__":
    main()
