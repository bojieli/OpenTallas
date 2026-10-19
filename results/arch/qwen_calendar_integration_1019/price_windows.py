import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('../src/tools/qwen_layerbench').resolve()))
from table_load_contract import *
doc=json.loads(Path('table_windows.json').read_text())
loads=[]
for w in doc['windows']:
    l=w['start'];s=l-RANGE_TO_LOADER_SAMPLE
    loads.append(dict(user=w['user'],stage=w['stage'],range_start=s,
      command_output=s+RANGE_COMMAND_OUTPUT,loader_input=l,
      first_payload=l+LOADER_FIRST_PAYLOAD,last_payload=l+LOADER_LAST_PAYLOAD,
      last_vm_write=l+LOADER_LAST_PAYLOAD+TARGET_WRITE_AFTER_PAYLOAD,
      first_read_bound=l+LOADER_FIRST_READ_BOUND,
      loader_port_interval=[l,l+LOADER_PORT_RESERVATION],
      caller_reservation_interval=[s,s+RANGE_RESERVATION],
      measured_first_read=w['first_read'],measured_last_read=w['last_read'],
      measured_retirement=w['last_read']+1,
      measured_first_read_slack_vs_bound=w['first_read']-l-LOADER_FIRST_READ_BOUND))
out=dict(contract=contract(),windows_sha256=doc['receipt']['windows_sha256'],loads=loads,
 aggregate=dict(loads=144,loader_port_reserved_edges=144*LOADER_PORT_RESERVATION,
 caller_reserved_edges=144*RANGE_RESERVATION,
 origin_expansion_edges=144*RANGE_RESERVATION_EXTRA_VS_LOADER,
 loader_port_delta_edges=0,per_user_origin_expansion_edges=36*RANGE_RESERVATION_EXTRA_VS_LOADER,
 critical_path_delta=None,reason='nine frontedges plus one tail; no production overlap/dependency graph bound'))
Path('fixed_load_pricing.json').write_text(json.dumps(out,indent=2)+'\n')
print('FIXED_LOAD_PRICING_PASS',out['aggregate'])
