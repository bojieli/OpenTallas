import pathlib,json,re,importlib.util
r=pathlib.Path('.');sp=importlib.util.spec_from_file_location('lint',r/'tools/textbook_lint.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
g,top=T.flatten(T.parse_verilog((r/'synth/results/asap7/opentallas_qkd_kvs_attn_fl_ba5_asap7_ref_gate/base/1_2_yosys.v').read_text()),None);A=T.build(g,None);cert=json.loads((r/'candidate/correspondence.json').read_text());s=(r/'full/tb_full.sv').read_text();lines=[];checks=[];targets=[]
for item in cert['copies']:
 oi=item['origin']
 if A['kind'][oi]!='ff':continue
 op=[pn for pn,bs in g.cells[oi][2].items() if A['pin_dir'][oi][pn]=='out'];assert len(op)==1;oq=g.cells[oi][2][op[0]][0];nq=item['output'];ci=item['copy'];targets.append(ci)
 checks.append(f'if(dut.n{oq}!==dut.n{nq})begin $display("NATIVE_COHORT_MISMATCH c{ci} origin={oi} trial=%0d cycle=%0d",trial,cycle);$fatal(1);end')
for line in s.splitlines():
 if line.startswith('qkd_kvs_attn_fl_ba4 old(') or 'old.u_core.u_attn_face.rdata' in line or line.startswith('if(old_'):continue
 line=line.replace('module tb_full;','module tb_native;').replace('qkd_kvs_attn_fl_ba5 dut(','qkd_kvs_attn_safe_control dut(')
 if 'ATTN_FULL_EXACT PASS' in line:line=line.replace('ATTN_FULL_EXACT PASS','ATTN_NATIVE_COHORT PASS').replace('all_public_outputs=11',f'copied_FF={len(checks)} randomized_initialization=Verilator2')
 lines.append(line)
 if line=='#0.6;':lines.extend(checks)
(r/'native/tb_native.sv').write_text('\n'.join(lines)+'\n')
source=(r/'candidate/qkd_kvs_attn_safe_control.v').read_text();ci=targets[0]
# Causal broken copied data input, exact original source retained.
pat=rf'(\bc{ci} \([^\n]*?\.D\()n\d+(\))';bad,n=re.subn(pat,r"\g<1>1'b0\2",source,count=1);assert n==1
(r/'native/candidate_mut1.v').write_text(bad)
