from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'tools/qwen_dv');from soft_cone_inventory import inventory
p=Path('mapped/net_dirs.json');raw=p.read_bytes();d=json.loads(raw)
d['modules']={k:v for k,v in d['modules'].items() if not v.get('attributes',{}).get('blackbox')}
r=inventory(d,'qfd_dv_stream_packer')
r['scope']='Actual ASAP7 TT ABC combinational mapping; sequential primitives remain generic. No STA/physical/native-flop qualification.'
r['netlist_sha256']=hashlib.sha256(raw).hexdigest()
Path('mapped/inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r[k] for k in ['cells','issues','register_outputs_over32','driven_nets_over32_count']},indent=2))
print(json.dumps(r['highest_generic_stage_depth'][:2]))
