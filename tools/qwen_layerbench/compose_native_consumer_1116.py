#!/usr/bin/env python3
"""Compose current native S8 consumer timing through existing dependency hooks.

The measured consumer profile owns HR/XPF readiness.  Tile arithmetic/delivery,
installation and final physical transport remain independently qualified inputs.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import dv_lower as D
import dv_layer as L
import dv_lower_xhead as X

BOUNDARY={'qkv':'pre_qkv','o':'pre_o','gu':'pre_gu','down':'pre_down'}

def compose(ages_path,stage=1,matrix_ages_path=None,phase_profile_path=None):
    ages_path=Path(ages_path)
    a=X.load_ages(ages_path)
    if D.SLICE_RTL!='s8' or a.get('slice_rtl')!='s8' or a.get('status')!='PASS_COMPONENT_COMPOSED':
        raise ValueError('native S8 selected-component profile required')
    selected_inputs={}
    if matrix_ages_path is not None or phase_profile_path is not None:
        if matrix_ages_path is None or phase_profile_path is None:
            raise ValueError('native round96 tile and actual AR phase must be selected together')
        mp,pp=Path(matrix_ages_path),Path(phase_profile_path)
        mat=json.loads(mp.read_text());phase=json.loads(pp.read_text())
        if mat.get('schema')!='opentallas.qwen.native-matrix-ages.v1' or not mat.get('native_component_profile'):
            raise ValueError('actual native matrix component profile required')
        a=dict(a,tile=dict(mat['tile'],native_round96=True))
        a=X.native_phase_profile(a,phase)
        selected_inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (mp,pp)}
    su=D.load_ages();D.check_memory_profile(su, "DV_SU_AGES")
    if not su.get('composition',{}).get('native_zero_parent_transport'):
        raise ValueError('this composition requires the explicit native zero-parent SU profile')
    delays={};history=[]
    for iteration in range(len(BOUNDARY)+2):
        edges={b:[dict(label='measured native x consumer readiness',cycles=n,grade='COMPONENT_COMPOSED',source=str(ages_path))] for b,n in delays.items()}
        comp=L.compose(stage=stage,die_edges=edges)
        low=X.lower_layer(comp,a,stage)
        if low['errors']:raise ValueError(low['errors'])
        history.append(dict(iteration=iteration,edges=dict(delays),go_delays={c['matvec']:c['go_delay'] for c in low['consumers']}))
        extra={}
        for c in low['consumers']:
            if c['go_delay']:
                if c['matvec']=='qkv+1':raise ValueError('next-stage recurrence requires explicit period recomposition')
                b=BOUNDARY[c['matvec']];extra[b]=max(extra.get(b,0),c['go_delay'])
        if not extra:break
        for b,n in extra.items():delays[b]=delays.get(b,0)+n
    else:raise ValueError('native consumer dependency composition did not converge')
    if comp['calendar']['clashes'] or comp['calendar']['occupancy_clashes']:
        raise ValueError('recomposed native calendar has a command or occupancy clash')
    low['ages']=str(ages_path)
    comp['native_xhead_consumer']=dict(status='PASS_COMPONENT_COMPOSED',profile=str(ages_path),profile_sha256=hashlib.sha256(ages_path.read_bytes()).hexdigest(),dependency_edges=delays,iterations=history,lowering=low,selected_native_inputs=selected_inputs,installed=False,bound_transport_qualified=False)
    # A concrete consumer lowering supersedes only the old absence-of-lowering warning.
    comp['gaps']=[g for g in comp['gaps'] if not g.startswith('COLUMN-HEAD x CONSUMER:')]
    comp['gaps'].append('NATIVE HR/XPF INSTALL: measured current-source lowering and producer dates are composed; emitted ME/XPF/monitor rows still require selected native table installation and final transport.')
    return comp

def main():
    p=argparse.ArgumentParser();p.add_argument('--ages',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--matrix-ages',type=Path);p.add_argument('--phase-profile',type=Path);p.add_argument('--stage',default=1,type=int);a=p.parse_args()
    r=compose(a.ages,a.stage,a.matrix_ages,a.phase_profile);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps(dict(layer=r['composition']['layer_latency'],chained=r['composition']['chained_period'],cold=r['composition']['l0_cold'],dependency_edges=r['native_xhead_consumer']['dependency_edges'],entries=r['calendar']['entries'],clashes=r['calendar']['clashes'],occupancy=r['calendar']['occupancy_clashes'])))
if __name__=='__main__':main()
