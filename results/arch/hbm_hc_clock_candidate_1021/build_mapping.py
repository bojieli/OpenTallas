#!/usr/bin/env python3
"""Emit a source-bound HC SAFE2/P40 clock/reset delta; never mutate a die graph."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(contract,profile,spec,landing,insertion):
 rows=[];entries=[];resets=[]
 assert spec['clock_ports']==['clk']+[f'clk_t[{i}]' for i in range(4)]
 assert spec['clock_cts_roots']==['clk'] and landing['clock']=='clk' and landing['stages']==2
 assert insertion['lib_clock_pin']=='clk' and insertion['parasitics']=='spef' and insertion['raw_source']
 for q in ['SW','SE','NW','NE']:
  n='hc_'+q;i=contract['instances'][n]
  assert i['master']==profile['hubs'][n]['master']=='ot_hbm_hc_qhub_static'
  assert i['params']=={'DRLY':2,'CHX':11} and 'clk_t' not in i['ports']
  old=[r for r in contract['clock_resets'] if r['instance']==n]
  clk=next(r for r in old if r['kind']=='clock' and r['port']=='clk');rst=next(r for r in old if r['kind']=='reset' and r['port']=='rst_n')
  assert clk['domain']==rst['domain']=='stream' and clk['source']==['hb_ckgen','pll_stream'] and rst['source']==['hb_ckgen','por_stream']
  rows.append(dict(clk,port='clk_t',bits=4))
  for k,p in enumerate(spec['clock_ports']):
   entries.append(dict(instance=n,port=p,generator_entry=n if k==0 else f'{n}__ckp{k:03}',domain=clk['domain'],source=clk['source'],delivery='DISTINCT_LITERAL_PIN_AND_DIE_TREE_BRANCH',role='glue CTS root' if k==0 else 'hard tree child entry',child=None if k==0 else dict(instance=f'u_cen.g_hard.g_qt[{k-1}].u_t',master='ot_hbm_hc_qtree16_static',clock_pin='clk',reference={c:{f:insertion[c]['boundary'][f] for f in ['min','mean','max']} for c in ['tt','ff','ss']})))
  resets.append(dict(instance=n,retained_graph_row=rst,external_reset_ports_added=0,physical_parent_landing=landing,internal_tree_reset=dict(source='u_cen.g_rc.g_rt.u_rst_t',clock='clk',copies=4,SYNC_STAGES=2,TREE_STAGES=1,output='rcn_t[c] -> u_cen.g_hard.g_qt[c].u_t.rst_n'),child_reset='Existing CLOSED tree16 reset face landing2 then ot_rst_relay local release; keep actual per-region phases, no invented universal sum',qualification='Parent clock delivery/assert/release/startup remains OPEN; no stopped-clock reset guarantee'))
 assert len(entries)==20 and len({(r['instance'],r['port']) for r in entries})==20
 return dict(status='UNADOPTED_CLOCK_RESET_MAPPING_CANDIDATE',preserved_die_source='017b32285/N',candidate_HC_source='5bdf1a9c5',candidate_profile=profile,clock_resets_add=rows,literal_entries=entries,reset_ledger=resets,port_delta=dict(added={'clk_t':{'direction':'input','bits':4}},removed=[],unchanged='All existing ports and face fanout edges retained exactly; no new target/PLL/domain'),generator_rule=dict(source='tools/hbm_die_v15/die_case_v16.py:clock_entries',same_hub_entry_pairs=10,total_intra_hub_pairs=40,communicating_tile_pairs='Conservative all-entry combinations from existing generator',missing_physical_pin='Existing generator raises; never substitute centre',physical_parent_pin_coordinates='OPEN until actual candidate GEN/view; no C6 parent closure alias'),timing_scope='Each of4 child entries binds same master/clk min/mean/max envelope, not individual-entry values or mean-only refs. Per-entry route delivery must be measured.',adoption_requirements=['HC exact source/full graph+params+calendar positive/causal proof','Actual native32 and geometry/model before parent physical','Source-hash S2 invalidations/reuse, actual GEN20pins/reset/STA and mandatory S11 IR','New parent physical body/source-qualified view only; old C6 FAIL and old phase23 view never aliased'],current_die_mutation=False,new_jobs=0)
if __name__=='__main__':
 c=json.load(open(sys.argv[1]));p=json.load(open(HERE/'candidate_profile.json'));s=json.load(open(HERE/'c6_reference_spec.json'));r=json.load(open(HERE/'c6_reset_landing.json'));i=json.load(open(HERE/'tree16_insertion.json'))
 delta=json.load(open(HERE/'actual_interface_delta.json'));assert delta['selected_N_contract_sha256']==sha(Path(sys.argv[1]))
 assert delta['ports']['clk_t']==dict(direction='input',bits=4)
 for q in ['SW','SE','NW','NE']:
  old=c['instances']['hc_'+q]['ports'];assert len(old)==79
  assert all(delta['ports'][k]==v for k,v in old.items()) and set(delta['ports'])-set(old)=={'clk_t'}
 out=build(c,p,s,r,i);out['input_sha256']={f.name:sha(f) for f in [Path(sys.argv[1]),HERE/'candidate_profile.json',HERE/'c6_reference_spec.json',HERE/'c6_reset_landing.json',HERE/'tree16_insertion.json']}
 out['input_sha256']['actual_interface_delta.json']=sha(HERE/'actual_interface_delta.json')
 out['HC_interface_delta_ref']='f96d23c9b; all79 existing ports and incident dataedges retained, only clk_t4 additive'
 out['programme_scope']='HC helper fail-closed npos!=1: scoped rank0k31 HC.HC_MIX_POST/pricedrecord30 hc_attn K20480 relocatedA64/O72 only. G0+51/tail+83/emit+583 onlythisscope; multi-position rootwindow NOT_GENERATED_OR_QUALIFIED. Mapping does not qualify programme.'
 (HERE/'mapping_candidate.json').write_text(json.dumps(out,indent=2)+'\n');print('HC_CLOCK_CANDIDATE20literalentries/16additivepins/0newresetports; no graph mutation/no jobs')
