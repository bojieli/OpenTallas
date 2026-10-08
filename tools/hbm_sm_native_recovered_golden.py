#!/usr/bin/env python3
"""Regenerate all NC8 golden rows from the exact recovered native producer.

No ISA conversion: compare original seq/lines/X payload bytes before admitting
these references. Arithmetic mode and RNG are identical to cmd_run.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import dshbm_sm_pq_seq as P
import hdc_golden_v41 as V

def generate(source,out):
    source,out=Path(source),Path(out);V.set_arith('chunk8');rng=np.random.default_rng(20261005)
    ops,deps=P.seq_ops('stress',False);seq=[];lines=[];xs=[];refs=[];resident=None;ptr=0
    for i,((tag,fmt,k,rows,load),dep) in enumerate(zip(ops,deps)):
        if load:
            g=P.MS.gen_op('v41_'+fmt,rows,k,8,rng);resident=g;rbase=ptr;ptr=(ptr+g['Gn']*g['c'])%128
        else:g=P.MS.gen_op('v41_'+fmt,rows,k,8,rng,X=resident['X'])
        seq += [rows,g['c'],g['Gn'],g['fmt'],len(g['lines']),1,load,g['Gn']*g['c'],dep,rbase]
        lines += list(map(int,g['lines']))
        if load:xs += list(map(int,g['xw']))
        for row in range(rows):
            refs.append((i,row,sum(int(P.G.bits(g['gold'][n][row]))<<(32*n) for n in range(8))))
    for name,values in [('seq.hex',seq),('lines.hex',lines),('x.hex',xs)]:
        actual=[int(x,16) for x in (source/name).read_text().split()]
        if actual!=values:raise ValueError('recovered source differs: '+name)
    out.mkdir(parents=True,exist_ok=False)
    (out/'golden_rows.txt').write_text(''.join(f'{i} {r} {v:064x}\n' for i,r,v in refs))
    receipt=dict(status='PASS',scope='original generator exact recovered payload equality; all8 golden columns; no RTL simulation',records=len(ops),rows=len(refs),source_sha256={str(source/n):hashlib.sha256((source/n).read_bytes()).hexdigest() for n in ['seq.hex','lines.hex','x.hex']})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();generate(a.source,a.out)
