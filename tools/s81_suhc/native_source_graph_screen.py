#!/usr/bin/env python3
"""Screen every elaborated native HC internal bit using its actual pin and arc.

Only the explicit common-boundary phi-R delivery request is assumed. Actual
external producer/net/clock/reset bindings and routed RC remain unqualified.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import native_comb_seams as S
import native_actual_family_screen as F
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pinreg_audit as A
import pair_check as P


def screen(plan, joins, manifest, out):
    leaves={l['instance']:l for l in plan['instances']};geometry={};metrics={};refs={}
    for name,l in leaves.items():
        if l.get('pin_assignment'):
            q=json.loads((ROOT/l['pin_assignment']).read_text());w,h=l['outline_um'];ox,oy=l['origin_um'];g={}
            for bus,p in q['ports'].items():
                for bit,(face,layer,offset,depth) in enumerate(p['per_bit']):
                    n=bus if p['bits']==1 else f'{bus}[{bit}]'
                    x,y={'N':(offset,h-depth/2),'S':(offset,depth/2),'W':(depth/2,offset),'E':(w-depth/2,offset)}[face];g[n]=(ox+x,oy+y)
            geometry[name]=g
        else:geometry[name]=S.pins(l)
        cell=l['cell']
        if cell in metrics:continue
        vp=ROOT/manifest['leaf_interfaces'][cell]['actual_interface_lib'];view=vp.parent
        assert hashlib.sha256(vp.read_bytes()).hexdigest()==manifest['leaf_interfaces'][cell]['lib_sha256']
        insertion=view/('provisional_insertion.json' if (view/'provisional_insertion.json').exists() else 'insertion.json')
        ins=json.loads(insertion.read_text())
        if cell=='ot_s81_hc_cseq':
            cc=ROOT/'results/rtl/s81_suhc_20261013/native_repack_v7_v9/cseq_closed_clock_recovery/controller_boundary_references.json'
            ins['clock_measurements']={'cck':json.loads(cc.read_text())}
        metrics[cell]={};refs[cell]={}
        for corner in ('tt','ff'):
            lib=A.parse_lib(view/(cell+'_'+corner+'.lib'));r=A.clock_refs(lib,ins,corner)
            refs[cell][corner]=r;metrics[cell][corner]=A.pin_metrics(lib,r)
    rows=[];groups=[]
    for join in joins['joins']:
        if not join['scope'].startswith('internal'):continue
        ai,ap=join['a'];bi,bp=join['b'];ac=leaves[ai]['cell'];bc=leaves[bi]['cell'];bucket=[]
        for ab,bb,net in join['bits']:
            an=ap if manifest['leaf_interfaces'][ac]['ports'][ap]['scalar'] else f'{ap}[{ab}]'
            bn=bp if manifest['leaf_interfaces'][bc]['ports'][bp]['scalar'] else f'{bp}[{bb}]'
            assert an in geometry[ai] and bn in geometry[bi], ('Missing actual pin',ai,an,bi,bn)
            ax,ay=geometry[ai][an];bx,by=geometry[bi][bn];L=abs(ax-bx)+abs(ay-by)
            a=metrics[ac]['tt'][an];b=metrics[bc]['tt'][bn];af=metrics[ac]['ff'][an];bf=metrics[bc]['ff'][bn]
            row={'a':[ai,an],'b':[bi,bn],'net_bit':net,'manhattan_um':round(L,4)}
            if a['out'] is None or b['inp'] is None:
                row.update(status='NOARC_REQUIRES_ACTUAL_CONSTANT_OR_UNUSED_PROOF',launch_arc=a['out'],capture_arc=b['inp'])
            else:
                assert a['clk']==['sk'] and b['clk']==['sk'], 'actual related clock or edge needs separate check'
                ra=refs[ac]['tt']['sk']['rise'];rb=refs[bc]['tt']['sk']['rise'];deep=max(ra,rb)>P.LEVEL_PS
                budget=P.T_PS-P.U_SETUP-(P.SKEW_DEEP if deep else P.SKEW_SAME)
                setup=budget-a['out']-b['inp']-P.W_TT*L
                hold=None if af['lmin'] is None or bf['hold'] is None else af['lmin']+P.W_FF_CREDIT*L-bf['hold']-P.HOLD_TREE
                row.update(status='pass' if setup>=0 and hold is not None and hold>=0 else 'fail',setup_ps=round(setup,4),hold_ps=None if hold is None else round(hold,4),launch_ps=round(a['out'],4),capture_ps=round(b['inp'],4),budget_ps=round(budget,4))
            rows.append(row);bucket.append(row)
        judged=[r for r in bucket if 'setup_ps' in r]
        groups.append({'a':join['a'],'b':join['b'],'bits':len(bucket),'judged_bits':len(judged),'noarc_bits':len(bucket)-len(judged),'min_setup_ps':min((r['setup_ps'] for r in judged),default=None),'min_hold_ps':min((r['hold_ps'] for r in judged if r['hold_ps'] is not None),default=None),'fail_bits':sum(r['status']=='fail' for r in bucket)})
    out.mkdir(parents=True,exist_ok=True)
    with gzip.open(out/'internal_actual_bit_rows.json.gz','wt') as f:json.dump(rows,f,separators=(',',':'))
    judged=[r for r in rows if 'setup_ps' in r]
    summary={'schema':'opentallas.s81.native_hc_actual_source_bit_screen.v1','status':'CONDITIONAL common-phi per-corner phi-R request only; full external/source/reset/routed checks remain',
             'actual_internal_bits':len(rows),'actual_internal_bus_joins':len(groups),'judged_bits':len(judged),
             'noarc_bits':len(rows)-len(judged),'fail_bits':sum(r['status']=='fail' for r in rows),
             'min_setup_ps':min(r['setup_ps'] for r in judged),'min_hold_ps':min(r['hold_ps'] for r in judged if r['hold_ps'] is not None),
             'groups':groups,'route_admission':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='groups'},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--joins',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();screen(json.loads(a.plan.read_text()),json.loads(a.joins.read_text()),json.loads(a.manifest.read_text()),a.out)
