#!/usr/bin/env python3
"""Compute ASAP dependency depth of OpenQASM u/cx/swap files.

Each instruction has unit duration by default, matching ordinary circuit DAG depth.
With --decompose-swaps, each SWAP is replaced by CX(a,b), CX(b,a), CX(a,b).
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path

def parse(path:Path):
    ops=[]
    qre=re.compile(r'q\[(\d+)\]')
    for raw in path.read_text().splitlines():
        line=raw.strip()
        if line.startswith('u('): ops.append(('u',tuple(map(int,qre.findall(line)))))
        elif line.startswith('cx '): ops.append(('cx',tuple(map(int,qre.findall(line)))))
        elif line.startswith('swap '): ops.append(('swap',tuple(map(int,qre.findall(line)))))
    return ops

def depth(ops,decompose=False,two_qubit_only=False):
    last={}; counts={'u':0,'cx':0,'swap':0}; layers=[]
    for kind,qs in ops:
        counts[kind]+=1
        expanded=[(kind,qs)]
        if kind=='swap' and decompose:
            a,b=qs; expanded=[('cx',(a,b)),('cx',(b,a)),('cx',(a,b))]
        for k,q in expanded:
            if two_qubit_only and k=='u': continue
            layer=1+max((last.get(x,0) for x in q),default=0)
            for x in q:last[x]=layer
            layers.append((k,q,layer))
    return max(last.values(),default=0),counts

def main():
    ap=argparse.ArgumentParser();ap.add_argument('qasm',nargs='+');a=ap.parse_args()
    allres=[]
    for f in a.qasm:
        p=Path(f);ops=parse(p)
        native,c=depth(ops)
        decomposed,_=depth(ops,True)
        twoq,_=depth(ops,False,True)
        twoq_dec,_=depth(ops,True,True)
        r={'file':p.name,'operations':sum(c.values()),**c,'native_instruction_depth':native,
           'three_cx_swap_decomposed_depth':decomposed,'two_qubit_native_depth':twoq,
           'two_qubit_three_cx_swap_decomposed_depth':twoq_dec}
        allres.append(r);print(json.dumps(r,sort_keys=True))
    Path(__file__).resolve().parent.joinpath('depth_metrics.json').write_text(json.dumps(allres,indent=2)+'\n')
if __name__=='__main__':main()
