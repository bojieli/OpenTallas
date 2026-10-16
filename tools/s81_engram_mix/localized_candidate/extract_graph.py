import re,subprocess,json
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--own-valid',action='store_true');args=p.parse_args()
R=Path(__file__).resolve().parents[3];O=args.out;O.mkdir(parents=True,exist_ok=True)
sources=['rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_clocked_candidate.sv','rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv','rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv']
if args.own_valid:sources+=['rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_localized_candidate.sv']
modules={}
for p in sources:
 s=(R/p).read_text()
 for m in re.finditer(r'\bmodule\s+(\w+)\b.*?\bendmodule\b',s,re.S):modules[m[1]]=m[0]
leafs=['mul4','chunk8','add8','norm','sum','signed_sqrt','sigmoid','mix_control','rly','mixq_shcol','mixq_shctl']
texts=[]
for n in leafs:
 name='ot_s81_engram_'+n
 header=modules[name].split(';',1)[0]+';'
 texts.append('(* blackbox *) '+header+'\nendmodule')
wires=['ot_s81_engram_mixq_localized_candidate','ot_s81_engram_mix_relay_localized_candidate','ot_s81_engram_mixq_shell_localized','ot_s81_engram_gate']if args.own_valid else['ot_s81_engram_mixq_clocked_candidate','ot_s81_engram_mix_relay_clocked_candidate','ot_s81_engram_mixq_shell','ot_s81_engram_gate']
for n in wires:texts.append(modules[n])
(O/'graph_source.sv').write_text('\n'.join(texts))
top='ot_s81_engram_mixq_localized_candidate'if args.own_valid else'ot_s81_engram_mixq_clocked_candidate'
r=subprocess.run(['yosys','-Q','-T','-p',f'read_verilog -sv {O}/graph_source.sv; hierarchy -check -top {top} -chparam VM_LAT 13; flatten; opt_expr; opt_clean; write_json {O}/cluster_graph.json'],capture_output=True,text=True);(O/'graph_extract.log').write_text(r.stdout+r.stderr);print(r.returncode);print((r.stdout+r.stderr)[-1200:])
