import json,re,hashlib
from pathlib import Path
F=Path('/srv/opentallas-scratch2/claude/codex-kv-1030')
p=F/'bind_e0/rtl/kv3_hg_v3_part.sv';text=p.read_text()
def pins(inst):
 b=re.search(r'\s'+inst+r'\s*\((.*?)\n    \);',text,re.S)
 assert b,inst
 return dict(re.findall(r'\.(\w+)\(([^()]*)\)',b[1]))
def names(ps):
 return set(re.findall(r'\b[a-zA-Z_]\w*', ' '.join(v for k,v in ps.items() if not k.endswith('clk') and k not in ['clk','ck','rst_n'] and not k.endswith('rst_n'))))
a=pins('u_ectl'); b=pins('u_head0_e0');common=names(a)&names(b);assert not common,common
chain=[('u_ectl','t0','u_hst0_g','ti_a'),('u_hst0_g','ti_b','u_head1_u_ftg','ti_a'),('u_head1_u_ftg','ti_b','u_hst0_t2','ti_a'),('u_hst0_t2','ti_b','u_head0_e0','g_front_0_u_front__row_in')]
for src,out,dst,inp in chain:
 x=pins(src)[out].split('[')[0];y=pins(dst)[inp].split('[')[0];assert x==y,(src,dst,x,y)
r={'scope':'worst BOTH-REAL intra diagnostic hg_WS_7 (typekv3_hg_v3), q0tap12 ->E0tap2','result':'No direct ECTL aggregate-to-E0 signal net (commonclock/reset excluded); q0 is subset of full ECTL, so the aggregate endpoint pair is not an actual singlecycle data path.','shared_signal_names':sorted(common),'actual_command_chain':chain,'intervening_registered_stages':3,'stage_module':'qkh_head_gather_stage uses qkh_head_tstage with ti_b/e_b posedge registers; production MUT0','bound_source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':str(p),'diagnostic_preserved':'25negative aggregate all-tap pairs remain in sta_real7; do not reinterpret as real-net pin-matched hold. Actual partition/relay hold is still unmeasured until full kits.'}
(F/'intra_path_diagnosis.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
