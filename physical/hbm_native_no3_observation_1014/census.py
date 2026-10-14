#!/usr/bin/env python3
"""Actual hard-master clock and observation sink census; observed receiver mutant."""
import pathlib,subprocess,sys,json,hashlib,collections
root=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
records=[]
for mut in [0,2]:
 dst=out/f'mut{mut}';dst.mkdir(exist_ok=True)
 ys=f'read_verilog -sv -DOT_NO3_HARD_CHILDREN physical/hbm_native_no3_observation_1014/ot_hbm_native_no3_composition_1014.sv physical/hbm_native_no3_observation_1014/hard_children_bb.sv\nhierarchy -check -top ot_hbm_native_no3_composition_1014 -chparam MUT {mut}\nproc\nflatten\nopt\ncheck -assert\nwrite_json {dst}/actual.json\n'
 q=subprocess.run(['yosys','-p',ys],cwd=root,text=True,capture_output=True);(dst/'yosys.log').write_text(q.stdout+q.stderr)
 if q.returncode:raise RuntimeError(q.stdout[-1500:]+q.stderr[-1500:])
 d=json.loads((dst/'actual.json').read_text());m=d['modules']['ot_hbm_native_no3_composition_1014'];clk=m['ports']['clk_sm']['bits'][0];obs=m['ports']['fclk_observe']['bits'][0]
 masters=[];sinks=[]
 for name,c in m['cells'].items():
  dirs=c['port_directions']
  for n,bs in c['connections'].items():
   if dirs[n]=='input' and obs in bs:sinks.append({'instance':name,'port':n,'master':c['type']})
  if c['type'].startswith(('ot_hbm_native_no3_hub','ot_hbm_w2_stn_slice')):
   pin='clk_sm' if c['type'].startswith('ot_hbm_native_no3_hub') else 'clk';masters.append({'instance':name,'master':c['type'],'clock_pin':pin,'clock_root':'clk_sm' if c['connections'][pin]==[clk] else 'fclk_observe' if c['connections'][pin]==[obs] else str(c['connections'][pin])})
 stateful=[n for n,c in m['cells'].items() if c['type'].startswith(('$dff','$adff','$sdff','$aldff'))]
 ok=len(masters)==6 and all(x['clock_root']=='clk_sm' for x in masters) and not sinks and not stateful
 rec={'MUT':mut,'verdict':'PASS' if ok else 'FAIL','actual_hard_masters':masters,'master_counts':dict(collections.Counter(x['master'] for x in masters)),'observation_functional_sinks':sinks,'own_parent_state':stateful,'observation_top_output_only':ok,'actual_json_sha256':hashlib.sha256((dst/'actual.json').read_bytes()).hexdigest(),'expectation_met':ok if mut==0 else not ok,'scope':'Literal synthesized candidate composition; five actual existing payload masters plus unchanged body of candidate hub. Not a real die placement/clock/price qualification.'}
 records.append(rec);print(json.dumps(rec),flush=True)
 assert rec['expectation_met']
(out/'gate.json').write_text(json.dumps({'schema':'opentallas.no3.actual_observation_abi_census.v1','verdict':'PASS','source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'physical/hbm_native_no3_observation_1014').glob('*') if p.is_file()},'cases':records},indent=2)+'\n')
