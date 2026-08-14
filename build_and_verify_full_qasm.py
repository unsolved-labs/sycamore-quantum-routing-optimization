#!/usr/bin/env python3
"""Reinsert all source single-qubit gates, emit mapped QASM, and verify full-unitary equivalence.

The source file is byte-for-byte checked against the audited Git blob SHA. The
mapped circuit is simulated on its active physical footprint and compared on
all 256 logical basis inputs with the original 8-qubit unitary.
"""
from __future__ import annotations
import argparse, ast, cmath, hashlib, json, math, re
from pathlib import Path
from dataclasses import dataclass
import numpy as np

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'original_vqe_8_4_10_100.qasm'
EXPECTED_GIT_BLOB='cdcb957d2c8f9a9f25fa5a530b80d8b6e7bd8af5'

@dataclass(frozen=True)
class Op:
    kind:str
    qubits:tuple[int,...]
    params:tuple[float,...]=()
    cx_index:int|None=None


def git_blob_sha(data:bytes)->str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def eval_angle(expr:str)->float:
    tree=ast.parse(expr.strip(),mode='eval')
    def go(n):
        if isinstance(n,ast.Expression): return go(n.body)
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)): return float(n.value)
        if isinstance(n,ast.Name) and n.id=='pi': return math.pi
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            v=go(n.operand); return v if isinstance(n.op,ast.UAdd) else -v
        if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            a,b=go(n.left),go(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            return a/b
        raise ValueError(f'unsafe angle expression: {expr!r}')
    return float(go(tree))


def parse_source()->list[Op]:
    data=SOURCE.read_bytes()
    assert git_blob_sha(data)==EXPECTED_GIT_BLOB
    ops=[]; cxidx=0
    ure=re.compile(r'^u\((.*)\) q\[(\d+)\];$')
    cxre=re.compile(r'^cx q\[(\d+)\],q\[(\d+)\];$')
    for line in data.decode().splitlines():
        line=line.strip()
        if not line or line.startswith(('OPENQASM','include','qreg')):continue
        m=ure.match(line)
        if m:
            parts=[x.strip() for x in m.group(1).split(',')]
            assert len(parts)==3
            ops.append(Op('u',(int(m.group(2)),),tuple(eval_angle(x) for x in parts)))
            continue
        m=cxre.match(line)
        if m:
            ops.append(Op('cx',(int(m.group(1)),int(m.group(2))),(),cxidx));cxidx+=1;continue
        raise ValueError(f'unparsed source line: {line}')
    assert cxidx==71
    return ops


def u_matrix(theta,phi,lam):
    c=math.cos(theta/2);s=math.sin(theta/2)
    return np.array([[c,-cmath.exp(1j*lam)*s],[cmath.exp(1j*phi)*s,cmath.exp(1j*(phi+lam))*c]],dtype=np.complex128)


def apply_u(state:np.ndarray,n:int,q:int,U:np.ndarray)->None:
    bit=1<<q
    for base in range(1<<n):
        if base&bit:continue
        i0=base;i1=base|bit
        a=state[i0].copy();b=state[i1].copy()
        state[i0]=U[0,0]*a+U[0,1]*b
        state[i1]=U[1,0]*a+U[1,1]*b


def apply_cx(state:np.ndarray,n:int,c:int,t:int)->None:
    cb=1<<c;tb=1<<t
    for i in range(1<<n):
        if (i&cb) and not(i&tb):
            j=i|tb;state[[i,j]]=state[[j,i]]


def apply_swap(state:np.ndarray,n:int,a:int,b:int)->None:
    if a==b:return
    ab=1<<a;bb=1<<b
    for i in range(1<<n):
        ba=bool(i&ab);bbv=bool(i&bb)
        if ba==bbv or ba:continue
        j=i^ab^bb;state[[i,j]]=state[[j,i]]


def simulate(n:int,ops:list[Op],initial:np.ndarray)->np.ndarray:
    st=initial.copy()
    for op in ops:
        if op.kind=='u': apply_u(st,n,op.qubits[0],u_matrix(*op.params))
        elif op.kind=='cx': apply_cx(st,n,*op.qubits)
        elif op.kind=='swap': apply_swap(st,n,*op.qubits)
        else: raise AssertionError(op.kind)
    return st


def qasm_angle(x:float)->str:
    return format(x,'.17g')


def build(route_name:str)->dict:
    source_ops=parse_source()
    route=json.loads((ROOT/route_name).read_text())
    bench=json.loads((ROOT/'benchmark.json').read_text())
    assert [(o.qubits[0],o.qubits[1]) for o in source_ops if o.kind=='cx']==[tuple(x) for x in bench['cx_gates']]

    pending=[[] for _ in range(8)]
    before=[{} for _ in range(71)]
    for op in source_ops:
        if op.kind=='u':pending[op.qubits[0]].append(op)
        else:
            a,b=op.qubits;before[op.cx_index][a]=pending[a];before[op.cx_index][b]=pending[b];pending[a]=[];pending[b]=[]
    tails=pending

    mapping={int(q):int(p) for q,p in route['initial_mapping'].items()}
    mapped=[];consumed_u=0;seen_cx=[]
    def emit_cx(idx1:int):
        nonlocal consumed_u
        idx=idx1-1;a,b=bench['cx_gates'][idx]
        for q in (a,b):
            for uop in before[idx][q]:
                mapped.append(Op('u',(mapping[q],),uop.params));consumed_u+=1
        mapped.append(Op('cx',(mapping[a],mapping[b]),(),idx));seen_cx.append(idx)
    for idx1 in route['schedule'][0]['executed_cx_1_based']:emit_cx(idx1)
    for (u,v),phase in zip(route['swaps'],route['schedule'][1:]):
        mapped.append(Op('swap',(u,v)))
        for q,p in list(mapping.items()):
            if p==u:mapping[q]=v
            elif p==v:mapping[q]=u
        for idx1 in phase['executed_cx_1_based']:emit_cx(idx1)
    for q in range(8):
        for uop in tails[q]:mapped.append(Op('u',(mapping[q],),uop.params));consumed_u+=1
    assert consumed_u==sum(o.kind=='u' for o in source_ops)==65
    assert len(seen_cx)==71 and len(set(seen_cx))==71

    orig_per=[[] for _ in range(8)];new_per=[[] for _ in range(8)]
    for o in source_ops:
        if o.kind=='cx':
            for q in o.qubits:orig_per[q].append(o.cx_index)
    for idx in seen_cx:
        for q in bench['cx_gates'][idx]:new_per[q].append(idx)
    assert orig_per==new_per

    active=sorted({p for p in route['initial_mapping'].values()}|{p for e in route['swaps'] for p in e})
    loc={p:i for i,p in enumerate(active)};n=len(active)
    assert 8 <= n <= 9

    U0=np.eye(1<<8,dtype=np.complex128)
    original_final=simulate(8,source_ops,U0)

    embed=np.zeros((1<<n,1<<8),dtype=np.complex128)
    initmap={int(q):loc[int(p)] for q,p in route['initial_mapping'].items()}
    for x in range(1<<8):
        y=0
        for q in range(8):
            if x>>q&1:y|=1<<initmap[q]
        embed[y,x]=1
    mapped_local=[Op(o.kind,tuple(loc[p] for p in o.qubits),o.params,o.cx_index) for o in mapped]
    actual=simulate(n,mapped_local,embed)

    finalmap={q:loc[p] for q,p in mapping.items()}
    expected=np.zeros_like(actual)
    for y in range(1<<8):
        py=0
        for q in range(8):
            if y>>q&1:py|=1<<finalmap[q]
        expected[py,:]=original_final[y,:]
    delta=actual-expected
    maxerr=float(np.max(np.abs(delta)))
    froerr=float(np.linalg.norm(delta))
    assert maxerr<2e-13,(maxerr,froerr)

    out=ROOT/f"mapped_{Path(route_name).stem}.qasm"
    with out.open('w') as f:
        f.write('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[54];\n')
        for o in mapped:
            if o.kind=='u':f.write(f"u({qasm_angle(o.params[0])},{qasm_angle(o.params[1])},{qasm_angle(o.params[2])}) q[{o.qubits[0]}];\n")
            elif o.kind=='cx':f.write(f"cx q[{o.qubits[0]}],q[{o.qubits[1]}];\n")
            else:f.write(f"swap q[{o.qubits[0]}],q[{o.qubits[1]}];\n")

    result={'route':route['id'],'source_git_blob_sha1':EXPECTED_GIT_BLOB,'active_physical_nodes':active,
            'source_u_gates':65,'source_cx_gates':71,'mapped_u_gates':65,'mapped_cx_gates':71,
            'mapped_swaps':len(route['swaps']),'all_logical_basis_inputs_verified':256,
            'max_absolute_amplitude_error':maxerr,'frobenius_error':froerr,
            'final_mapping':{str(q):p for q,p in mapping.items()},'mapped_qasm':out.name}
    (ROOT/f"full_unitary_{Path(route_name).stem}.json").write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('route',nargs='?',default='route.json');a=ap.parse_args()
    r=build(a.route);print('FULL_UNITARY_EQUIVALENCE_VERIFIED');print(json.dumps(r,indent=2))
