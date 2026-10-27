#!/usr/bin/env python3
"""Restore simulation image identities from exact canonical source; no topology or cycle change."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from qxpq_go_boundary import _group, _named
PAT = re.compile(r"(?m)^[ \t]*(ot_v41_rom_elem_q_qxpq_w10(?:_gb)?|ot_rom_4096x72_m8|dsfd_bf_col|dsfd_bf_front_roots)\b")

def calls(text):
    for m in PAT.finditer(text):
        pos=m.end()
        while text[pos].isspace(): pos+=1
        p0=p1=None
        if text[pos]=='#':
            p0=text.index('(',pos);p1=_group(text,p0);pos=p1
        n=re.match(r'\s*(\w+)\s*\(',text[pos:])
        if not n: raise ValueError('unsupported instance syntax')
        c0=pos+n.end()-1;c1=_group(text,c0)
        yield dict(module=m.group(1).removesuffix('_gb'),name=n.group(1),p0=p0,p1=p1,
                   insert=m.end(),params=_named(text[p0+1:p1-1]) if p0 is not None else {},
                   ports=text[c0:c1])

def restore(actual,reference):
    refs={}
    for c in calls(reference):
        key=(c['module'],c['name'])
        if 'INSTANCE' not in c['params']:raise ValueError('reference identity missing: '+str(key))
        expr=c['params']['INSTANCE'][2]
        if key in refs and refs[key]!=expr:raise ValueError('ambiguous reference identity')
        refs[key]=expr
    edits=[];rows=[];shapes=[]
    for c in calls(actual):
        key=(c['module'],c['name'])
        if key not in refs:raise ValueError('actual call absent from reference: '+str(key))
        expr=refs[key]
        old=c['params'].get('INSTANCE')
        if old and old[2]!=expr:raise ValueError('image identity differs from canonical: '+str(key))
        if not old:
            if c['p1'] is None:edits.append((c['insert'],' #(.INSTANCE('+expr+'))'))
            else:edits.append((c['p1']-1,(', ' if c['params'] else '')+'.INSTANCE('+expr+')'))
        shapes.append({k:v[2] for k,v in c['params'].items() if k!='INSTANCE'})
        rows.append(dict(module=c['module'],instance=c['name'],expression=expr,
                         ports_sha256=hashlib.sha256(c['ports'].encode()).hexdigest()))
    if not rows:raise ValueError('no image-backed calls')
    for pos,s in sorted(edits,reverse=True):actual=actual[:pos]+s+actual[pos:]
    # Only the INSTANCE named parameter may change; ports and all shape parameters remain exact.
    for before,shape,after in zip(rows,shapes,calls(actual)):
        if shape!={k:v[2] for k,v in after['params'].items() if k!='INSTANCE'}:raise ValueError('shape change')
        if before['ports_sha256']!=hashlib.sha256(after['ports'].encode()).hexdigest():raise ValueError('port change')
    return actual,dict(schema='opentallas.gb_image_identity.v1',bindings=rows,restored=len(edits),
                      added_cycles=0,hardware_changed=False,native_provider_qualified=False)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--actual',type=Path,required=True);ap.add_argument('--reference',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    text,receipt=restore(a.actual.read_text(),a.reference.read_text())
    receipt['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.actual,a.reference]}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text)
    a.out.with_suffix('.identity.json').write_text(json.dumps(receipt,indent=1)+'\n')
if __name__=='__main__':main()
