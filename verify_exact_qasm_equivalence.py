#!/usr/bin/env python3
"""Exact symbolic equivalence checker for the released mapped OpenQASM circuit.

This checker does not evaluate gate angles numerically. It verifies that every
source u(...) gate appears exactly once with the same symbolic parameter
expressions on the physical wire currently carrying its logical qubit, every
source CX appears exactly once with the same directed logical operands, all
per-logical-qubit source dependencies are respected, every mapped CX/SWAP uses
a frozen hardware edge, and the mapped SWAP/CX schedule agrees with route.json.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "original_vqe_8_4_10_100.qasm"
MAPPED = ROOT / "mapped_route.qasm"
ROUTE = ROOT / "route.json"
BENCHMARK = ROOT / "benchmark.json"
EXPECTED_SOURCE_GIT_BLOB_SHA1 = "cdcb957d2c8f9a9f25fa5a530b80d8b6e7bd8af5"


@dataclass(frozen=True)
class Op:
    op_id: int
    kind: str
    qubits: tuple[int, ...]
    params: tuple[str, ...] = ()


def git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def canonical_expr(expr: str) -> str:
    return re.sub(r"\s+", "", expr)


def parse_qasm(path: Path, allow_swap: bool):
    qreg_n = None
    ops = []
    u_re = re.compile(r"^u\((.*)\) q\[(\d+)\];$")
    cx_re = re.compile(r"^cx q\[(\d+)\],q\[(\d+)\];$")
    swap_re = re.compile(r"^swap q\[(\d+)\],q\[(\d+)\];$")
    qreg_re = re.compile(r"^qreg q\[(\d+)\];$")
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("OPENQASM") or line.startswith("include"):
            continue
        m = qreg_re.match(line)
        if m:
            qreg_n = int(m.group(1)); continue
        m = u_re.match(line)
        if m:
            parts = tuple(canonical_expr(x) for x in m.group(1).split(","))
            assert len(parts) == 3, f"{path}:{lineno}: expected 3 u parameters"
            ops.append(("u", (int(m.group(2)),), parts)); continue
        m = cx_re.match(line)
        if m:
            ops.append(("cx", (int(m.group(1)), int(m.group(2))), ())); continue
        m = swap_re.match(line)
        if m and allow_swap:
            ops.append(("swap", (int(m.group(1)), int(m.group(2))), ())); continue
        raise AssertionError(f"{path}:{lineno}: unsupported line: {line}")
    assert qreg_n is not None, f"{path}: missing qreg"
    return qreg_n, ops


def main() -> None:
    source_bytes = SOURCE.read_bytes()
    actual_blob = git_blob_sha(source_bytes)
    assert actual_blob == EXPECTED_SOURCE_GIT_BLOB_SHA1, f"source QASM blob mismatch: {actual_blob}"
    source_n, source_raw = parse_qasm(SOURCE, allow_swap=False)
    mapped_n, mapped_ops = parse_qasm(MAPPED, allow_swap=True)
    assert source_n == 8 and mapped_n == 54
    bench = json.loads(BENCHMARK.read_text())
    route = json.loads(ROUTE.read_text())

    source_ops = []
    queues = [deque() for _ in range(source_n)]
    source_cx_pairs = []
    cx_index_by_op_id = {}
    for op_id, (kind, qubits, params) in enumerate(source_raw):
        op = Op(op_id, kind, qubits, params)
        source_ops.append(op)
        for q in qubits:
            queues[q].append(op)
        if kind == "cx":
            source_cx_pairs.append((qubits[0], qubits[1]))
            cx_index_by_op_id[op_id] = len(source_cx_pairs)
    assert len(source_ops) == 136
    assert sum(op.kind == "u" for op in source_ops) == 65
    assert len(source_cx_pairs) == 71
    assert source_cx_pairs == [tuple(x) for x in bench["cx_gates"]], "benchmark CX list != pinned source QASM"

    edge_set = {frozenset(edge) for edge in bench["hardware_edges"]}
    mapping = {int(q): int(p) for q, p in route["initial_mapping"].items()}
    assert set(mapping) == set(range(source_n)) and len(set(mapping.values())) == source_n
    at_physical = {p: q for q, p in mapping.items()}
    consumed = set(); seen_cx = []; seen_swaps = []

    def consume(op: Op) -> None:
        assert op.op_id not in consumed, f"source op {op.op_id} consumed twice"
        for q in op.qubits:
            assert queues[q] and queues[q][0] == op, f"source dependency violation on q{q}"
        for q in op.qubits:
            queues[q].popleft()
        consumed.add(op.op_id)

    for mapped_index, (kind, physical, params) in enumerate(mapped_ops, 1):
        if kind == "swap":
            a, b = physical
            assert frozenset((a, b)) in edge_set, f"mapped op {mapped_index}: illegal SWAP {physical}"
            seen_swaps.append([a, b])
            logical_a = at_physical.pop(a, None); logical_b = at_physical.pop(b, None)
            if logical_a is not None:
                mapping[logical_a] = b; at_physical[b] = logical_a
            if logical_b is not None:
                mapping[logical_b] = a; at_physical[a] = logical_b
            continue
        if kind == "u":
            (p,) = physical
            assert p in at_physical, f"mapped op {mapped_index}: u acts on empty physical q[{p}]"
            logical = at_physical[p]
            assert queues[logical], f"mapped op {mapped_index}: no source op remains on q{logical}"
            expected = queues[logical][0]
            assert expected.kind == "u" and expected.qubits == (logical,)
            assert expected.params == params, f"mapped op {mapped_index}: symbolic u parameters changed"
            consume(expected); continue
        if kind == "cx":
            p_control, p_target = physical
            assert frozenset((p_control, p_target)) in edge_set, f"mapped op {mapped_index}: illegal CX edge"
            assert p_control in at_physical and p_target in at_physical
            logical_control = at_physical[p_control]; logical_target = at_physical[p_target]
            expected_control = queues[logical_control][0]; expected_target = queues[logical_target][0]
            assert expected_control == expected_target, f"mapped op {mapped_index}: CX endpoints not ready for same source op"
            expected = expected_control
            assert expected.kind == "cx" and expected.qubits == (logical_control, logical_target), f"mapped op {mapped_index}: CX direction/logical operands changed"
            seen_cx.append(cx_index_by_op_id[expected.op_id]); consume(expected); continue
        raise AssertionError(kind)

    assert len(consumed) == len(source_ops) and all(not q for q in queues)
    assert seen_swaps == route["swaps"], "mapped QASM SWAP sequence != route.json"
    expected_cx_schedule = [i for phase in route["schedule"] for i in phase["executed_cx_1_based"]]
    assert seen_cx == expected_cx_schedule, "mapped QASM CX schedule != route.json"
    assert len(seen_swaps) == route["swap_count"] == 13 and len(seen_cx) == 71
    final_mapping = {str(q): mapping[q] for q in sorted(mapping)}
    expected_final = {str(q): int(route["schedule"][-1]["mapping"][str(q)]) for q in range(source_n)}
    assert final_mapping == expected_final

    report = {
        "status": "PASS",
        "proof_mode": "exact_symbolic_dependency_replay",
        "source_git_blob_sha1": actual_blob,
        "source_operations": len(source_ops),
        "source_u_gates": 65,
        "source_cx_gates": 71,
        "mapped_swaps": 13,
        "mapped_cx_gates": len(seen_cx),
        "symbolic_u_parameters_preserved": True,
        "hardware_edges_checked": True,
        "source_dependency_dag_checked": True,
        "route_schedule_checked": True,
        "floating_point_used_in_correctness_oracle": False,
        "final_mapping": final_mapping,
    }
    (ROOT / "exact_equivalence_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("EXACT_SYMBOLIC_EQUIVALENCE_VERIFIED")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
