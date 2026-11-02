from pathlib import Path
import sys,json,subprocess,shutil
R=Path('/srv/opentallas-scratch2/claude/codex-s81-shiftx-1620/proof2');SRC=Path('/srv/opentallas-scratch2/claude/codex-s81-wave-1131/src');sys.path.insert(0,str(SRC/'tools/die_plan'));import bind_elab as E
report=json.load(open(R/'report.json'));assert len(report['cases'])==9
name=report['module'];sv=R/'actual'/(name+'.sv');old=R.parent/'old.sv'
f=R/'formal';f.mkdir(exist_ok=True)
(f/'miter.sv').write_text('module miter(input [33:0] B,output ok);wire[127:0]G,U;gold g(.B(B),.Y(G));gate u(.B(B),.Y(U));assign ok=(G===U);endmodule\n')
base=f'read_json "{R}/primitive.json"\nrename {name} gold\nread_verilog -sv "{sv}"\nrename {name} gate\nread_verilog -formal "{f}/miter.sv"\nhierarchy -check -top miter\nproc\nflatten\nopt_clean\n'
formal=[]
for label,extra in [('defined_inputs','-set-def-inputs'),('arbitrary_undef_inputs','')]:
 ys=f/(label+'.ys');ys.write_text(base+f'sat -verify -enable_undef {extra} -prove ok 1 -show B -show G -show U\n')
 try:E.run_yosys(ys,f/(label+'.log'),[R.parent],mem_gb=2);rc=0
 except E.ElabError:rc=1
 formal.append(dict(case=label,rc=rc));print('FORMAL',label,rc,flush=True)
 if label=='defined_inputs':assert rc==0,'candidate fails exact primitive defined/OOB-X proof'
# Actual CW address domain only: old Yosys frontend is checked, not assumed to share the Verilator failure.
oldbase=base.replace(str(sv),str(old))
ys=f/'old_yosys_cw.ys';ys.write_text(oldbase+''.join(f'sat -verify -enable_undef -set-def-inputs -set B 34\'b{format((-32*k)%(1<<34),"034b")} -prove ok 1\n' for k in range(4)))
E.run_yosys(ys,f/'old_yosys_cw.log',[R,R.parent],mem_gb=2);print('OLD_YOSYS_CW_FOUR_MASKS_PASS',flush=True)
# Exact production simulator and canonical four CW offsets. Out-of-A bits remain X in source; compare defined mask.
v=R/'verilator';v.mkdir(exist_ok=True)
(v/'tb.sv').write_text(f'''module tb;reg[33:0]B;wire[127:0]Y;reg[127:0]want;integer bad=0;{name}u(.B(B),.Y(Y));initial begin for(integer k=0;k<4;k++)begin B=34'(-32*k);want=128'hffffffff<<(32*k);#1;$display("CW k%0d B%h Y%032h want%032h",k,B,Y,want);if((Y&want)!==want)bad++;end $display("CW_MASK_ERRORS %0d",bad);if(bad)$fatal(1,"CWmask mismatch");$finish;end endmodule'''.replace(name+'u(',name+' u('))
vl=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator';assert vl.is_file(),vl
p=subprocess.run([str(vl),'--binary','--timing','--top-module','tb','-Wno-fatal','--build-jobs','1','-Mdir',str(v/'obj'),str(sv),str(v/'tb.sv')],capture_output=True,text=True);(v/'build.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr[-2000:]
p=subprocess.run([str(v/'obj/Vtb')],capture_output=True,text=True);(v/'run.log').write_text(p.stdout+p.stderr);assert p.returncode==0 and 'CW_MASK_ERRORS 0' in p.stdout,p.stdout+p.stderr;print(p.stdout,flush=True)
report.update(formal=formal,old_yosys_reachable_cw_domain='four canonical CW masks PASS; no blanket claim for arbitrary oldSV high-B',verilator='5.050 actualfourCWoffsets PASS',scope='printer portability fix; primitive JSON/ABI exact, no architectural state/cycle/reset or implicit source-event adoption')
(R/'final_report.json').write_text(json.dumps(report,indent=1)+'\n');assert all(x['rc']==0 for x in formal),'full undef proof requires diagnosis; notREADY'
