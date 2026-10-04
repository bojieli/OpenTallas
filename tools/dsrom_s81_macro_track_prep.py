#!/usr/bin/env python3
"""S81 actual retained-object pin/PG preparation under Maxwell; never invokes physical tools.
Optional --placements and --channels consume actual Maxwell JSON objects unchanged.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_s81_macro_track_prep_20261004'
INPUT=BASE/'inputs'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())


def lattice(residues,track_pitch,site_pitch):
    period=math.lcm(track_pitch,site_pitch)
    return dict(period_nm=period,origin_residues_nm=[i for i in range(0,period,site_pitch) if i%track_pitch in residues])


def selected_rows(path, key):
    r=read(path)
    if not isinstance(r,dict) or r.get('stages')!=81 or r.get('selection_commit')!='73851317fd9b4fb86c56f6ff760e29981ec610f2':
        raise ValueError('only Claude738 selected S81 object manifest is accepted')
    return r[key]


def channel_count(low,high,pitch,residues,blocked):
    if low>high or pitch<=0:raise ValueError('invalid channel bounds')
    tracks={q for r in residues for q in range(low+(r-low)%pitch,high+1,pitch)}
    denied={q for q in tracks if any(a<=q<=b for a,b in blocked)}
    return dict(total_tracks=len(tracks),blocked_tracks=len(denied),available_tracks=len(tracks-denied))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--placements',type=Path,help='actual Maxwell placed instance records, no synthetic coordinates')
    ap.add_argument('--channels',type=Path,help='actual Maxwell layer corridor and PG/clock exclusion records')
    a=ap.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    s=importlib.util.spec_from_file_location('alignment',INPUT/'tools/check_macro_track_alignment.py')
    align=importlib.util.module_from_spec(s);s.loader.exec_module(align)
    choice=read(INPUT/'claude738_model.json')
    assert choice['decision']['area']['stages']==81 and choice['decision']['area']['pairs']==2417
    price=choice['priced']['S81_ragged_RD64_replicated']
    owner=read(INPUT/'maxwell_s81_selected.json')
    assert owner['S81']['stages']==81 and owner['S81']['total_dies']==368
    objects=read(INPUT/'actual_geometry_objects.json')
    rows=[];macros={}
    for r in objects:
        p=INPUT/r['local_path'];assert sha(p)==r['sha256']
        text=gzip.decompress(p.read_bytes()).decode() if p.suffix=='.gz' else p.read_text()
        for m in align.parse_lef(text):
            macros[m['name']]=m
            audit=align.audit_macro(m,align.ASAP7_TRACKS_NM,align.ASAP7_LAYERS,str(p.relative_to(BASE)))
            joint={}
            for layer,rule in audit['summary'].items():
                axis='y' if align.ASAP7_LAYERS[layer][0]=='H' else 'x'
                pitch,_=align.track_residues(align.ASAP7_TRACKS_NM[layer],axis)
                grid=align.ROW_Y_NM if axis=='y' else align.SITE_X_NM
                joint[layer]={o:lattice(res,pitch,grid) for o,res in rule['origin_rule_mod_track_nm'].items()}
            supplies=[dict(pin=p['name'],use=p['use'],layer=layer,bbox_local_nm=list(rect))
                      for p in m['pins'] if p['use'] in ('POWER','GROUND') for layer,rect in p['rects']]
            rows.append(dict(role=r['role'],grade=r['grade'],source_path=r['path'],sha256=r['sha256'],
                macro=m['name'],size_nm=[m['W'],m['H']],alignment=audit,joint_site_track_lattices=joint,
                actual_supply_rectangles=supplies,selected=False,
                native_supply_access_layers=sorted({p['layer'] for p in supplies}),
                upper_trunk_connection='M4 contacts need native M4-M5-M6-M7-M8 upfeed; M7 contact needs M7-M8; retain actual vias/OBS and never synthesize M1-only loads'))
    placed=[]
    if a.placements:
        for p in selected_rows(a.placements,'instances'):
            if p['master'] not in macros:raise ValueError('missing actual selected master '+p['master'])
            m=macros[p['master']];x,y=p['origin_nm'];o=p['orientation']
            if o not in align.ORIENT:raise ValueError('use LEF R0/MX/MY/etc orientation')
            pg=[dict(pin=q['name'],use=q['use'],layer=l,bbox_global_nm=[v+([x,y,x,y][i]) for i,v in enumerate(align.transform_rect(r,o,m['W'],m['H']))])
                for q in m['pins'] if q['use'] in ('POWER','GROUND') for l,r in q['rects']]
            placed.append(dict(instance=p['instance'],master=p['master'],pin_alignment=align.check_placement(m,o,x,y),
                               actual_oriented_supply_shapes=pg))
    corridors=[]
    if a.channels:
        for c in selected_rows(a.channels,'channels'):
            layer=c['layer'];axis=c['axis']
            pitch,res=align.track_residues(align.ASAP7_TRACKS_NM[layer],axis)
            excluded=c['pg_intervals_nm']+c['clock_shield_intervals_nm']+c['obstruction_intervals_nm']
            result=channel_count(c['low_nm'],c['high_nm'],pitch,res,excluded)
            corridors.append(dict(c,**result,capacity_pass=result['available_tracks']>=c['required_tracks']))
    rec=dict(schema='opentallas.dsrom.s81.macro_track_prep.v1',source_commit=subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),selection_commit='73851317fd9b4fb86c56f6ff760e29981ec610f2',
        selected=dict(stages=81,pairs_per_die=2417,bf=519,return_depth=64,return_topology='ragged active-pair tree',
            projected_die_area_mm2=choice['decision']['area']['die_mm2'],projected_die_area_grade='ANALYTICAL_NOT_PLACED_FIT',
            decision_price=price,total_dies=368,indexer_wk_wq_b='replicated on ALL four ranks',
            indexer_dedup_area_credit_mm2=0,per_rank_indexer_actual_area_mm2=None,
            per_rank_area_note='No area credited for multicast/dedup; actual selected per-rank rectangles/netlist still Maxwell binding',
            ROM_ECC=False,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        selected_inventory_input=owner['S81'],actual_selected_object_status=owner['actual_selected_inputs'],
        per_rank_indexer_policy=owner['indexer'],mapped_native_return=owner['native_node_mapping'],
        required_inventory_generation=owner['required_generation'],owner_reported_existing_jobs=owner['jobs'],
        object_pin_supply_inputs=rows,actual_placements=placed,actual_channels=corridors,
        inputs_sha256={str(p.relative_to(BASE)):sha(p) for p in sorted(INPUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
            |{str(p):sha(p) for p in (a.placements,a.channels) if p},
        distinct_PDN_IR_inputs=dict(supply_shapes='real LEF rectangles, actual orientations when supplied',
            selected_power_map=None,selected_bump_sources=None,selected_PG_vias_and_shapes=None,
            selected_clock_C_exclusions=None,actual_current_per_instance=None,
            IR_result=None,PDN_connectivity_result=None,recipe_source='inputs/maxwell_pdn_preparation.json',
            dependency='Maxwell actual S81 placement/power/source objects; historical204W inventory not re-used as S81 power'),
        channel_policy=dict(long_haul_layers='owner selected upper-metal corridor; no M3/M5 long-haul',
            max_registered_stage_length_um=430,PG_clock_exclusions='count actual shapes, not guessed utilization',
            selected_channel_objects_received=bool(a.channels),capacity_qualified=False),
        gates=dict(selected_die_DEF_received=bool(a.placements),selected_object_source_binding='PENDING Maxwell',
            selected_die_macro_alignment=None,selected_die_fit=None,PDN_IR=None,GRT=None,SS_FF=None,
            historical_S82_fit_credit=False,failed_Rcap0_selected=False,PHY_proxy_qualified=False),
        owner='Maxwell: actual selected die PDN/IR/GRT; Bacon: pin/PG geometry and actual-channel input preparation',
        status='S81_BOUND_READ_ONLY_PREPARATION; RETAINED_OBJECTS_NOT_SELECTED_DIE_CLOSURE',
        launches=dict(PnR=False,build=False,sweep=False,HBM_work=False))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(rec,indent=2)+'\n')
    print('S81 only: 2417 active pairs, RD64, 368 dies; audited',len(rows),'actual retained macro objects; selected placement and PG/channel binding pending Maxwell')


if __name__=='__main__':main()
