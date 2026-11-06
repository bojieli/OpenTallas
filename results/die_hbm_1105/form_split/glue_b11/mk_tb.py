#!/usr/bin/env python3
"""HBM-FORM-SPLIT-8+REFORM-B11 glue lock-step bench generator.
    mk_tb.py COMP.sv TB.sv
REF = hfd_hgi_vms_glue_nw_t__fcore (uncut kit core, unchanged RTL); DUT = hfd_hgi_vms_glue_nw_t__p11comp #(XREG 2) = the 3
pieces with the two kit face flops on every crossing net.  Declared shift: 0 on every port (both sides keep the same
die-pin face flops, so the kit face shells are left out of both).  Random stimulus on every input, in episodes with
reset between them; each episode enables a random subset of the input groups (ring cw / ring ccw / hub / replay /
banks) so the sticky fault paths are reached first by different sources.  MUT0 must PASS; DMUT 1..4 must FAIL."""
import re, sys
from pathlib import Path
src = Path(sys.argv[1]).read_text()
m = re.search(r"module hfd_hgi_vms_glue_nw_t__p11comp #\([^)]*\) \((.*?)\);", src, re.S)
ports = []
for ln in m.group(1).split(",\n"):
    mm = re.match(r"\s*(input|output) wire (?:\[(\d+):0\] )?(\w+)", ln)
    ports.append((mm[1], int(mm[2] or 0) + 1, mm[3]))
grp = lambda n: ("ra" if n.startswith("cw_in") or n == "ring_tx_enable" else "rb" if n.startswith("ccw_in") else
                 "rt" if n.startswith("ring_tx") else
                 "hub" if n in ("client_seq", "response_enable", "response_seq", "bank_enable", "bank_client", "hub_ring_enable", "hub_ring_client") else
                 "rep" if n.startswith("replay") else "bank")
G = ["ra", "rb", "rt", "hub", "rep", "bank"]
L = ["`timescale 1ns/1ps", "`default_nettype none", "module tb;", " reg clk=0, rst_n=0; always #1 clk=~clk;"]
for d, wd, n in ports:
    if n in ("clk", "rst_n"): continue
    if d == "input": L.append(f" reg [{wd-1}:0] {n}=0;")
    else: L.append(f" wire [{wd-1}:0] r_{n}, d_{n};")
def conn(p):
    return ",".join(f".{n}({n})" if n in ("clk", "rst_n") else (f".{n}({n})" if d == "input" else f".{n}({p}_{n})") for d, wd, n in ports)
L.append(f" hfd_hgi_vms_glue_nw_t__fcore u_ref({conn('r')});")
L.append(f" hfd_hgi_vms_glue_nw_t__p11comp #(.XREG(2),.DMUT(`DMUT)) u_dut({conn('d')});")
L.append(" integer cyc=0, err=0, ep=0, live=0, act=0; reg [5:0] en; reg [31:0] dens;")
L.append(" function automatic [31:0] rb(input integer d); rb=($urandom%100)<d; endfunction")
L.append(" task automatic drive; begin")
for d, wd, n in ports:
    if d != "input" or n in ("clk", "rst_n"): continue
    g = G.index(grp(n))
    words = (wd + 31) // 32
    rnd = "{" + ",".join("$urandom" for _ in range(words)) + "}"
    if wd >= 64:
        # wide flits / beats: valid / owner / kind bits random, payload random
        L.append(f"  {n}=en[{g}]?{wd}'({rnd}):'0;")
        L.append(f"  if(en[{g}] && !rb(dens)) {n}[{wd-1}]=1'b0;")
    else:
        L.append(f"  {n}=en[{g}]?{wd}'({rnd}):'0;")
        if wd == 1: L.append(f"  if(en[{g}]) {n}=rb(dens);")
L.append(" end endtask")
L.append(" always @(negedge clk) begin")
L.append("  if(rst_n && cyc>4) begin")
for d, wd, n in ports:
    if d == "output":
        L.append(f"   if(r_{n}!==d_{n}) begin err=err+1; if(err<8) $display(\"DIFF ep %0d cyc %0d {n} ref %h dut %h\",ep,cyc,r_{n},d_{n}); end")
L.append("   if(r_ring_fault!=0 || r_vmstat[18]) act=act+1;")
L.append("   if(r_b0_pq[284]|r_b3_pq[284]|r_cw_out[2223]|r_ccw_out[2223]|r_b0_xq[275]|r_b5_xq2[275]) live=live+1;")
L.append("  end")
L.append("  if(rst_n) cyc=cyc+1;")
L.append("  drive;")
L.append(" end")
L.append(""" initial begin
  for(ep=0; ep<`EPS; ep=ep+1) begin
   en=(ep<2)?6'h3f:6'($urandom); if(ep%5==1) en=6'b000001; if(ep%5==2) en=6'b000110; if(ep%5==3) en=6'b011000;
   dens=(ep%3==0)?50:((ep%3==1)?8:90);
   rst_n=0; cyc=0; repeat(6) @(negedge clk); rst_n=1;
   repeat(`CYC) @(negedge clk);
  end
  $display("GLUE_LOCKSTEP DMUT %0d episodes %0d err %0d live %0d faultcycles %0d", `DMUT, `EPS, err, live, act);
  if(err!=0) $display("FAIL"); else $display("PASS");
  $finish;
 end
endmodule
`default_nettype wire""")
Path(sys.argv[2]).write_text("\n".join(L) + "\n")
print("ports", len(ports))
