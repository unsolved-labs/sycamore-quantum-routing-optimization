#!/usr/bin/env python3
"""Dependency-free verifier for a route certificate in this package."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument('route',nargs='?',default='route.json')
    args=ap.parse_args()
    root=Path(__file__).resolve().parent
    bench=json.loads((root/'benchmark.json').read_text())
    route=json.loads((root/args.route).read_text())
    gates=[tuple(x) for x in bench['cx_gates']]
    edge_set={frozenset(x) for x in bench['hardware_edges']}
    mapping={int(k):int(v) for k,v in route['initial_mapping'].items()}
    assert set(mapping)==set(range(bench['logical_qubits']))
    assert len(set(mapping.values()))==len(mapping)
    last=[None]*bench['logical_qubits'];pred=[]
    for i,(a,b) in enumerate(gates):
        p=set()
        if last[a] is not None:p.add(last[a])
        if last[b] is not None:p.add(last[b])
        pred.append(p);last[a]=last[b]=i
    done=set(); reconstructed=[]
    def closure():
        new=[];changed=True
        while changed:
            changed=False
            for i,(a,b) in enumerate(gates):
                if i in done or not pred[i].issubset(done):continue
                if frozenset((mapping[a],mapping[b])) in edge_set:
                    done.add(i);new.append(i+1);changed=True
        return new
    reconstructed.append(closure())
    for step,(u,v) in enumerate(route['swaps'],1):
        assert frozenset((u,v)) in edge_set, f'illegal SWAP {step}: {(u,v)}'
        lu=next((q for q,p in mapping.items() if p==u),None)
        lv=next((q for q,p in mapping.items() if p==v),None)
        if lu is not None:mapping[lu]=v
        if lv is not None:mapping[lv]=u
        assert len(set(mapping.values()))==len(mapping)
        reconstructed.append(closure())
    assert len(done)==len(gates), f'only {len(done)}/{len(gates)} CX gates routed'
    claimed=[x['executed_cx_1_based'] for x in route['schedule']]
    assert reconstructed==claimed, 'stored schedule does not match reconstructed schedule'
    print('VERIFIED')
    print('route:',route['id'])
    print('CX gates:',len(gates))
    print('SWAPs:',len(route['swaps']))
    print('added CX at 3 per SWAP:',3*len(route['swaps']))
    print('final mapping:', ' '.join(f'q{q}->p{mapping[q]}' for q in sorted(mapping)))

if __name__=='__main__':main()
