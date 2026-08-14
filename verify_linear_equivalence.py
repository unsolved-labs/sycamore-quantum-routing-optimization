#!/usr/bin/env python3
"""Independent GF(2) equivalence verifier for the released CNOT-routing witness."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable


def row_hex(rows: Iterable[int]) -> str:
    return " ".join(f"{r:02x}" for r in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("route", nargs="?", default="route.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    bench = json.loads((root / "benchmark.json").read_text())
    route = json.loads((root / args.route).read_text())

    n_logical = int(bench["logical_qubits"])
    n_physical = int(bench["physical_qubits"])
    gates = [tuple(map(int, gate)) for gate in bench["cx_gates"]]
    edges = {frozenset(map(int, edge)) for edge in bench["hardware_edges"]}

    mapping = {int(q): int(p) for q, p in route["initial_mapping"].items()}
    assert set(mapping) == set(range(n_logical))
    assert len(set(mapping.values())) == n_logical

    logical_rows = [1 << q for q in range(n_logical)]
    for control, target in gates:
        logical_rows[target] ^= logical_rows[control]

    physical_rows = [0] * n_physical
    for q, p in mapping.items():
        physical_rows[p] = 1 << q

    executed: list[int] = []
    schedule = route["schedule"]
    assert len(schedule) == len(route["swaps"]) + 1

    def execute_phase(indices_1_based: list[int]) -> None:
        for idx1 in indices_1_based:
            idx = int(idx1) - 1
            assert 0 <= idx < len(gates)
            control, target = gates[idx]
            pc, pt = mapping[control], mapping[target]
            assert frozenset((pc, pt)) in edges, (
                f"CX {idx1} is not on a hardware edge: p{pc}->p{pt}"
            )
            physical_rows[pt] ^= physical_rows[pc]
            executed.append(idx)

    execute_phase(schedule[0]["executed_cx_1_based"])

    for step, ((u, v), phase) in enumerate(zip(route["swaps"], schedule[1:]), 1):
        u, v = int(u), int(v)
        assert frozenset((u, v)) in edges, f"illegal SWAP {step}: {(u, v)}"

        physical_rows[u], physical_rows[v] = physical_rows[v], physical_rows[u]
        for q, p in list(mapping.items()):
            if p == u:
                mapping[q] = v
            elif p == v:
                mapping[q] = u

        execute_phase(phase["executed_cx_1_based"])

    assert len(executed) == len(gates)
    assert len(set(executed)) == len(gates), "a logical CX was executed more than once"

    original_per_wire = [[] for _ in range(n_logical)]
    routed_per_wire = [[] for _ in range(n_logical)]
    for idx, (a, b) in enumerate(gates):
        original_per_wire[a].append(idx)
        original_per_wire[b].append(idx)
    for idx in executed:
        a, b = gates[idx]
        routed_per_wire[a].append(idx)
        routed_per_wire[b].append(idx)
    assert routed_per_wire == original_per_wire, "per-logical-qubit CX order changed"

    final_rows = [physical_rows[mapping[q]] for q in range(n_logical)]
    assert final_rows == logical_rows, (
        "linear transformation mismatch\n"
        f"logical: {row_hex(logical_rows)}\n"
        f"routed:  {row_hex(final_rows)}"
    )

    occupied = set(mapping.values())
    garbage = {p: row for p, row in enumerate(physical_rows) if p not in occupied and row}
    assert not garbage, f"nonzero garbage remains outside the final mapping: {garbage}"

    digest_payload = bytes(logical_rows) + bytes(final_rows)
    digest = hashlib.sha256(digest_payload).hexdigest()

    print("LINEAR_EQUIVALENCE_VERIFIED")
    print("route:", route["id"])
    print("logical CX gates:", len(gates))
    print("physical SWAPs:", len(route["swaps"]))
    print("source matrix rows (hex):", row_hex(logical_rows))
    print("routed matrix rows (hex):", row_hex(final_rows))
    print("matrix-pair sha256:", digest)
    print("final mapping:", " ".join(f"q{q}->p{mapping[q]}" for q in range(n_logical)))


if __name__ == "__main__":
    main()
