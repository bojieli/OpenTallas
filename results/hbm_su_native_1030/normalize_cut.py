"""Map generated disconnected output concatenation to standard Verilog open port."""
import hashlib,json,pathlib,re
from pin_plan import PACK,ROOT
HERE=pathlib.Path(__file__).parent;rows=[]
provider=(PACK/'ot_hbm_su_static_pinned_bank.sv').read_text();assert 'output wire[READERS-1:0]read_return' in provider
for top in ['ot_hnx_su_exp__rst3','ot_hnx_su_plain4__lid9_rst3','ot_hnx_su_plain4__7dd6a1bbbf47_rst3']:
 raw=(PACK/(top+'.sv')).read_text();empty=re.findall(r'\.(\w+)\(\{\}\)',raw);assert empty and set(empty)=={'read_return'}
 owners=[]
 for line in raw.splitlines():
  if '.read_return({})' not in line:continue
  assert re.match(r'\s*ot_hbm_su_static_pinned_bank\s*#\(',line),line
  instance=re.search(r'\)\s+(m\d+)\s*\(',line).group(1);owners.append(instance)
 assert len(owners)==len(empty)
 fixed=raw.replace('.read_return({})','.read_return()');assert fixed.replace('.read_return()','.read_return({})')==raw
 p=ROOT/'physical/die_plan/hbm_arch_cores/wrappers'/(top+'__synth.sv');p.write_text(fixed)
 rows.append(dict(module=top,original_sha256=hashlib.sha256(raw.encode()).hexdigest(),synth_sha256=hashlib.sha256(fixed.encode()).hexdigest(),disconnected_output_ports=len(empty),output_owner_module='ot_hbm_su_static_pinned_bank',owner_instances=owners,port_direction='output',port='read_return',proof='Only unused pinned-bank output read_return empty connection changes from invalid empty concat to standard open output; all connected bits, logic, state, and hierarchy byteidentical'))
(HERE/'normalize_cut_receipt.json').write_text(json.dumps(dict(status='PASS_DISCONNECTED_OUTPUT_SYNTAX_ONLY',rows=rows),indent=1)+'\n');print('PASS',[(r['module'],r['disconnected_output_ports'])for r in rows])
