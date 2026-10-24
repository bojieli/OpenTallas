#!/usr/bin/env python3
"""XT1 numeric and fixed-calendar negative control, preserving the numeric checker verdicts.

The HR-skew mutant can remain numerically exact while delivering every result one edge late.
Compare actual column issue/result edges to the nominal run: a static consumer calendar cannot
slide with the mutant. This is a sensitivity check, not a claim of timing closure or plan binding.
"""
import argparse,json
from pathlib import Path

def evaluate(n, m):
    sides=['near','far'] if 'near' in n else [None]
    differences=[];valid=True;numeric_caught=False
    for side in sides:
        nn=n[side] if side else n;mm=m.get(side,{}) if side else m
        valid &= nn.get('verdict')=='PASS'
        numeric_caught |= mm.get('verdict')=='FAIL'
        ops=nn.get('per_op',{})
        valid &= set(ops)=={'qkv','o','gu','down'}
        for op,v in ops.items():
            for key in ('cw_go','rs_edges'):
                edges=v.get(key,[]);other=mm.get('per_op',{}).get(op,{}).get(key,[])
                valid &= bool(edges)
                if edges != other:
                    differences.append(dict(side=side or 'near',op=op,signal=key,nominal_edges=edges,mutant_edges=other))
    caught=numeric_caught or bool(differences)
    result=dict(verdict='PASS' if valid and caught else 'FAIL',scope='nominal numeric exactness and static consumer-edge mutant sensitivity; not physical signoff or generated-die token pass',nominal_numeric_pass=bool(valid),mutant_numeric_verdict=m.get('verdict'),mutant_caught=bool(caught),mutant_detection='numeric mismatch' if numeric_caught else 'fixed consumer edges differ' if differences else 'NOT CAUGHT',differences=differences)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--nominal",type=Path,required=True);ap.add_argument("--mutant",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    result=evaluate(json.loads(a.nominal.read_text()),json.loads(a.mutant.read_text()))
    a.out.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='differences'}));return 0 if result['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
