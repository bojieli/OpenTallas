"""Extract and exercise the actual emitted reset nodes, without arithmetic replication."""
from pathlib import Path
import json,re,hashlib,sys,subprocess
root=Path.cwd();receipt=json.loads((root/'results/arch/qwen_flat_native_2000/construction.json').read_text());nodes=receipt['reset_forest_nodes'];source=root/'rtl/qwen_flat_native_2000/qfd_flat_ml1_native_bounded.sv';out=Path(sys.argv[1]).resolve();out.mkdir(exist_ok=False,parents=True)
text=source.read_text();connections={r['bit']:r for r in nodes};lines=[]
for line in text.splitlines():
 if 'qfd_lctx_full32_dff_pn0 'in line:
  mt=re.search(r'\.Q\(n_(\d+)\)',line)
  if mt and int(mt[1])in connections:lines.append(line)
assert len(lines)==len(nodes)==76
wires={2,3}|{r['bit']for r in nodes}|{r['parent']for r in nodes}
sv='module reset_extract(input wire clk,rst_n,output wire [75:0] q);\nwire '+','.join('n_'+str(x)for x in sorted(wires))+';\nassign n_2=clk;assign n_3=rst_n;\n'+'\n'.join(lines)+'\nassign q={'+','.join('n_'+str(r['bit'])for r in reversed(nodes))+'};endmodule\n'
sv+='module tb_reset_extract;reg clk=0;always #5 clk=~clk;reg rst_n=0;wire[75:0]q;integer age=0,checks=0;reset_extract dut(clk,rst_n,q);\nalways @(posedge clk)begin if(!rst_n)age=0;else age=age+1;#1;\n'
for i,node in enumerate(nodes):sv+=f'if(q[{i}] !== (age>={node["level"]}))$fatal(1,"RESET_LEVEL_FAIL node{i} age=%0d q=%b",age,q[{i}]);checks=checks+1;\n'
sv+='end\ninitial begin repeat(5)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);#2;rst_n=0;#1;if(q!==76\'d0)$fatal(1,"ASYNC_ASSERT_FAIL");repeat(4)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);$display("RESET_FOREST_PASS nodes=76 levels=3 checks=%0d dirty_async=1",checks);$finish;end endmodule\n'
(out/'reset_extract.sv').write_text(sv)
(out/'identity.json').write_text(json.dumps(dict(parent_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),helper_source_sha256=hashlib.sha256((root/'rtl/qwen_flat_native_2000/qfd_flat_ml1_native_helpers.sv').read_bytes()).hexdigest(),scope='Exact76 emitted reset FF instance lines; original actual clock; no arithmetic or SRAM substitution'),indent=2)+'\n')
v=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator';cmd=[str(v),'--binary','--timing','-j','2','-Wno-fatal','--top-module','tb_reset_extract','-Mdir',str(out/'obj'),str(out/'reset_extract.sv'),'rtl/qwen_flat_native_2000/qfd_flat_ml1_native_helpers.sv']
with(out/'build.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
with(out/'run.log').open('w')as f:subprocess.run([str(out/'obj/Vtb_reset_extract')],stdout=f,stderr=subprocess.STDOUT,check=True)
print((out/'run.log').read_text())
