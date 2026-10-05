#!/usr/bin/env python3
"""Observe actual immutable mux write blocking; no replacement RTL or timing claim."""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN="d2c28c279c4b8df731f9c4937e790831529a954b"
PATHS=["rtl/chip/ot_chip_v41x_kv_reqmux.sv","rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv"]
def main(out):
 out.mkdir(parents=True,exist_ok=False)
 raw={p:subprocess.check_output(["git","show",PIN+":"+p],cwd=ROOT) for p in PATHS}
 declarations="reg clk=0; always #5 clk=~clk; reg rst_n=0; reg [3:0] cv=0,cwe=0; wire [3:0] iv,iw,ir,id,ov,ow,orr,od; wire fault;"
 instances=[]
 for n,(path,data) in enumerate(raw.items()):
  text=data.decode(); module=re.search(r"module\s+(\w+)",text).group(1)
  header=text.split(");",1)[0]
  ports=[]
  monitors={"m_v":("iv" if n==0 else "ov"),"m_we":("iw" if n==0 else "ow"),"c_rdy":("ir" if n==0 else "orr"),"c_wr_done":("id" if n==0 else "od"),"fault":"fault"}
  for direction,name in re.findall(r"\b(input|output)\s+(?:wire|reg)\s+(?:\[[^\]]+\]\s*)?(\w+)",header):
   if direction=="output":
    if name in monitors:ports.append("."+name+"("+monitors[name]+")")
   else:
    value={"clk":"clk","rst_n":"rst_n","c_v":"cv","c_we":"cwe","m_rdy":"4'hf","m_wr_done":"4'hf"}.get(name,"'0")
    ports.append("."+name+"("+value+")")
  if "clk, rst_n" in header: ports.append(".rst_n(rst_n)")
  instances.append(module+" dut"+str(n)+"("+",".join(ports)+");")
 tb="`timescale 1ns/1ps\nmodule tb; "+declarations+"\n"+"\n".join(instances)+"\n"+"""initial begin
 #2; rst_n=0; #10; rst_n=1; cv=1; cwe=0; #1;
 $display("read ov=%b ow=%b ready=%b fault=%b",ov,ow,orr,fault); if(ov!==1 || ow!==0 || orr!==1 || fault!==0) $fatal(1,"read positive failed");
 cwe=1; #1;
 if(iv!==1 || iw!==0 || id!==0) $fatal(1,"inner write-block witness changed");
 if(ov!==0 || orr!==0 || od!==0) $fatal(1,"outer write-block witness changed");
 @(posedge clk); #1; if(fault!==1) $fatal(1,"write did not fault");
 $display("PASS_READ_POSITIVE_WRITE_BLOCKED_INNER_NO_WE_NO_DONE_OUTER_NO_ACCEPT_FAULT"); $finish;
 end endmodule
"""
 with tempfile.TemporaryDirectory(prefix="parent-ckv-writepath-") as temp:
  t=Path(temp); files=[]
  for path,data in raw.items(): f=t/Path(path).name;f.write_bytes(data);files.append(str(f))
  (t/"tb.sv").write_text(tb)
  c=subprocess.run(["iverilog","-g2012","-s","tb","-o",str(t/"sim"),str(t/"tb.sv")]+files,capture_output=True,text=True)
  assert c.returncode==0,c.stderr
  r=subprocess.run(["vvp",str(t/"sim")],capture_output=True,text=True); (out/"tb.sv").write_text(tb); (out/"run.log").write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
 (out/"tb.sv").write_text(tb);(out/"compile.log").write_text(c.stdout+c.stderr);(out/"run.log").write_text(r.stdout+r.stderr)
 receipt=dict(verdict="PASS_REPRODUCED_CONNECTED_WRITE_BLOCKER",source_commit=PIN,source_pins={p:hashlib.sha256(b).hexdigest() for p,b in raw.items()},read_positive=True,inner_ckv_write_enable_forced_zero=True,inner_ckv_completion_forced_zero=True,outer_ckv_write_rejected=True,outer_fault_asserted=True,persistent_KV_qualified=False,scope="Actual two unchanged mux modules only; not full service/token, physical timing, or a corrected write path.")
 (out/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n");print(json.dumps(receipt))
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--out",type=Path,required=True);main(a.parse_args().out)
