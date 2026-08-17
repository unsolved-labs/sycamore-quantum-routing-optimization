#!/usr/bin/env python3
"""Build an exact mapped QASM and run a secondary numerical unitary regression.

The emitted mapped QASM preserves every source u(...) parameter expression
symbolically. The authoritative full-circuit correctness oracle is
verify_exact_qasm_equivalence.py. This script additionally evaluates the same
expressions numerically and compares all 256 logical computational-basis
columns as a regression/cross-check.
"""
from __future__ import annotations

import argparse, ast, cmath, hashlib, json, math, re, subprocess, sys
from dataclasses import dataclass
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "original_vqe_8_4_10_100.qasm"
EXPECTED_GIT_BLOB = "cdcb957d2c8f9a9f25fa5a530b80d8b6e7bd8af5"

@dataclass(frozen=True)
class Op:
    kind: str
    qubits: tuple[int, ...]
    params: tuple[str, ...] = ()
    cx_index: int | None = None

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def eval_angle(expr: str) -> float:
    tree = ast.parse(expr.strip(), mode="eval")
    def go(node):
        if isinstance(node, ast.Expression): return go(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return float(node.value)
        if isinstance(node, ast.Name) and node.id == "pi": return math.pi
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = go(node.operand); return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = go(node.left), go(node.right)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            return left / right
        raise ValueError(f"unsafe angle expression: {expr!r}")
    return float(go(tree))

def parse_source() -> list[Op]:
    data = SOURCE.read_bytes(); assert git_blob_sha(data) == EXPECTED_GIT_BLOB
    ops = []; cx_index = 0
    u_re = re.compile(r"^u\((.*)\) q\[(\d+)\];$"); cx_re = re.compile(r"^cx q\[(\d+)\],q\[(\d+)\];$")
    for raw in data.decode().splitlines():
        line = raw.strip()
        if not line or line.startswith(("OPENQASM", "include", "qreg")): continue
        m = u_re.match(line)
        if m:
            params = tuple(x.strip() for x in m.group(1).split(",")); assert len(params) == 3
            ops.append(Op("u", (int(m.group(2)),), params)); continue
        m = cx_re.match(line)
        if m:
            ops.append(Op("cx", (int(m.group(1)), int(m.group(2))), (), cx_index)); cx_index += 1; continue
        raise ValueError(f"unparsed source line: {line}")
    assert cx_index == 71 and sum(op.kind == "u" for op in ops) == 65
    return ops

def u_matrix(params: tuple[str, ...]) -> np.ndarray:
    theta, phi, lam = (eval_angle(x) for x in params); c = math.cos(theta / 2); s = math.sin(theta / 2)
    return np.array([[c, -cmath.exp(1j * lam) * s], [cmath.exp(1j * phi) * s, cmath.exp(1j * (phi + lam)) * c]], dtype=np.complex128)

def apply_u(state, n, q, matrix):
    bit = 1 << q
    for base in range(1 << n):
        if base & bit: continue
        i0, i1 = base, base | bit; a = state[i0].copy(); b = state[i1].copy()
        state[i0] = matrix[0, 0] * a + matrix[0, 1] * b; state[i1] = matrix[1, 0] * a + matrix[1, 1] * b

def apply_cx(state, n, control, target):
    cb = 1 << control; tb = 1 << target
    for i in range(1 << n):
        if (i & cb) and not (i & tb):
            j = i | tb; state[[i, j]] = state[[j, i]]

def apply_swap(state, n, a, b):
    if a == b: return
    ab = 1 << a; bb = 1 << b
    for i in range(1 << n):
        has_a = bool(i & ab); has_b = bool(i & bb)
        if has_a == has_b or has_a: continue
        j = i ^ ab ^ bb; state[[i, j]] = state[[j, i]]

def simulate(n, ops, initial):
    state = initial.copy()
    for op in ops:
        if op.kind == "u": apply_u(state, n, op.qubits[0], u_matrix(op.params))
        elif op.kind == "cx": apply_cx(state, n, *op.qubits)
        elif op.kind == "swap": apply_swap(state, n, *op.qubits)
        else: raise AssertionError(op.kind)
    return state

def build(route_name: str) -> dict:
    source_ops = parse_source(); route = json.loads((ROOT / route_name).read_text()); benchmark = json.loads((ROOT / "benchmark.json").read_text())
    source_cx = [(op.qubits[0], op.qubits[1]) for op in source_ops if op.kind == "cx"]
    assert source_cx == [tuple(x) for x in benchmark["cx_gates"]]
    pending = [[] for _ in range(8)]; before = [{} for _ in range(71)]
    for op in source_ops:
        if op.kind == "u": pending[op.qubits[0]].append(op)
        else:
            a, b = op.qubits; before[op.cx_index][a] = pending[a]; before[op.cx_index][b] = pending[b]; pending[a] = []; pending[b] = []
    tails = pending; mapping = {int(q): int(p) for q, p in route["initial_mapping"].items()}; mapped = []; seen_cx = []
    def emit_cx(index_1_based: int) -> None:
        index = index_1_based - 1; a, b = source_cx[index]
        for q in (a, b):
            for u_op in before[index][q]: mapped.append(Op("u", (mapping[q],), u_op.params))
        mapped.append(Op("cx", (mapping[a], mapping[b]), (), index)); seen_cx.append(index)
    for index_1_based in route["schedule"][0]["executed_cx_1_based"]: emit_cx(index_1_based)
    for (u, v), phase in zip(route["swaps"], route["schedule"][1:]):
        mapped.append(Op("swap", (u, v)))
        for q, p in list(mapping.items()):
            if p == u: mapping[q] = v
            elif p == v: mapping[q] = u
        for index_1_based in phase["executed_cx_1_based"]: emit_cx(index_1_based)
    for q in range(8):
        for u_op in tails[q]: mapped.append(Op("u", (mapping[q],), u_op.params))
    assert sum(op.kind == "u" for op in mapped) == 65; assert sum(op.kind == "cx" for op in mapped) == 71; assert sum(op.kind == "swap" for op in mapped) == 13
    assert len(seen_cx) == 71 and len(set(seen_cx)) == 71
    original_per = [[] for _ in range(8)]; mapped_per = [[] for _ in range(8)]
    for op in source_ops:
        if op.kind == "cx":
            for q in op.qubits: original_per[q].append(op.cx_index)
    for index in seen_cx:
        for q in source_cx[index]: mapped_per[q].append(index)
    assert original_per == mapped_per

    out = ROOT / f"mapped_{Path(route_name).stem}.qasm"
    with out.open("w") as handle:
        handle.write('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[54];\n')
        for op in mapped:
            if op.kind == "u": handle.write(f"u({','.join(op.params)}) q[{op.qubits[0]}];\n")
            elif op.kind == "cx": handle.write(f"cx q[{op.qubits[0]}],q[{op.qubits[1]}];\n")
            else: handle.write(f"swap q[{op.qubits[0]}],q[{op.qubits[1]}];\n")

    subprocess.run([sys.executable, str(ROOT / "verify_exact_qasm_equivalence.py")], cwd=ROOT, check=True)

    active = sorted(set(route["initial_mapping"].values()) | {p for edge in route["swaps"] for p in edge}); location = {p: i for i, p in enumerate(active)}; n_active = len(active); assert 8 <= n_active <= 9
    original_final = simulate(8, source_ops, np.eye(1 << 8, dtype=np.complex128))
    embed = np.zeros((1 << n_active, 1 << 8), dtype=np.complex128); initial_mapping = {int(q): location[int(p)] for q, p in route["initial_mapping"].items()}
    for logical_basis in range(1 << 8):
        physical_basis = 0
        for q in range(8):
            if logical_basis >> q & 1: physical_basis |= 1 << initial_mapping[q]
        embed[physical_basis, logical_basis] = 1
    mapped_local = [Op(op.kind, tuple(location[p] for p in op.qubits), op.params, op.cx_index) for op in mapped]
    actual = simulate(n_active, mapped_local, embed); final_mapping = {q: location[p] for q, p in mapping.items()}; expected = np.zeros_like(actual)
    for logical_basis in range(1 << 8):
        physical_basis = 0
        for q in range(8):
            if logical_basis >> q & 1: physical_basis |= 1 << final_mapping[q]
        expected[physical_basis, :] = original_final[logical_basis, :]
    delta = actual - expected; max_error = float(np.max(np.abs(delta))); frobenius_error = float(np.linalg.norm(delta)); assert max_error < 2e-13, (max_error, frobenius_error)
    result = {"route": route["id"], "source_git_blob_sha1": EXPECTED_GIT_BLOB, "mapped_qasm": out.name, "symbolic_parameter_preservation": True, "exact_full_circuit_checker": "verify_exact_qasm_equivalence.py", "exact_full_circuit_status": "PASS", "numerical_regression_role": "secondary_cross_check_only", "active_physical_nodes": active, "source_u_gates": 65, "source_cx_gates": 71, "mapped_u_gates": 65, "mapped_cx_gates": 71, "mapped_swaps": len(route["swaps"]), "all_logical_basis_inputs_numerically_checked": 256, "max_absolute_amplitude_error": max_error, "frobenius_error": frobenius_error, "final_mapping": {str(q): p for q, p in mapping.items()}}
    (ROOT / f"full_unitary_{Path(route_name).stem}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("route", nargs="?", default="route.json"); args = parser.parse_args()
    report = build(args.route); print("EXACT_QASM_BUILT"); print("NUMERICAL_UNITARY_REGRESSION_VERIFIED"); print(json.dumps(report, indent=2))
