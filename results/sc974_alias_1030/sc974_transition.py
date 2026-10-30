from pathlib import Path
import json,re
b=Path('/srv/opentallas-scratch2/claude/codex-sc974-alias-1030');o=b/'candidate';p=b/'proof';p.mkdir(exist_ok=True)
E=json.load((o/'endpoint_map.json').open());I=json.load((b/'input/port_interface.json').open());state=json.load((o/'state_bijection.json').open())['mapping'];ix={r['instance']:k for k,r in enumerate(state)};N=len(ix)
rx=re.compile(r'(?P<master>qfd_s2_bmath_dff_p(?:n0)?)\s*#\(\.ID\((?P<id>\d+)\)\)\s*(?P<instance>u_\d+)\s*\((?P<pins>[^;]*?)\);')
def cut(text,newname):
 text=re.sub(r'\(\*.*?\*\)\s*','',text,flags=re.S);oldname=re.search(r'\bmodule\s+(\w+)',text)[1];text=text.replace('module '+oldname+'(','module '+newname+'(',1)
 changes=[];found=set()
 for m in rx.finditer(text):
  inst=m['instance'];j=ix[inst];ps=dict(re.findall(r'\.(\w+)\(([^)]+)\)',m['pins']));found.add(inst)
  v=f"assign {ps['Q']} = state[{j}]; assign next_D[{j}] = {ps['D']}; assign reset_R[{j}] = {ps.get('R',chr(49)+chr(39)+'b1')}; assign clock_C[{j}] = {ps['C']};"
  changes.append((m.start(),m.end(),v))
 assert found==set(ix)
 pieces=[];at=0
 for a,z,t in changes:pieces.extend([text[at:a],t]);at=z
 pieces.append(text[at:]);text="".join(pieces)
 end=text.index(');',text.index('module '));text=text[:end]+',state,next_D,reset_R,clock_C'+text[end:];end=text.index(');',text.index('module '))+2;text=text[:end]+f'\ninput wire [{N-1}:0] state;\noutput wire [{N-1}:0] next_D, reset_R, clock_C;\n'+text[end:];return text
(p/'gold_cut.sv').write_text(cut((b/'input/qfd_dv_s5_sc2_k79.sv').read_text(),'sc974_gold_cut'))
(p/'alias_cut.sv').write_text(cut((o/'source/qfd_dv_s5_sc2_k79_alias974.sv').read_text(),'sc974_alias_cut'))
def expand(expr):
 expr=expr.strip()
 if expr.startswith('{'):return sum((expand(x) for x in reversed(expr[1:-1].split(','))),[])
 m=re.fullmatch(r'(\w+)\[(\d+):(\d+)\]',expr)
 return [f'{m[1]}[{k}]' for k in range(int(m[3]),int(m[2])+1)] if m else [expr]
parent={}
for x in I['ports']:
 if x['direction']=='input':
  for bit in expand(x['parent_net']):
   m=re.fullmatch(r'(\w+)(?:\[(\d+)\])?',bit);assert m,bit;parent[m[1]]=max(parent.get(m[1],0),int(m[2])+1 if m[2] else 1)
assert sum(parent.values())==357,parent
aliases=[x for x in E['endpoints'] if x['new_alias']];mut=aliases[0];correct=mut['actual_parent_net'];m=re.fullmatch(r'(\w+)\[(\d+)\]',correct);assert m;wrong=f'{m[1]}[{int(m[2])-1}]'
lines=['module sc974_transition_miter #(parameter MUT=0) (',',\n'.join([f'input wire [{width-1}:0] {n}' for n,width in sorted(parent.items())]+[f'input wire [{N-1}:0] state','output wire pass']),');',f'wire [{N-1}:0] gd,gr,gc,ad,ar,ac;']
for x in I['ports']:
 if x['direction']=='output':lines.append(f"wire [{x['bits']-1}:0] g_{x['name']},a_{x['name']};")
for prefix,mod in [('g','sc974_gold_cut'),('a','sc974_alias_cut')]:
 con=[]
 for x in I['ports']:con.append('.'+x['name']+'('+(x['parent_net'] if x['direction']=='input' else prefix+'_'+x['name'])+')')
 if prefix=='a':
  for row in aliases:
   value=row['actual_parent_net']
   if row is mut:value=f'(MUT ? {wrong} : {correct})'
   con.append('.'+row['private_port']+'('+value+')')
 con += ['.state(state)',f'.next_D({prefix}d)',f'.reset_R({prefix}r)',f'.clock_C({prefix}c)'];lines.append(mod+' '+prefix+' ('+',\n'.join(con)+');')
outs=[x for x in I['ports'] if x['direction']=='output'];lines += ['assign pass = (gd == ad) && (gr == ar) && (gc == ac) && '+ ' && '.join(f"(g_{x['name']} == a_{x['name']})" for x in outs)+';','endmodule'];(p/'miter.sv').write_text('\n'.join(lines)+'\n')
(p/'proof_scope.json').write_text(json.dumps(dict(kind='universal one-transition/output source miter with ALL43058 states as shared arbitrary inputs',state_mapping='bijective identity, no reset/initial-state assumption',compared=['all43058D equations','all43058reset equations','all43058clock event nets','all215outputs'],parent_input_bits=sum(parent.values()),parent_alias_mapping='literal original parent expressions per port_interface.json',wrong_alias=dict(port=mut['private_port'],instance=mut['instance'],correct=correct,wrong=wrong),native_qualification='NOT RUN; proof cutpoint model does not waive native KEEP/FACE or timing'),indent=2)+'\n')
for tag,mode in [('normal',0),('wrong_alias',1)]:
 script=f'read_verilog -sv {b}/input/qfd_dv_s5_sc2_k79_helpers.sv {p}/gold_cut.sv {p}/alias_cut.sv {p}/miter.sv; hierarchy -top sc974_transition_miter -chparam MUT {mode}; setattr -mod -unset keep_hierarchy; setattr -unset keep; proc; flatten; opt; techmap; opt; sat -verify -prove pass 1 -show pass -show {m[1]}'
 if mode:script+=f' -dump_vcd {p}/wrong_alias.vcd'
 (p/(tag+'.ys')).write_text(script+'\n')
(p/'run.sh').write_text(f'''#!/bin/bash
set -uo pipefail
p={p}
yosys -Q -s "$p/normal.ys" >"$p/normal.log" 2>&1
rc=$?;if [ "$rc" != 0 ];then tail -n10 "$p/normal.log";exit "$rc";fi
echo "SC974_ARBITRARY_STATE_TRANSITION_PASS"
yosys -Q -s "$p/wrong_alias.ys" >"$p/wrong_alias.log" 2>&1
rc=$?;if [ "$rc" = 0 ];then echo MUTANT_SURVIVED;exit 1;fi
if grep -q 'Called with -verify and proof did fail' "$p/wrong_alias.log";then echo "WRONG_ALIAS_MUTANT_CAUGHT";else tail -n12 "$p/wrong_alias.log";exit 2;fi
''')
print('CUT_TRANSITION_PREPARED',N,'states',len(aliases),'aliases','MUTANT',correct,'->',wrong)
