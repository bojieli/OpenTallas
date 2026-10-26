"""Run inside an admitted ORFS container with candidate rtl_lint.py in /checks."""
import importlib.util,json
from pathlib import Path
p=Path('/checks/rtl_lint.py');s=importlib.util.spec_from_file_location('lint',p);lint=importlib.util.module_from_spec(s);s.loader.exec_module(lint)
base=Path('/checks/fixtures');base.mkdir(exist_ok=True)
positive='''module top #(parameter integer N=1)(input ck,input x,output reg q);
generate if(N==2) begin always @(posedge ck) q<=x; end
else begin missing_when_wrong_parameter u_missing(); end endgenerate endmodule\n'''
cases={'parameter_positive':(positive,2,True),'parameter_mutant':(positive,1,False),
 'implicit':('module top #(parameter integer N=1)(input ck,input x,output q); assign q=implicit_net; endmodule\n',2,False),
 'undriven':('module top #(parameter integer N=1)(input ck,input x,output reg q); wire orphan; always @(posedge ck) q<=orphan; endmodule\n',2,False),
 'missing':('module top #(parameter integer N=1)(input ck,input x,output q); missing_module u(.x(x),.q(q)); endmodule\n',2,False)}
results={}
for name,(rtl,n,expected) in cases.items():
 k=base/name;k.mkdir(exist_ok=True);(k/'dut.sv').write_text(rtl)
 (k/'config.mk').write_text(f'export DESIGN_NAME = top\nexport VERILOG_FILES = {k}/dut.sv\nexport VERILOG_TOP_PARAMS = N {n}\n')
 rc=lint.run(k);d=json.loads((k/'rtl_lint.json').read_text());actual=d['verdict']=='PASS';results[name]=dict(verdict=d['verdict'],expected_pass=expected,rc=rc,errors=d['errors']);assert actual==expected,(name,d)
(Path('/checks/control_results.json')).write_text(json.dumps(results,indent=2)+'\n');print('RTL_LINT_CONTROLS 5/5 PASS')
