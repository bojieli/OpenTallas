#!/usr/bin/env python3
"""Emit the existing boot-aware Engram die master with actual E/H0/H1 hard cores.

The boot decoder and all other source modules are preserved byte for byte.
The same-cycle split implementation is copied from its authoritative RTL.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

def emit(boot_source, split_source, *, mutant=0):
    if mutant not in (0, 1, 2):
        raise ValueError('unsupported split mutant')
    top = list(re.finditer(r'\bmodule\s+dsdv_eng_rr\s*#\s*\(', boot_source))
    sp = list(re.finditer(r'\bmodule\s+dsdv_eng_rr_split\s*#\s*\(', split_source))
    if len(top) != 1 or len(sp) != 1:
        raise ValueError('expected one real boot die master and one split master')
    prefix, old = boot_source[:top[0].start()], boot_source[top[0].start():]
    if len(re.findall(r'\bendmodule\b', old)) != 1:
        raise ValueError('boot master must be final source module')
    if 'dsdv_eng_cfg' not in old or '.cfg_en(en)' not in old or '.cfg_rank(rk)' not in old:
        raise ValueError('real CTL boot decoder is required; no configuration straps')
    cut = re.search(r'\n\s*dsdv_eng_rr_c\s*#', old)
    if not cut:
        raise ValueError('expected monolithic core instantiation after boot decoder')
    body = split_source[sp[0].start():]
    close = body.find('\n);')
    if close < 0:
        raise ValueError('cannot identify split port-list boundary')
    body = body[close + 4:body.index('endmodule')]
    for name in ('u_e', 'u_h0', 'u_h1'):
        if not re.search(r'\b'+name+r'\s*\(', body):
            raise ValueError('missing actual hard core '+name)
    for a,b in [('cfg_en','en'),('cfg_layer','ly'),('cfg_rank','rk')]:
        body = re.sub(r'(?<!\.)\b'+a+r'\b', b, body)
    return prefix + old[:cut.start()] + '\n    localparam integer SPLIT_MUT = '+str(mutant)+';\n' + body + '\nendmodule\n'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--boot-source',required=True);p.add_argument('--split-source',required=True)
    p.add_argument('--out',required=True);p.add_argument('--mutant',type=int,default=0)
    a=p.parse_args();bs=Path(a.boot_source).read_text();ss=Path(a.split_source).read_text()
    out=emit(bs,ss,mutant=a.mutant);o=Path(a.out);o.parent.mkdir(parents=True,exist_ok=True);o.write_text(out)
    rec={'boot_source':a.boot_source,'split_source':a.split_source,'cycles_added':0,
         'status_cycles_added':0,'mutant':a.mutant,'actual_cores':['u_e','u_h0','u_h1'],
         'required_defines':['OT_S81ENG_RR_N32'],'preserves_boot_decoder':True,
         'sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in [('boot',bs),('split',ss),('emitted',out)]}}
    o.with_suffix('.adoption.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec))
if __name__=='__main__':main()
