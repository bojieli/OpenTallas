from pathlib import Path
import importlib.util,json,subprocess
root=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('rtl_lint',root/'rtl_lint.py');lint=importlib.util.module_from_spec(sp);sp.loader.exec_module(lint)
yosys='/home/ubuntu/.local/opentallas-tools/bin/yosys'
rows=[]
for name,rtl,params,expected in [
 ('production_valid','module demo #(parameter MODE=0)(input a,output y); generate if(MODE==1) assign y=a; else nonexistent broken(a,y); endgenerate endmodule','MODE 1',0),
 ('production_bad_default_clean','module demo #(parameter MODE=1)(input a,output y); generate if(MODE==1) assign y=a; else begin wire floating; assign y=floating; end endgenerate endmodule','MODE 2',1),
 ('unknown_parameter','module demo(input a,output y); assign y=a; endmodule','MODE 1',1),
]:
 k=root/name;k.mkdir(exist_ok=True);(k/'demo.sv').write_text(rtl)
 (k/'config.mk').write_text(f'export DESIGN_NAME = demo\nexport VERILOG_FILES = {k}/demo.sv\nexport VERILOG_TOP_PARAMS = {params}\n')
 rc=lint.run(k,yosys)
 rows.append({'name':name,'rc':rc,'expected':expected,'record':json.loads((k/'rtl_lint.json').read_text())})
 assert rc==expected,(name,rc,expected)
 if name=='production_bad_default_clean':
  old=root/'mutant.ys';old.write_text(lint.script(k).replace(' -chparam MODE 2',''))
  m=subprocess.run([yosys,'-q','-s',str(old)],capture_output=True,text=True)
  assert m.returncode==0,m.stdout+m.stderr
  rows.append({'name':'mutant_ignores_params','rc':m.returncode,'expected':0,'why':'old checker falsely passes the clean default instead of the broken production specialization'})
(root/'controls.json').write_text(json.dumps(rows,indent=2)+'\n')
print('TOP_PARAM_CONTROLS PASS',len(rows))
