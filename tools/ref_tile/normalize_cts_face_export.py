#!/usr/bin/env python3
"""Normalize actual CTS face ETMs once, with explicit external-load RC basis.

An unqualified placement-estimated CTS export is never a CLOSED routed view.
A saved benchmark cap can remain embedded in placement RC after writer swaps
SDC loads; caller must identify that base cap instead of calling it intrinsic.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--view',required=True,type=Path)
    p.add_argument('--master',default='ot_qfd_vm_face_sn_e1')
    p.add_argument('--base-cap-ff',required=True,type=float)
    p.add_argument('--lef',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hier_contract'));import pinreg_audit as A
    ins=json.loads((a.view/'insertion.json').read_text())
    out={'scope':'UNROUTED actual standalone SN EN1 CTS candidate; placementRC; no CLOSED/adoption/S-slot-fit. Raw per-pin O-R/S+R, no boundary-extrema addback. First ETM load table point; see explicit base capacitance.',
         'placement_RC_base_external_output_cap_fF':a.base_cap_ff,'load_policy':'Original benchmark80fF remains required and unchanged; base0 is a separate curve/diagnostic context, never a timing waiver.',
         'master':a.master,'orientation':{'d':'S','q':'N','clk':'W','me_e':'W'},'outline_um':[129.6,12.96],'corner_refs':{},'pins':{},'summary':{},'hashes':{}}
    for c in ('tt','ff','ss'):
        f=a.view/f'{a.master}_{c}.lib';out['hashes'][f.name]=hashlib.sha256(f.read_bytes()).hexdigest();lib=A.parse_lib(f);refs=A.clock_refs(lib,ins,c)
        assert list(refs)==['clk'];R=refs['clk']['rise'];out['corner_refs'][c]=refs['clk'];norm={}
        for pin,pin_data in lib['pins'].items():
            if not (re.fullmatch(r'[dq]\[\d+\]',pin) or pin=='me_e'):continue
            os=[];ls=[];ss=[];hs=[]
            for typ,rel,t in pin_data['arcs']:
                assert rel=='clk'
                if typ=='rising_edge':vs=[t[k][0] for k in ('cell_rise','cell_fall') if t.get(k)];os+=vs;ls+=vs
                if typ=='setup_rising':ss += [x for k in ('rise_constraint','fall_constraint') for x in t.get(k,[])]
                if typ=='hold_rising':hs += [x for k in ('rise_constraint','fall_constraint') for x in t.get(k,[])]
            norm[pin]={'O_ps':max(os) if os else None,'o_ps':max(os)-R if os else None,'l_ps':min(ls)-R if ls else None,
                       'S_ps':max(ss) if ss else None,'s_ps':max(ss)+R if ss else None,'h_ps':max(hs)-R if hs else None}
        assert sum(x.startswith('q[') for x in norm)==512 and sum(x.startswith('d[') for x in norm)==512
        qp=[(n,m['o_ps']) for n,m in norm.items() if n.startswith('q[')];dp=[(n,m['s_ps']) for n,m in norm.items() if n.startswith('d[')]
        out['pins'][c]=norm;out['summary'][c]={'R_ps':R,'q_max':max(qp,key=lambda z:z[1]),'q_gt220':sum(x>220 for _,x in qp),
                                            'd_max':max(dp,key=lambda z:z[1]),'d_gt190':sum(x>190 for _,x in dp),'me_e':norm['me_e']}
    out['hashes'][a.lef.name]=hashlib.sha256(a.lef.read_bytes()).hexdigest();out['hashes']['insertion.json']=hashlib.sha256((a.view/'insertion.json').read_bytes()).hexdigest()
    out['lef_pins']={}
    for m in re.finditer(r'\bPIN\s+(\S+)(.*?)\n\s*END\s+\1\s',a.lef.read_text(),re.S):
        r=re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',m[2])
        if r:
            x,y,X,Y=map(float,r.groups());out['lef_pins'][m[1]]=[(x+X)/2,(y+Y)/2]
    a.out.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out['summary'],indent=2))


if __name__=='__main__':main()
