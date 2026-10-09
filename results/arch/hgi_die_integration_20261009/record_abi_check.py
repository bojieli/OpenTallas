import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('tools').resolve()))
import die_top_lint as L
import hgi_die_record_ports as H
p=L.parse_module('inputs/ot_hgi_seq.sv','ot_hgi_seq')['ports']
fields,width=H.layout(H.RECORD_FIELDS)
checks={
'command_width':width==1+p['d_hdr'][1]+p['d_sut'][1]+p['d_desc'][1],
'header':fields[1]['hi']-fields[1]['lo']==p['d_hdr'][1],
'sut':fields[2]['hi']-fields[2]['lo']==p['d_sut'][1],
'descriptors':fields[3]['hi']-fields[3]['lo']==p['d_desc'][1],
'unit_flags':p['u_v']==('output',12) and all(p[x]==('input',12) for x in ['u_rdy','u_done','u_fault']),
'known_unit_codes':H.UNIT_CODES=={'quant':4,'coll':6},
'return_width':H.layout(H.RETURN_FIELDS)[1]==3}
r={'scope':'actual committed sequencer header vs declared transport layout; not engine binding, die connectivity, timing or finite-flow evidence','source_commit':'3fae1571db02c46fe9fa1c7630065af0ee8bf42f','source_sha256':hashlib.sha256(Path('inputs/ot_hgi_seq.sv').read_bytes()).hexdigest(),'transport_sha256':hashlib.sha256(Path('tools/hgi_die_record_ports.py').read_bytes()).hexdigest(),'checks':checks,'command_bits':width,'return_bits':3,'verdict':'PASS' if all(checks.values()) else 'FAIL'}
Path('results/record_abi_check.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
sys.exit(not all(checks.values()))
