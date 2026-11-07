"""Add one output pin cycle on program fault, preserving all internal logic bytes."""
from pathlib import Path
import sys,hashlib,json,re
p=Path(sys.argv[1]);r=p/'rtl/qkd_hr_core_prompt.v';s=r.read_text()
a='else u_program__fault <= _3129_;';b='else u_program__fault <= hrfp_u_program__fault_0_internal_state;'
assert s.count(a)==1
# The output face is only a declared/written port. Internal users use the separate hrfp state.
uses=[l for l in s.splitlines() if re.search(r'(?<![A-Za-z0-9_])u_program__fault(?![A-Za-z0-9_])',l)]
assert len(uses)==5,(len(uses),uses)
n=s.replace(a,b);assert n.replace(b,a)==s
r.write_text(n)
m={'schema':'opentallas.private_pin_cycles.v1','variant':'vK','parent_variant':'vJ2','added_rx_clk_PIN_cycles':{'u_program__fault':1},'inherited_PIN_cycles':{'s_ar_to_s_r':1,'u_program__authorized_footer_and_valid':1},'inherited_reset_release_cycles':3,'RTL_change':a+' -> '+b,'internal_logic_byte_exact':True,'old_rtl_sha256':hashlib.sha256(s.encode()).hexdigest(),'new_rtl_sha256':hashlib.sha256(n.encode()).hexdigest(),'source_transform':'codex/kv-prompt-channel-1107 fault_pin_cycle.py','parent_model_obligation':'compiler/token parent must delay program fault observation by one ck edge; no state/feedback/handshake change'}
(p/'PIN_CYCLES.json').write_text(json.dumps(m,indent=2)+'\n')
with (p/'config.mk').open('a') as f:f.write('\n# vK REDESIGN: u_program__fault face D takes internal-state Q; PIN CYCLES +1 fault output only. Internal feedback unchanged.\n')
print(json.dumps(m))
