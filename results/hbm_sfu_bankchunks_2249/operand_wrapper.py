from pathlib import Path
import json
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-2249/bankchunks');y=json.load(open('/srv/opentallas-scratch2/claude/die-hbm-29/b29d/out/asbuilt.json'));M=y['modules'];m=M['hbm_current_native_top']
for n in ('sfucore_NE','u_core','u_engine','u_memory','u_store'):m=M[m['cells'][n]['type']]
c=m['cells']['g_operand[0].u_group'];ports=[];conns=[];const={}
for pn,bs in c['connections'].items():
 dr=c['port_directions'][pn]
 if not bs:conns.append(f'.{pn}()');continue
 if dr=='output' or any(isinstance(b,int) for b in bs):
  ports.append(f' {dr} wire [{len(bs)-1}:0] {pn}')
  expr=pn if dr=='output' else '{'+','.join(f'{pn}[{i}]' if isinstance(b,int) else "1'b"+b for i,b in reversed(list(enumerate(bs))))+'}'
 else:expr='{'+','.join("1'b"+b for b in reversed(bs))+'}'
 conns.append(f'.{pn}({expr})');const[pn]=sum(isinstance(b,str) for b in bs)
params=','.join(f'.{k}({int(v,2)})' for k,v in c['parameters'].items())
s='module ot_sfu_operand_actual(\n'+',\n'.join(ports)+');\n ot_hgi_su_lgroup2_bankchunks #('+params+')u(\n'+',\n'.join(conns)+');\nendmodule\n';(R/'operand_actual_wrapper.sv').write_text(s);(R/'operand_actual_constant_bits.json').write_text(json.dumps(const,indent=1));print(const)
