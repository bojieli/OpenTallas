from pathlib import Path
from collections import defaultdict
import argparse,json,sys,shutil,re,hashlib
p=argparse.ArgumentParser();p.add_argument('--tools',required=True);p.add_argument('--plan',required=True);p.add_argument('--reference',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools)
import schema as S,die_trial as D,gen_phys as G
path=Path(a.plan);P=S.Plan(S.load(path),path);out=Path(a.out);(out/'abstracts').mkdir(parents=True,exist_ok=True);(out/'grt').mkdir(exist_ok=True);smod=D.standin_module_names(P);bits={};stats={}
for tn,t in sorted(P.types.items()):
 text,st=D.abstract_lef(P,tn,module_name=smod[tn],landing_infra=True,reset_infra=True)
 (out/'abstracts'/(smod[tn]+'.lef')).write_text(text);stats[tn]=st
 b=defaultdict(int)
 for bus,bit,*_ in G.type_pins(P,tn):b[bus]=max(b[bus],bit+1)
 bits[tn]=dict(b)
text,ft=D.route_netlist(P,bits,landing_infra=True,reset_infra=True);(out/'grt/route.v').write_text(text)
ref=Path(a.reference)
for name in ['grt.tcl','obs.tcl','tracks.tcl']:
 shutil.copy2(ref/'grt'/name,out/'grt'/name)
# Clock-only route wrappers contain one black-box module per macro; preserve
# the complete new infrastructure pin lists by regenerating route_netlist.
ports={}
for f in (out/'abstracts').glob('*.lef'):
 for name in re.findall(r'^\s*PIN\s+(\S+)',f.read_text(),re.M):ports[name]=ports.get(name,0)+1
receipt=dict(schema='opentallas.native_target_infra.v1',plan=str(path),plan_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source='existing die_trial.abstract_lef/route_netlist landing_infra=True,reset_infra=True; reference exact-origin target Tcl/OBS',types=len(stats),parts=len(P.parts),declared_start_pin_types=ports.get('cland_tstart_in',0),raw_reset_pin_types=ports.get('cland_raw_reset_out',0),landing_infra=True,reset_infra=True,route=False,physical_timing=False)
(out/'emit_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
