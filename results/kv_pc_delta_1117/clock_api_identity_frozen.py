import sys,json,copy,hashlib;from pathlib import Path
root=Path('/srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg5_340b90be_d15')
sys.path.insert(0,str(root/'tools/die_plan'))
import schema as S,gen_phys as G
import die_rows as D
b=Path('/srv/opentallas-scratch2/claude/kv-r/pc_delta_hg6');f=root/'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json';raw=json.load(open(f));new=copy.deepcopy(raw);r=json.load(open(b/'HG6_PC_carve_only_rows.json'));D.apply_rows(new,r)
P=S.Plan(raw,str(f));N=S.Plan(new,str(f));rep={}
sha=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
for tn in r['rows']:
 print('CHECK_CLOCK_API',tn,flush=True)
 cp0=G.clock_pins(P,tn);cp1=G.clock_pins(N,tn);ct0=G.core_tap_pins(P,tn);ct1=G.core_tap_pins(N,tn);cores0=S.core_taps(P,tn);cores1=S.core_taps(N,tn)
 assert cp0==cp1 and ct0==ct1 and cores0==cores1
 assert {k:v for k,v in raw['partition_types'][tn]['clock'].items() if k!='reserved_sites_um'}=={k:v for k,v in new['partition_types'][tn]['clock'].items() if k!='reserved_sites_um'}
 rep[tn]=dict(clock_pins=len(cp0),clock_pins_sha256=sha(cp0),core_tap_pins=len(ct0),core_tap_pins_sha256=sha(ct0),actual_core_taps_sha256=sha(cores0),clock_fields_except_reservations_identical=True,legacy_flags_changed=False)
o=dict(verdict='PASS',scope='Exact frozen D15 generation API comparison; carve-only delta changes no tap flags or clock records',baseline_plan_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),types=rep,tool_root=str(root/'tools/die_plan'))
(b/'HG6_PC_frozen_clock_identity.json').write_text(json.dumps(o,indent=1)+'\n');print(json.dumps(o,indent=1),flush=True)
