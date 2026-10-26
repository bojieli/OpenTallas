"""Compare emitted async-load FFs with the actual native Yosys backend."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bind
import bind_elab as E

pytestmark=pytest.mark.skipif(not shutil.which("iverilog") or not (shutil.which("docker") or E.os.environ.get("OT_BIND_YOSYS")),reason="native Yosys and Icarus required")

@pytest.fixture(scope="module")
def native(tmp_path_factory):
    d=tmp_path_factory.mktemp("aldff_native")
    modules=[]
    for cp in (0,1):
        for ap in (0,1):
            for enabled in (0,1):
                n=f"gold_{cp}_{ap}_{enabled}"
                modules.append(f"module {n}(input clk,aload,en,input[7:0]d,ad,output reg[7:0]q);\n"
                    f"always @({'posedge' if cp else 'negedge'} clk or {'posedge' if ap else 'negedge'} aload) "
                    f"if ({'' if ap else '!'}aload) q<=ad; else {'if(en) ' if enabled else ''}q<=d;\nendmodule\n")
    (d/"gold.sv").write_text("".join(modules))
    (d/"run.ys").write_text(f"read_verilog -sv {d/'gold.sv'}\nproc\nopt\nwrite_json {d/'native.json'}\nwrite_verilog -noattr {d/'native.v'}\n")
    E.run_yosys(d/"run.ys",d/"native.log",[d],mem_gb=2)
    return d,json.loads((d/"native.json").read_text())

@pytest.mark.parametrize("mutant",[False,True])
def test_async_load_matches_native_all_polarities_and_enable(native,tmp_path,mutant):
    d,j=native
    names=sorted(j['modules'])
    bodies=[]; inst=[]; seen=set()
    for i,n in enumerate(names):
        cells=[c for c in j['modules'][n]['cells'].values() if c['type'] in ('$aldff','$aldffe')]
        assert len(cells)==1
        cell=cells[0]; seen.add(cell['type'])
        params=dict(cell['parameters'])
        if mutant and i==0:
            params['ALOAD_POLARITY']='0' if params['ALOAD_POLARITY'].endswith('1') else '1'
        c=NS(ytype=cell['type'],yparams=params,src='actual native frontend')
        conn={'CLK':'clk','ALOAD':'aload','AD':'ad','D':'d','Q':'q'}
        if 'EN' in cell['connections']:conn['EN']='en'
        body=bind._glue(c,conn,f'cell_{i}')
        bodies.append(f"module dut_{i}(input clk,aload,en,input[7:0]d,ad,output wire[7:0]q);\n{body}\nendmodule\n")
        inst += [f"{n} g{i}(.clk(clk),.aload(aload),.en(en),.d(d),.ad(ad),.q(g[{8*i}+:8]));",
                 f"dut_{i} u{i}(.clk(clk),.aload(aload),.en(en),.d(d),.ad(ad),.q(u[{8*i}+:8]));"]
    assert seen=={'$aldff','$aldffe'}
    (tmp_path/'dut.sv').write_text(''.join(bodies))
    tb="module tb; reg clk=0,aload=0,en=0; reg[7:0]d=0,ad=0; wire[63:0]g,u; integer seed=17,i,bad=0;\n"+'\n'.join(inst)+"""
initial begin
 for(i=0;i<6000;i=i+1) begin
  case(i%5)
   0: clk=~clk;
   1: aload=~aload;
   2: begin d=$random(seed); ad=$random(seed); end
   3: en=~en;
   4: begin clk=~clk; d=$random(seed); end
  endcase
  #1; if(g!==u) bad=bad+1;
 end
 if(bad) $fatal(1,"async-load mismatch count=%0d",bad);
 $display("ALDFF_NATIVE_PASS checks=48000"); $finish;
end
endmodule
"""
    (tmp_path/'tb.sv').write_text(tb)
    exe=tmp_path/'sim'
    subprocess.run(['iverilog','-g2012','-o',str(exe),str(d/'native.v'),str(tmp_path/'dut.sv'),str(tmp_path/'tb.sv')],check=True,capture_output=True)
    r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
    assert (r.returncode!=0)==mutant,r.stdout+r.stderr
