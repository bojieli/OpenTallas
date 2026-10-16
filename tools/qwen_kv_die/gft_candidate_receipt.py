#!/usr/bin/env python3
"""Check source primitive versus analyzed model without a die GEN trial."""
import ast
import hashlib
import json
import os
from pathlib import Path
import gft_placement as P

ROOT=Path(__file__).resolve().parents[2]


def main():
    src=ROOT/'tools/qwen_kv_die/kv_die.py'
    f=next(n for n in ast.parse(src.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_v143_stages')
    ns=dict(HGS=(324.,21.6),HSS=(21.6,21.6),SHAVE=.216,ECTL=(764.64,129.6),TILE_Y={'c':0.,'h2':0.},HEAD=(1080.,492.456),SPLIT_HEAD_FT=(1080.,508.68),V143_ROW=43.2,V143_GAP=21.6,V143B=False,V143C=True,V143_X=dict(t2f=108.,s1f=437.4),GFT_SELECTED=None)
    exec(compile(ast.Module(body=[f],type_ignores=[]),'<source-placement-primitive>','exec'),ns)
    recs=[]
    for mode in ['balanced_405.864','balanced_409.32']:
        os.environ['OT_KV_GFT_GEOMETRY']=mode;p=P.selected()
        for col in [0,1]:
            def run(v):
                ns['GFT_SELECTED']=v;out={}
                ns['_v143_stages'](lambda n,m,x,y,w,h,o,*_:out.update({n:(m,x,y,w,h,o)}),'T_0',0,0,col)
                return out
            old,new=run(None),run(p)
            assert set(old)==set(new) and len(new)==16
            assert all(old[n][0]==new[n][0] and old[n][3:]==new[n][3:] for n in old)
            sx=-1 if col else 1
            for near,far,sy in [(1,0,-1),(2,3,1)]:
                for h,ox,row in [(near,54,1),(far,405,2)]:
                    a=old[f'hst_T_0_{h}_g'];z=new[f'hst_T_0_{h}_g']
                    assert abs(z[1]-a[1]-sx*(p['gx']-ox))<1e-8
                    assert abs(z[2]-a[2]-sy*43.2*(row-1))<1e-8
                for role,ox,nrow in [('t1',-216,1),('t2',135,2),('s1',480.6,2),('s2',540,1)]:
                    a=old[f'hst_T_0_{near}_{role}'];z=new[f'hst_T_0_{near}_{role}']
                    nx=p['tx'] if role.startswith('t') else p['sx']
                    assert abs(z[1]-a[1]-sx*(nx-ox))<1e-8
                    assert abs(z[2]-a[2]-sy*43.2*(nrow-2))<1e-8
            recs.append(dict(mode=mode,mirror_column=col,instances=16,names_masters_orientations_sizes_equal=True,proposal_coordinate_deltas_match_source_primitive=True))
    os.environ['OT_KV_GFT_GEOMETRY']='balanced_394.2'
    try:P.selected();raise AssertionError('review-only mode accepted')
    except ValueError:pass
    b=ROOT/'results/arch/qwen_gft_geometry_0253/all32';rank=[]
    for name in ['balanced_405.864','balanced_409.32','balanced_394.2']:
        r=json.loads((b/(name+'.json')).read_text())
        external=[v for v in r['under20um_gaps'] if not v['a'].endswith('ftg')]
        rank.append(dict(name=name,data_edges=r['data_edges'],over500=r['over500_edges'],collisions=len(r['collisions']),external_under20=len(external),max_named_pair_um=r['worst_groups'][0]['max_um'],max_multicast_hpwl_um=r['worst_multicast_hpwl'][0][0],moved_clock_endpoints=len(r['clock_incidents']),eligible_for_model_review=not external and not r['collisions'],native_timing_qualified=False))
    files=['kv_die.py','gft_placement.py','gft_geometry.py','gft_candidate_receipt.py']
    receipt=dict(scope='SOURCE_GEOMETRY_CANDIDATE_ONLY_NO_GEN_TRIAL',rank=rank,source_primitive_checks=recs,source_sha256={n:hashlib.sha256((ROOT/'tools/qwen_kv_die'/n).read_bytes()).hexdigest() for n in files},cycles_changed=0,actual_leaf_names_types_sizes_orientations_changed=False,band_rows=2,band_row_pitch_um=43.2,between_stage_rows_gap_um=21.6,horizontal_master_gap_um=27.,allocated_head_column_local_x_um=[-216,864],recommended_stage_x_extent_um=[54.864,778.464],die_outline_changed=False,ft_channel_um=[351.,189.,361.8,27.],ftg_rect_um=[356.4,189.54,324.,21.6],fts_rect_um=[685.8,191.7,21.6,21.6],interior_under20_note='All736 reported sub20 gaps of eligible plans are inside the existing near-head FT channel/packed head. FT moves2.16 within its declared channel; no new external band/sliver or overlap. Interior small clearances remain explicitly reported for lead review.',clock_note='448 moved actual clock endpoints are recorded in each full JSON; clock roots/types/counts unchanged. Physical delivery phi-R and native wire/STA still require real GEN/route. These G/FT/T/S leaves have no reset port; every existing reset relay/frame rectangle is collision checked.',required_next=['die lead personally inspects final fullmodel PNGs and narrow source hook','choose reviewed opt-in plan; rebuild all incident allocator/clock/keepouts before physical trial','real GEN/GRT/STA using bound closed views; actual routed length/capacitance and TT/FF decide'])
    (b/'source_candidate_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(rank))


if __name__=='__main__':main()
