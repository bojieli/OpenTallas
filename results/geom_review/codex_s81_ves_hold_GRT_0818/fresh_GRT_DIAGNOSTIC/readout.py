# Private diagnostic driver: canonical unchanged legacy_gate policy generators.
# Insert four path queries before its existing negative-data early stop; never bypass that stop.
from pathlib import Path
import sys,json,subprocess,os,re,hashlib,math
sys.path.insert(0,'/work')
import legacy_gate as gate
import signoff as so
k=Path('/work');base=k/'run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base';db=base/'5_1_grt.odb';assert db.is_file();assert (so.PERIOD_PS,so.UNC_SETUP_PS,so.UNC_HOLD_PS)==(833.0,0.0,25.0)
assert hashlib.sha256(db.read_bytes()).hexdigest()=='84c29dae0308cb633e37c1e061bf5e0c65f213aad11306fe0b960d3231970d07'
pg=json.loads((k/'saved_GRT_PG.json').read_text());assert pg['failure_count']==0 and pg['checked']==337566
for name in ['source_wire_diff.json','clock_reset_frozen_diff.json']:
 guard=json.loads((k/name).read_text());assert guard['verdict']=='PASS' and guard['n_insts_changed']==0 and guard['n_nets_changed']==0
config=(k/'config.mk').read_text();settings={}
sdc=(k/'constraint.sdc').read_text();unc_lines=[x for x in sdc.splitlines() if x.startswith('set_clock_uncertainty ')]
assert 'set_clock_uncertainty 0.0000 -setup [all_clocks]' in unc_lines and 'set_clock_uncertainty 25.0000 -hold [all_clocks]' in unc_lines

for key in ['OT_VCLK_TT','OT_VCLK_FF','LAYER_PARASITICS_FILE']:
 found=re.findall(r'^export\s+'+key+r'\s*=\s*(\S+)\s*$',config,re.M);assert len(found)==1;settings[key]=found[0]
disc,ctx,policy=gate.policy_context(k,base,settings);body=(k/'query_body.tcl').read_text();assert not re.search(r'^\s*(exit|read_db|read_sdc|read_spef|estimate_parasitics|repair_)\b',body,re.M)
results={}
for corner in ['TT','FF']:
 session=gate.policy_session(k,corner,base,disc,ctx,policy);anchor='so_timing STD\n';assert session.count(anchor)==1;session=session.replace(anchor,anchor+body+'\n');p=k/f'ves_policy_{corner}.tcl';p.write_text(session)
 env=dict(os.environ,**settings,OT_POSTCTS_GRT='1',OT_CORNER=corner,ODB=str(db),OT_POSTCTS_TOL='20.0')
 log=k/f'ves_policy_{corner}.log'
 with log.open('w') as f:r=subprocess.run(['openroad','-no_init','-threads','2','-exit',str(p)],env=env,stdout=f,stderr=subprocess.STDOUT)
 text=log.read_text(errors='replace');row={'exit':r.returncode,'queries_complete':'VES_DIAGNOSTIC_PATHS_DONE' in text,'loaded_clock_gate':json.loads((k/f'postcts_gate_{corner.lower()}.json').read_text()) if (k/f'postcts_gate_{corner.lower()}.json').exists() else None}
 if r.returncode==0:
  m=so.parse_session(text);row['policy_corner']=so.corner_result(m);parsed=row['policy_corner'];assert parsed['done'] and parsed['parasitics']=='global_routing' and parsed['periods'] and all(math.isfinite(float(v)) and abs(float(v)-833)<1e-6 for v in parsed['periods'].values());row['required_fail']=m['kv'].get('G2_REQUIRED_FAIL');row['complete_clock_census']=not bool(row['required_fail'])
 results[corner]=row
(k/'VES_FRESH_GRT_DIAGNOSTIC.json').write_text(json.dumps({'kind':'fresh_GRT_ALL_RC_diagnostic_only','original_physical_clock_RC_restored':False,'original_routed_clock_means_ps':{'TT':251.26,'FF':205.65},'unqualified_frozen_protocol_reason':'22 unchangedzero-wire driver-only CLOCK spurs unsupportedbycurrenttypedguard; legacygatefrozenmodeintegration pendingFLOW; no spursdroppedorretyped','policy':{'period_ps':833,'setup_unc_ps':0,'hold_unc_ps':25},'ODB_sha256':hashlib.sha256(db.read_bytes()).hexdigest(),'actual_SDC_sha256':hashlib.sha256(sdc.encode()).hexdigest(),'actual_uncertainty_lines':unc_lines,'corners':results,'scope':'fresh nativeGRT estimates, noDUTedit/no routedRC/SIGNED/adoption/count credit'},indent=2))
assert all(x['exit']==0 and x['queries_complete'] for x in results.values()),results
print('VES_FRESH_GRT_DIAGNOSTIC_COMPLETE',json.dumps({c:{'exit':x['exit'],'required_fail':x.get('required_fail')} for c,x in results.items()}))
