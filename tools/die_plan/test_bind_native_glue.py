"""Native backend helpers preserve memory state and X part-select behavior."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_elab as E
from bind_native_glue import NativeGlue, NativeGlueError
import bind

pytestmark = pytest.mark.skipif(not shutil.which("iverilog") or
    not (shutil.which("docker") or E.os.environ.get("OT_BIND_YOSYS")),
    reason="native Yosys and Icarus required")

def test_rejects_implicit_or_unlisted_primitive(tmp_path):
    with pytest.raises(NativeGlueError):
        NativeGlue(tmp_path, ["$memrd_v2"])
    with pytest.raises(NativeGlueError):
        NativeGlue(tmp_path, "$mem_v2")

@pytest.mark.parametrize("mutant", [False, True])
def test_native_memory_and_shift_helpers(tmp_path, mutant):
    source = """module gold(input clk,input[7:0]mask,input[1:0]a,ra,
input[7:0]d,input[31:0]words,index,output[7:0]q,s);
reg[7:0]mem[0:3]; integer i,b;
initial for(i=0;i<4;i=i+1)mem[i]=8'h11+i;
always@(posedge clk)for(b=0;b<8;b=b+1)if(mask[b])mem[a][b]<=d[b];
assign q=mem[ra]; assign s=words[index+:8];
endmodule
"""
    (tmp_path/"gold.sv").write_text(source)
    (tmp_path/"extract.sv").write_text(source.replace(
        "for(b=0;b<8;b=b+1)if(mask[b])mem[a][b]<=d[b];",
        "if(mask[0])mem[a]<=d;"))
    (tmp_path/"extract.ys").write_text(
        f"read_verilog -sv {tmp_path/'extract.sv'}\nproc\nmemory_collect\nwrite_json {tmp_path/'gold.json'}\n")
    E.run_yosys(tmp_path/"extract.ys", tmp_path/"extract.log", [tmp_path], mem_gb=2)
    cells=json.loads((tmp_path/"gold.json").read_text())["modules"]["gold"]["cells"]
    memory=next(c for c in cells.values() if c["type"]=="$mem_v2")
    shift=next(c for c in cells.values() if c["type"]=="$shiftx")
    native=NativeGlue(os.path.relpath(tmp_path/"helpers", Path.cwd()), ["$mem_v2","$shiftx"])
    def cell(c):
        return NS(ytype=c["type"], yparams=c["parameters"], dirs=c["port_directions"],
                  ports=c["connections"])
    if mutant:
        memory["parameters"]["WR_CLK_POLARITY"]="0"
    m=cell(memory)
    mc={"RD_ADDR":"ra","RD_ARST":"1'b0","RD_CLK":"1'b0","RD_DATA":"q",
        "RD_EN":"1'b1","RD_SRST":"1'b0","WR_ADDR":"a","WR_CLK":"clk","WR_DATA":"d","WR_EN":"mask"}
    body=native.emit(m,mc,"mem0")
    body+=native.emit(cell(shift),{"A":"words","B":"index","Y":"s"},"shift0")
    # Identical memories share RTL, never state. The second instance is read-only.
    mc2=dict(mc,WR_EN="8'b0",RD_DATA="q_static")
    body+=native.emit(m,mc2,"mem1")
    assert len(native.files)==2
    (tmp_path/"dut.sv").write_text("""module dut(input clk,input[7:0]mask,input[1:0]a,ra,
input[7:0]d,input[31:0]words,index,output[7:0]q,s,q_static);
"""+body+"\nendmodule\n")
    tb="""module tb; reg clk=0; reg[7:0]mask=0,d=0;reg[1:0]a=0,ra=0;
reg[31:0]words=0,index=0;wire[7:0]gq,gs,uq,us,qs;reg[7:0]gr,ur;
integer i,seed=237,bad=0;
gold g(.clk(clk),.mask(mask),.a(a),.ra(ra),.d(d),.words(words),.index(index),.q(gq),.s(gs));
dut u(.clk(clk),.mask(mask),.a(a),.ra(ra),.d(d),.words(words),.index(index),.q(uq),.s(us),.q_static(qs));
always@(posedge clk)begin gr<=gq;ur<=uq;end
initial begin
for(i=0;i<3000;i=i+1)begin
 clk=0;mask=$random(seed);d=$random(seed);a=$random(seed);ra=(i%3==0)?a:$random(seed);
 words=$random(seed);index=i%43;
 #1;clk=1;#1;
 if(gq!==uq || gs!==us || gr!==ur || qs!==(8'h11+{6'b0,ra}))bad=bad+1;
end
if(bad)$fatal(1,"native helper mismatch %0d",bad);
$display("NATIVE_GLUE_PASS checks=12000");$finish;
end endmodule
"""
    (tmp_path/"tb.sv").write_text(tb)
    subprocess.run(["iverilog","-g2012","-o",str(tmp_path/"sim"),
        str(tmp_path/"gold.sv"),str(tmp_path/"dut.sv"),str(tmp_path/"tb.sv"),
        *map(str,native.files)],check=True,capture_output=True,text=True)
    r=subprocess.run(["vvp",str(tmp_path/"sim")],capture_output=True,text=True)
    assert (r.returncode != 0) == mutant, r.stdout+r.stderr
    if not mutant: assert "NATIVE_GLUE_PASS" in r.stdout

def test_collect_memories_is_explicit_and_does_not_map_state():
    base = E.yosys_script({"top": "top"}, [], [], [], "out.json")
    selected = E.yosys_script({"top": "top", "collect_memories": True}, [], [], [], "out.json")
    assert "memory_collect" not in base
    assert "proc\nmemory_collect\nwrite_json" in selected
    assert "memory_map" not in selected
    with pytest.raises(E.ElabError):
        E.yosys_script({"top": "top", "collect_memories": "true"}, [], [], [], "out.json")
    with pytest.raises(bind.BindError, match="not supported"):
        bind._glue(NS(ytype="$mem_v2", yparams={}, src="memory", path="private_ram"), {}, "private_ram")
