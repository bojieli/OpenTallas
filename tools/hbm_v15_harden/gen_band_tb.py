#!/usr/bin/env python3
"""HBM-V15-HARDEN 2026-10-15: lockstep bench of one v15.1 service band master (hfd_svc_v15_<q>_s<k>, N physical PCs,
wires only) against N stand-alone ot_hbm_svc_static_pc references.  Every lane gets its own directed-random driver
(the protocol driver of split/tb_hbm_svc_pc_ready_equiv.sv: opens, staged fills, scheduled reads, prefetch/write-back
commands with randomly delayed PHY responses, retires and violations); every output bit of every lane is compared every
cycle, and every lane must show reads, block-ready cycles and completed commands (no vacuous PASS).
usage: gen_band_tb.py <band .sv> <out tb .sv>   -> prints the band module name and lane count"""
import re, sys
from pathlib import Path

W = dict(open_v=1, open_bank=1, open_epoch=16, open_count=7, fill_v=1, fill_bank=1, fill_epoch=16, fill_slot=6,
         fill_data=256, read_v=1, read_bank=1, read_epoch=16, read_slot=6, out_v=1, out_data=256, retire_v=1,
         retire_bank=1, retire_epoch=16, cmd_v=1, cmd_write=1, cmd_bank=1, cmd_epoch=16, cmd_addr=30, cmd_step=30,
         block_ready=2, bank_owned=2, busy=1, done=1, fault=1, k_v=1, k_rdy=1, k_addr=30, k_len=4, k_tag=17, k_we=1,
         k_wdata=256, k_wstrb=32, k_wr_done=1, kr_v=1, kr_rdy=1, kr_tag=17, kr_beat=4, kr_data=256)
OUT = ["out_v", "out_data", "block_ready", "bank_owned", "busy", "done", "fault", "k_v", "k_addr", "k_len", "k_tag",
       "k_we", "k_wdata", "k_wstrb", "kr_rdy"]
INP = [p for p in W if p not in OUT]

DRV = r"""
// one lane's protocol driver (from split/tb_hbm_svc_pc_ready_equiv.sv), reacting to the REFERENCE PC's outputs
module hv15_band_lane_drv #(parameter integer SEED=7, parameter integer NL=1) (
 input wire clk, input wire rst_n, output reg want_rst,
 input wire [1:0] br_a, input wire busy_a, fault_a, krr_a, kv_a, kwe_a, input wire [16:0] kt_a,
 output reg open_v,open_bank,output reg [15:0] open_epoch,output reg [6:0] open_count,
 output reg fill_v,fill_bank,output reg [15:0] fill_epoch,output reg [5:0] fill_slot,output reg [255:0] fill_data,
 output reg read_v,read_bank,output reg [15:0] read_epoch,output reg [5:0] read_slot,
 output reg retire_v,retire_bank,output reg [15:0] retire_epoch,
 output reg cmd_v,cmd_write,cmd_bank,output reg [15:0] cmd_epoch,output reg [29:0] cmd_addr,cmd_step,
 output reg k_rdy,k_wr_done,kr_v,output reg [16:0] kr_tag,output reg [3:0] kr_beat,output reg [255:0] kr_data);
 integer seed, fault_run;
 reg [15:0] ep[0:1]; reg [6:0] cnt[0:1]; reg [6:0] nxt[0:1]; reg [1:0] own; reg viol; reg was_rst;
 function integer rnd(input integer n); rnd=$unsigned($random(seed))%n; endfunction
 initial begin
  seed=SEED; fault_run=0; own=0; viol=0; was_rst=1; want_rst=0;
  {open_v,open_bank,open_epoch,open_count,fill_v,fill_bank,fill_epoch,fill_slot,fill_data,read_v,read_bank,read_epoch,
   read_slot,retire_v,retire_bank,retire_epoch,cmd_v,cmd_write,cmd_bank,cmd_epoch,cmd_addr,cmd_step,k_rdy,k_wr_done,kr_v,
   kr_tag,kr_beat,kr_data}=0;
 end
 always @(negedge clk) begin
  open_v=0;fill_v=0;read_v=0;retire_v=0;cmd_v=0;k_wr_done=0;kr_v=0; want_rst=0;
  fault_run=fault_a?fault_run+1:0;
  if(!rst_n) begin was_rst=1; own=0; end
  else if(was_rst) begin was_rst=0; own=0; viol=(rnd(4*NL)==0); end
  else if(fault_run>20 || rnd(30000)==0) want_rst=1;
  else begin
   k_rdy=(rnd(3)!=0);
   if(krr_a && rnd(3)==0) begin kr_v=1; kr_tag=(viol&&rnd(50)==0)?$random(seed):kt_a; kr_beat=0; kr_data={8{$random(seed)}}; end
   if(kwe_a && kv_a && k_rdy || busy_a && rnd(4)==0) k_wr_done=(rnd(2)==0) && (kwe_a || !viol ? 1 : rnd(2));
   if(!busy_a && rnd(25)==0) begin
    open_bank=rnd(2);
    if(!own[open_bank] || viol&&rnd(10)==0) begin
     open_v=1; open_epoch=$random(seed); open_count=(viol&&rnd(20)==0)?rnd(128):1+rnd(64);
     if(!own[open_bank]) begin own[open_bank]=1; ep[open_bank]=open_epoch; cnt[open_bank]=open_count; nxt[open_bank]=0; end
    end
   end
   if(!open_v && rnd(2)==0) begin
    fill_bank=rnd(2);
    if(own[fill_bank] && nxt[fill_bank]<cnt[fill_bank] && !(busy_a)) begin
     fill_v=1; fill_slot=nxt[fill_bank]; nxt[fill_bank]=nxt[fill_bank]+1;
     fill_epoch=(viol&&rnd(40)==0)?$random(seed):ep[fill_bank]; fill_data={8{$random(seed)}};
     if(viol&&rnd(40)==0) fill_slot=rnd(64);
    end
   end
   if(rnd(4)==0) begin read_bank=rnd(2); if(br_a[read_bank] || viol&&rnd(30)==0) begin
     read_v=1; read_epoch=ep[read_bank]; read_slot=rnd(cnt[read_bank]==0?1:cnt[read_bank]); end end
   if(!busy_a && !fill_v && !read_v && rnd(12)==0) begin
    cmd_bank=rnd(2); cmd_write=br_a[cmd_bank]?1:0;
    if(own[cmd_bank] && (cmd_write || nxt[cmd_bank]==0) || viol&&rnd(10)==0) begin
     cmd_v=1; cmd_epoch=ep[cmd_bank]; cmd_addr={$random(seed)}<<5; cmd_step=(1+rnd(8))<<5;
     if(!cmd_write) nxt[cmd_bank]=cnt[cmd_bank];
     if(cmd_write) own[cmd_bank]=0;
    end
   end
   if(!busy_a && !cmd_v && !fill_v && !read_v && rnd(60)==0) begin
    retire_bank=rnd(2); if(own[retire_bank] && br_a[retire_bank] || viol&&rnd(5)==0) begin
     retire_v=1; retire_epoch=ep[retire_bank]; own[retire_bank]=0; end
   end
  end
 end
endmodule
"""


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    txt = src.read_text()
    mod = re.search(r"^\s*module\s+(\w+)", txt, re.M).group(1)
    n = len(re.findall(r"ot_hbm_svc_static_pc\s+u_\w+\s*\(", txt))
    assert n >= 1, "no PC instances"
    L = []
    L.append("`timescale 1ns/1ps")
    L.append(DRV)
    L.append(f"module tb_hv15_band;\n parameter integer CYCLES=20000;\n reg clk=0; always #5 clk=~clk;\n reg rst_n=0;")
    for p in W:
        L.append(f" wire [{n * W[p] - 1}:0] {p};          // band-wide bus (lane k = [k*{W[p]} +: {W[p]}])")
        if p in OUT:
            L.append(f" wire [{n * W[p] - 1}:0] {p}_ref;")
    L.append(f" wire [{n - 1}:0] want_rst;")
    L.append(f" {mod} dut(.clk_pc({{{n}{{clk}}}}),.rst_n(rst_n)," + ",".join(f".{p}({p})" for p in W) + ");")
    for k in range(n):
        sl = lambda p: f"[{k * W[p]} +: {W[p]}]"
        r = lambda p: (f"{p}_ref" if p in OUT else p) + sl(p)
        L.append(f" ot_hbm_svc_static_pc ref{k}(.clk(clk),.rst_n(rst_n)," + ",".join(f".{p}({r(p)})" for p in W) + ");")
        L.append(f" hv15_band_lane_drv #(.SEED({1009 * (k + 1)}),.NL({n})) drv{k}(.clk(clk),.rst_n(rst_n),.want_rst(want_rst[{k}]),"
                 f".br_a(block_ready_ref{sl('block_ready')}),.busy_a(busy_ref[{k}]),.fault_a(fault_ref[{k}]),"
                 f".krr_a(kr_rdy_ref[{k}]),.kv_a(k_v_ref[{k}]),.kwe_a(k_we_ref[{k}]),.kt_a(k_tag_ref{sl('k_tag')}),"
                 + ",".join(f".{p}({p}{sl(p)})" for p in INP) + ");")
    cmp_a = "{" + ",".join(OUT) + "}"
    cmp_b = "{" + ",".join(p + "_ref" for p in OUT) + "}"
    L.append(f""" integer cyc, checks=0, seedoff=0, lane_reads[0:{n - 1}], lane_rdy[0:{n - 1}], lane_done[0:{n - 1}], k, minr, mind, minb;
 initial for(k=0;k<{n};k=k+1) begin lane_reads[k]=0; lane_rdy[k]=0; lane_done[k]=0; end
 always @(negedge clk) if(rst_n) begin
  checks=checks+1;
  if({cmp_a}!=={cmp_b}) $fatal(1,"BAND_EQUIV mismatch cycle=%0d out_v %b/%b busy %b/%b fault %b/%b k_v %b/%b",
     cyc,out_v,out_v_ref,busy,busy_ref,fault,fault_ref,k_v,k_v_ref);
  for(k=0;k<{n};k=k+1) begin
   if(out_v_ref[k]) lane_reads[k]=lane_reads[k]+1;
   if(block_ready_ref[2*k +: 2]!=0) lane_rdy[k]=lane_rdy[k]+1;
   if(done_ref[k]) lane_done[k]=lane_done[k]+1;
  end
 end
 initial begin
  for(cyc=0;cyc<CYCLES;cyc=cyc+1) begin
   @(posedge clk); #1;
   if(!rst_n) rst_n=1; else if(|want_rst) rst_n=0;
  end
  minr=lane_reads[0]; mind=lane_done[0]; minb=lane_rdy[0];
  for(k=1;k<{n};k=k+1) begin if(lane_reads[k]<minr) minr=lane_reads[k]; if(lane_done[k]<mind) mind=lane_done[k];
   if(lane_rdy[k]<minb) minb=lane_rdy[k]; end
  for(k=0;k<{n};k=k+1) $display("lane %0d reads=%0d dones=%0d ready=%0d",k,lane_reads[k],lane_done[k],lane_rdy[k]);
  if(minr==0 || mind==0 || minb==0) $fatal(1,"BAND_EQUIV vacuous lane: min reads=%0d dones=%0d ready=%0d",minr,mind,minb);
  $display("BAND_EQUIV PASS band={mod} lanes={n} cycles=%0d checks=%0d min_lane_reads=%0d min_lane_dones=%0d min_lane_ready=%0d",
           CYCLES,checks,minr,mind,minb);
  $finish;
 end
endmodule""")
    # per-PC clock entries (H-DIE grant 7aa4a2686): pulsing clk_pc[k] alone must update PC k only
    L.append(f"""module tb_hv15_band_clk;
 reg [{n - 1}:0] clk_pc=0; reg rst_n=0; integer k,j,checks=0;
 wire [{2 * n - 1}:0] bank_owned;""")
    for p in W:
        if p not in OUT and p != "bank_owned":
            val = "{%d{1'b1}}" % (n * W[p]) if p == "open_v" else ("{%d{7'd1}}" % n if p == "open_count" else "0")
            L.append(f" wire [{n * W[p] - 1}:0] {p}={val};")
    L.append(f" {mod} dut(.clk_pc(clk_pc),.rst_n(rst_n)," + ",".join(f".{p}({p})" for p in W if p in INP) + ",.bank_owned(bank_owned)"
             + "".join(f",.{p}()" for p in OUT if p != "bank_owned") + ");")
    L.append(f""" initial begin
  for(k=0;k<{n};k=k+1) begin
   rst_n=1; clk_pc=0; #1; rst_n=0; #2; rst_n=1; #2;
   clk_pc={n}'b1<<k; #2; clk_pc=0; #2;
   for(j=0;j<{n};j=j+1) begin
    if(bank_owned[2*j +: 2] !== (j==k ? 2'b01 : 2'b00)) $fatal(1,"BAND_CLOCK owner k=%0d j=%0d owned=%b",k,j,bank_owned[2*j +: 2]);
    checks=checks+1;
   end
  end
  $display("BAND_CLOCK_OWNERSHIP PASS lanes={n} checks=%0d",checks); $finish;
 end
endmodule""")
    out.write_text("\n".join(L) + "\n")
    print(mod, n)


if __name__ == "__main__":
    main()
