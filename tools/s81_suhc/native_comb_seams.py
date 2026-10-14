#!/usr/bin/env python3
"""Measured-view screen of explicit internal HC comb seams in packing request.

Checks per-bit pin Manhattan distances. Timing is conservative per-bus worst
arcs; a pass is preparation evidence, never a full routed parent proof.
"""
import argparse
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/hier_contract'))
import pinreg_pairs
import pair_check


def pins(leaf):
    view = ROOT/leaf['view']
    text = (view/(leaf['cell']+'.lef')).read_text()
    out = {}
    for name, block in re.findall(r'\bPIN\s+(\S+)(.*?)\n\s*END\s+\1\s', text, re.S):
        rects = re.findall(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', block)
        if rects:
            x0,y0,x1,y1 = map(float,rects[0])
            ox,oy = leaf['origin_um']
            out[name] = (ox+(x0+x1)/2,oy+(y0+y1)/2)
    return out


def screen(plan):
    by = {x['instance']:x for x in plan['instances']}
    geom = {k:pins(v) for k,v in by.items()}
    table = {v['cell']:pinreg_pairs.extract(v['view']) for v in by.values()}
    assert all(table.values()), 'Missing measured timing view'
    die = pair_check.Die(table, {k:v['cell'] for k,v in by.items()})
    rows=[]

    def seam(ai,ap,bi,bp,width=None,ao=0,bo=0):
        distances=[]
        missing=[]
        for bit in range(width or 1):
            an=f'{ap}[{bit+ao}]' if width else ap
            bn=f'{bp}[{bit+bo}]' if width else bp
            if an not in geom[ai] or bn not in geom[bi]:
                missing.append([an,bn]); continue
            a,b=geom[ai][an],geom[bi][bn]
            distances.append(abs(a[0]-b[0])+abs(a[1]-b[1]))
        if missing:
            rows.append(dict(a=[ai,ap],b=[bi,bp],status='MISSING_PIN',missing=missing[:4],missing_bits=len(missing)))
            return
        L=max(distances)
        r=pair_check.check(die,dict(a=(ai,by[ai]['cell'],ap),b=(bi,by[bi]['cell'],bp),um=L))
        rows.append(dict(a=[ai,ap],b=[bi,bp],bits=len(distances),worst_manhattan_um=round(L,3),timing=r))

    for p,w in (('v',7),('d',1128)):
        seam('u_seq','c_f'+p,'u_pd.u_f8',p+'_i',w)
        seam('u_pd.u_f8',p+'_o','u_pd.u_f5r1',p+'_i',w)
        seam('u_pd.u_f5r1',p+'_o','u_cf','f'+p+'_i',w)
    seam('u_cr.u_core','crd_o','u_pd.u_f5r1','r_i',2156)
    seam('u_pd.u_f5r1','r_o','u_pd.u_r6','d_i',2156)
    seam('u_pd.u_r6','d_o','u_pd.u_r5','d_i',2156)
    seam('u_pd.u_r5','d_o','u_rx','c_rd',108)
    for p,w in (('crv_o',8),('cpi_o',8),('ex1_o',512)):
        ip={'crv_o':'v_i','cpi_o':'p_i','ex1_o':'e_i'}[p]
        seam('u_cr.u_core',p,'u_cr.g_meta.u_m',ip,w)
    seam('u_cr.g_meta.u_m','v_o','u_rx','c_rv',8)
    seam('u_cr.g_meta.u_m','p_o','u_nt','c_pi',8)
    seam('u_cr.g_meta.u_m','e_o','u_nt','c_ex',512)
    seam('u_seq','ngo','u_nt','ngo_i')
    for a,b,w in (('ss_v','t_ssv',None),('ss','t_ss',32),('tflt','t_flt',None)):
        seam('u_nt',a,'u_seq',b,w)
    for a,b,w in (('j_v','j_v',None),('kind','j_kind',3),('base','j_base',14),('f_q','j_fq',None),
                  ('f_y','j_fy',None),('j_end','j_end',None),('fault','j_flt',None),('j_civ','j_civ',None)):
        seam('u_seq',a,'u_rx',b,w)
    for p in ('x_wdone','x_pob','x_f1','x_f4'):
        seam('u_rx',p,'u_seq',p)
    seam('u_cf','yfl','u_seq','c_yfl')
    for u in range(4):
        aq=f'g_aq[{u}].u_caq'
        seam('u_rx','o_run',aq,'run')
        seam('u_rx','o_kind',aq,'kind',3)
        seam('u_rx',f'o_rv[{u}]',aq,'rv_u')
        for a,b,w,off in (('vo','a_vo',None,u),('f','a_f',None,u),('e','a_e',10,u*10),('iqo','a_iq',24,u*24)):
            # Scalar lane destinations are explicitly indexed rather than
            # relying on bus-wide geometry for a one-bit net.
            if w is None:
                seam(aq,a,'u_rx',f'{b}[{off}]')
            else:
                seam(aq,a,'u_rx',b,w,bo=off)
    return dict(schema='opentallas.s81.hc.native_comb_seam_screen.v1',
                status='INCOMPLETE_INTERNAL_SEAM_SCREEN: external root/VM/chain pins and q-data joins remain',
                geometry_model='actual closed LEF first pin rectangle, Manhattan; routing can only add length',
                timing_model='measured TT/FF worst bus arcs and insertion compensation; no placeholder sides',
                seams=rows, fail_count=sum(r.get('timing',{}).get('status')=='fail' for r in rows),
                missing_count=sum(r.get('status')=='MISSING_PIN' for r in rows))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan',type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();r=screen(json.loads(a.plan.read_text()));a.out.write_text(json.dumps(r,indent=2)+'\n')
    print('seams',len(r['seams']),'failed',r['fail_count'],'missing',r['missing_count'])
