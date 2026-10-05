"""Fixed226 source construction handoff; no engine build or physical admission.

The archived owner WIP is an immutable observation, not an adopted netlist.
Preferred track stations bind packet bit order and direction, not legal sites.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import uarch_topk_finite_track_turn_model as T

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_selector_physical_join_20261002'
MANIFEST_SHA = '411792684b1b98f6be9cd5bf61261fd799064791cce0422a70424bf1c5a74076'
PINS = {
 'station': ('results/uarch/topk_buffered_station_source_model_20261002/model_r2.json', '1589f533c2212363c87b1fc286295444ff1b836680ba1daa92f6a5c2c017919e'),
 'tracks': ('results/uarch/topk_finite_track_turn_model_20261002/model_r2.json', 'aea66889167d55ce300f0f07cb36e0c5b90ca73b1d0fef8caa40ebeddff14409'),
 'caller_plan': ('results/rtl/topk_station_caller_fence_prepare_20261002/package_r3/sourceplan.json', '7127f21707a16c6d9f5e75b9a51d4db2790dd52676b2adc89cf798f1161b2366'),
 'caller': ('results/rtl/topk_station_caller_fence_prepare_20261002/package_r3/ot_w15_coll_dma_station_prepare.sv', '03a371a5ab3cfb85700563186a83c2aacaa0611465ce09ca3fbd1eb32691902f'),
}
# Actual concatenations, LSB first, not the sorted external track inventory.
PACKETS = {
 'inputs': [('stride',32),('k',14),('n',14),('go',1),('ld_data',2048),('ld_word',9),('ld_rank',2),('ld_id',1),('ld_valid',1)],
 'outputs': [('stat_cycles',32),('out_last',1),('out_data',2048),('out_nw',3),('out_valid',1),('fault',1),('done',1),('busy',1)],
 'write': [('done',1),('data',2048),('addr',60),('we',4)],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def archive(base=BASE):
    data=(base/'source_manifest.json').read_bytes()
    if sha(data)!=MANIFEST_SHA: raise ValueError('archive manifest changed')
    manifest=json.loads(data); records={}
    for name, pin in manifest.items():
        packed=(base/'inputs'/name).read_bytes()
        if sha(packed)!=pin['archive_sha256'] or len(packed)!=pin['archive_bytes']:
            raise ValueError('archive bytes changed')
        raw=gzip.decompress(packed) if pin['gzip_exact_byte_archive'] else packed
        if sha(raw)!=pin['original_sha256'] or len(raw)!=pin['original_bytes']:
            raise ValueError('original bytes changed')
        records[name]=raw.decode() if pin.get('format')=='text' else json.loads(raw)
    return records,manifest


def inputs(root=ROOT):
    out={}
    for name,(path,digest) in PINS.items():
        p=root/path
        if p.exists():
            data=p.read_bytes()
            if sha(data)!=digest: raise ValueError('fixed source changed: '+name)
            out[name]=data.decode() if name=='caller' else json.loads(data)
        else:
            # Absent historical package only. Present corrupt bytes never fall back.
            records,manifest=archive()
            key='fixed_'+name+('.sv.gz' if name=='caller' else '.json.gz')
            if manifest[key]['original_sha256']!=digest: raise ValueError('fallback pin mismatch')
            out[name]=records[key]
    return out


def offsets(group):
    out={}; pos=0
    for field,width in PACKETS[group]:
        for bit in range(width): out[f'{group}.{field}[{bit}]']=pos+bit
        pos+=width
    return out


def station_ledger(tracks):
    maps={g:offsets(g) for g in ('inputs','outputs')}; seen=set();rows=[]
    for entry in tracks['assignments']:
        pin=entry['pin']
        if pin in ('clock','reset'): continue
        group=pin.split('.')[0]
        if pin in seen or pin not in maps.get(group,{}): raise ValueError('packet track alias or unknown pin')
        seen.add(pin)
        points=T.station_coordinates(entry,3125440,16000000,100)
        if group=='inputs': points.reverse()  # Producer hub to selector.
        rows.append(dict(pin=pin,packet_bit=maps[group][pin],helper_instance='g_topk.g_station.u_'+('input' if group=='inputs' else 'return'),
          payload_instance_expression=f'payload[stage][{maps[group][pin]}]',stage_indices=list(range(99)),
          stage_order='hub_to_selector' if group=='inputs' else 'selector_to_hub',
          preferred_track_points_DBU=points,track=entry,legal_cell_sites_assigned=False))
    if seen!=set(maps['inputs'])|set(maps['outputs']): raise ValueError('missing packet track')
    return rows


def validate_enable(d):
    if d['candidate']!='DS4096-TP4-S58-PAR2-NP2048' or d['control_edges']!=1 or d['macro_data_edges']!=2:
        raise ValueError('scenario or control-edge contract changed')
    for case in d['cases'].values():
        copies=case['source_state_copies']
        if len(copies)!=8 or case['added_physical_FF']!=8 or case['added_capture_latency_cycles']!=0:
            raise ValueError('replica state/stage mismatch')
        if any(not c['unchanged_D_CLK_RESETN_SETN'] for c in copies): raise ValueError('replica equation changed')
        for c in copies:
            p=c['original_connections']
            if p['CLK']!='leaf_clk[0]' or ('valid' in c['instance'] and (p['RESETN']!='rst_n' or p['SETN']!="1'h1")):
                raise ValueError('replica clock/reset mismatch')
        if len(case['proposed_D_distribution'])!=2: raise ValueError('missing replica D producer')


def build():
    fixed=inputs();records,manifest=archive();enable=records['enable_construction_WIP.json.gz']
    validate_enable(enable)
    station=fixed['station'];cost=station['cost'];caller=fixed['caller_plan']
    if (cost['additional_cycles_per_call'],cost['ninecall_cycles'])!=(226,2034): raise ValueError('station latency changed')
    if [caller[k] for k in ('input_edges','return_edges','formed_write_edges')]!=[99,99,28]: raise ValueError('caller stage mismatch')
    rows=station_ledger(fixed['tracks']); shared=records['selected_caller_r5_WIP.json.gz']['finite_parent_construction']['shared_broadcast']
    if shared['added_BST_register_bits_per_shard']!=3264 or shared['added_source_edges']!=0: raise ValueError('BST state/stage changed')
    if shared['nominal_sites_per_shard']!=2048: raise ValueError('compiled pair count changed')
    cases={}
    for name,c in enable['cases'].items():
        paths=[]
        for p in c['proposed_D_distribution']:
            timing=p['SS_FF_complete_D_path']
            paths.append(dict(role=p['role'],predecessor=p['actual_predecessor_FF'],original_driver=p['actual_mapped_driver'],
              original_D=p['original_D'],same_edge=True,added_stage=0,
              SS_margin_ps=timing['ss']['SS_complete_margin_ps'],FF_hold_margin_ps=timing['ff']['FF_hold_margin_ps'],
              includes_existing_pin_sinks=timing['ss']['all_existing_predecessor_and_inverter_pin_sinks_included'],
              other_fanout_wire_extracted=False,full_path_source=p))
        cases[name]=dict(replica_connections=c['source_state_copies'],replica_D_paths=paths,
          local_enable_SS_margin_ps=c['minimum_SS_remaining_ps'],reservation_50pct_um2=c['conservative_50pct_core_reservation_um2'],
          gross_reservation_50pct_um2=2*(c['added_local_cell_area_um2']+c['new_D_tree_cell_area_um2']),
          conditional_old_decode_credit_um2=c['old_source_decode_removal_area_um2'],decode_removal_credit_requires_all_sinks_rewired=True,
          added_clock_pin_fF=c['clone_clock_pin_debit_SS_FF_fF'],added_reset_pin_fF=c['clone_reset_pin_debit_SS_FF_fF'],
          preferred_cells=len(c['placements']),cell_collisions=c['placement_cell_collisions'],
          macro_collisions=c['placement_macro_body_collisions'],existing_WAKE_ICG_collisions=c['placement_source_WAKExICG_collisions'])
    enable_res=sum(cases[n]['reservation_50pct_um2']*count for n,count in [('q',1686),('bfcolumn',362)])/1e6
    enable_gross=sum(cases[n]['gross_reservation_50pct_um2']*count for n,count in [('q',1686),('bfcolumn',362)])/1e6
    guard=caller['control_guard_area_addition']
    # Areas have distinct ownership: local clones exclude WAKE; shared broadcast
    # includes BUFFER floor and separately BST replica FF, not all logical BST.
    ledger=dict(selector_station_50pct_mm2=cost['station_cell_reservation_mm2_at50pct'],
      local_enable_replacement_2048_50pct_mm2=enable_res,
      shared_broadcast_BUFFER_50pct_mm2=shared['positive_shared_tree_cell_floor_at50pct_mm2'],
      shared_BST_replica_FF_50pct_mm2=shared['register_replica_floor_at50pct_mm2'],
      caller_guard_50pct_mm2=guard['AND2x2_reservation_mm2_at50pct'])
    result=dict(schema='opentallas.selector.fixed226.physical-join.v1',candidate=enable['candidate'],
      geometry=dict(N=4,NMAX=2048,LDW=4,P=64,PF=64,DIG=8,CB=14,S=58,PAR=2,NP=2048,q_pairs=1686,BF_pairs=362),
      archive_manifest_sha256=MANIFEST_SHA,archived_origins=manifest,fixed_sourcepins=PINS,
      physical_admission=False,no_engine_or_physical_job_launched=True,no_variant_sweep=True,
      owner_snapshot_is_not_adopted_source=True,station=dict(input_edges=99,return_edges=99,write_edges=28,cycles_per_call=226,ninecall_cycles=2034,
        packet_mapping_rows=len(rows),preferred_data_station_nodes=4210*99,formed_write_data_nodes=2113*28,
        ASR_valid_nodes=226,core_state_bits=698354,caller_fence_RTL_verified=False,
        write_packet_lsb_fields=PACKETS['write'],write_sites_require_actual_VM_endpoint_coordinates=True,
        source_calendar_calls=cost['source_calendar_calls'],clock_contract=station['clock_contract'],
        cell_master_dimensions=station['placement_contract']['LEF_master_dimensions']),
      enable=cases,baseline_control_fault_preserved=records['enable_diagnosis.json.gz']['raw_control_to_capture_one_cycle_slack_ps'],
      area_ownership=ledger,area_increment_floor_mm2=sum(ledger.values()),
      area_increment_without_unearned_decode_removal_credit_mm2=sum(ledger.values())-enable_res+enable_gross,
      partial_budget_scope='Distinct selector/local-enable/broadcast/BST/guard floors only; global clock/reset, hold repair, PG/escape and route detours not priced here. Existing parent reservation not added again.',
      state_ownership=dict(selector_transport_data_FF=475954,selector_transport_valid_ASR=226,local_enable_new_FF=8*2048,
        shared_BST_new_FF=3264,existing_WAKE_new_charge_bits=0),
      concrete_admission_deficits=[
        dict(owner='Archimedes',scope='same-edge valid/bank clone D',gate='FF hold',status='FAIL_CONDITIONAL_SOURCE_SCREEN',required='Repair/price source-bound min path; retain same source edge, verify existing fanout routes and SS setup.'),
        dict(owner='Archimedes/Maxwell',scope='8 new clock and4 reset pins per pair',gate='clock/reset',status='OPEN',required='Join actual leaf clock/RESETN routes including recovery/removal; no existing WAKE debit reuse.'),
        dict(owner='Archimedes',scope='local enable roots/leaves and capture cells',gate='PG/pin escape',status='OPEN',required='Legal source sites, LEF58 enclosure/spacing against PG/OBS, then extracted SS/FF timing.'),
        dict(owner='Maxwell',scope='3264 final BST replicas',gate='same-edge broadcast',status='OPEN',required='Actual common predecessor D/clock/reset fanout and min/max routes; no extra source service assumed.'),
        dict(owner='Epicurus/Archimedes/Maxwell',scope='fixed226 selector transport',gate='placed clock/PG/RC',status='OPEN',required='Map preferred track nodes to disjoint legal cell sites and actual matched global clock; 193.64um fanout-floor reach is not15mm route closure.'),
        dict(owner='Epicurus',scope='full N4 NMAX2048 selector/caller',gate='source equivalence',status='OPEN',required='Balanced core implementation and actual fence gate must preserve exact stable selection and final VM write/drain order.'),
      ])
    return result,rows


def emit(out):
    model,rows=build();out.mkdir(parents=True,exist_ok=True)
    payload=b''.join((json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode() for r in rows)
    packed=gzip.compress(payload,mtime=0);(out/'source_station_mapping.jsonl.gz').write_bytes(packed)
    model['station_mapping_artifact']=dict(sha256=sha(packed),bytes=len(packed),uncompressed_sha256=sha(payload),
      scope='4210 source packet bits,99 preferred logical nodes each; no placed-cell or extracted-RC claim')
    (out/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    return model


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=BASE/'r1');a=p.parse_args()
    model=emit(a.output)
    print(json.dumps(dict(physical_admission=model['physical_admission'],cycles_per_call=226,
      area_increment_floor_mm2=model['area_increment_floor_mm2'],deficits=len(model['concrete_admission_deficits'])),sort_keys=True))
