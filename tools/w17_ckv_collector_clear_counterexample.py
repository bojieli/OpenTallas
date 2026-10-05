#!/usr/bin/env python3
"""Unchanged full service counterexample: selection clear loses npresent reset."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];PIN='d2c28c279c4b8df731f9c4937e790831529a954b'
SOURCES=['rtl/chip/'+x+'.sv' for x in ['ot_chip_v41x_ckv_die_service','ot_chip_v41x_ckv_row_encoder','ot_chip_v41x_ckv_sel_ids','ot_chip_v41x_ckv_sel_fetch','ot_chip_v41x_ckv_selected_dma','ot_chip_v41x_ckv_fp4_decode','ot_chip_v41x_ckv_stream_merge']]
BENCH=r'''
`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;reg rst_n=0,sel=0;wire re;wire[14:0]addr;reg[511:0]rq=0;
reg[2:0]rx=0;wire fault;wire[5:0]fc;
ot_chip_v41x_ckv_die_service #(.K(512),.NSLOT(64)) dut(.clk(clk),.rst_n(rst_n),.sel_v(sel),.sel_vmword(15'd0),.nw_we(1'b0),.nw_addr(30'd0),.nw_data(1024'd0),.vm_re(re),.vm_raddr(addr),.vm_rq(rq),.vm_busy(),.c_v(),.c_rdy(4'hf),.c_addr(),.c_len(),.c_tag(),.c_we(),.c_wdata(),.c_wstrb(),.c_wr_done(4'd0),.c_sv(4'd0),.c_srdy(),.c_stag(64'd0),.c_sbeat(16'd0),.c_sdata(1024'd0),.ag_tx_valid(),.ag_tx_ready(1'b1),.ag_tx_rank(),.ag_tx_gid(),.ag_tx_row(),.ag_rx_valid(rx),.ag_rx_rank({10'd0,10'd0,10'd16}),.ag_rx_gid({21'd0,21'd0,21'd16}),.ag_rx_row(6912'd0),.job_v(1'b0),.job_ready(),.kv_v(),.kv_ready(1'b0),.kv_m(),.kv_w(),.job_done(),.fault(fault),.fault_code(fc),.rows_ready(),.st_rows_local(),.st_rows_remote(),.st_cycles_to_ready());
integer cyc=0;
always @(posedge clk)if(re===1'b1)for(integer j=0;j<16;j=j+1)rq[j*32+:32]<=32'(addr*16+j);
always @(negedge clk)begin
 cyc=cyc+1;if(cyc==5)rst_n=1;sel=(cyc==7||cyc==210);rx=(cyc==200)?3'b001:0;
 if(cyc==199)begin
  if(fault!==1'b0||dut.id_done!==1'b1||dut.id_count!==10'd512||dut.rd_act!==1'b0)$fatal(1,"fixture ID pipeline not retired");
 end
 if(cyc==202)begin
  if(fault!==1'b0||dut.npresent!==11'd1||dut.present[16]!==1'b1)$fatal(1,"fixture prior row not captured");
 end
 if(cyc==212)begin
  if(fault!==1'b0||dut.present!==512'd0||dut.npresent!==11'd1)$fatal(1,"unexpected collector reset outcome");
  $display("REPRODUCED_CLEAR_FAILURE old_count=1 new_present=0 new_count=1 expected_new_count=0");$finish;
 end
 if(cyc==300)$fatal(1,"collector fixture finite bound");
end
endmodule
'''
def main(out):
 pins={}
 with tempfile.TemporaryDirectory(prefix='w17-collector-clear-',dir='/home/ubuntu') as tmp:
  d=pathlib.Path(tmp);files=[]
  for i,p in enumerate(SOURCES):
   raw=subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT);pins[p]=dict(commit=PIN,path=p,sha256=hashlib.sha256(raw).hexdigest());f=d/f's{i}.sv';f.write_bytes(raw);files.append(str(f))
  b=d/'tb.sv';b.write_text(BENCH);c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'gate'),str(b),*files],capture_output=True,text=True,timeout=30)
  if c.returncode:raise RuntimeError(c.stderr)
  run=subprocess.run(['vvp',str(d/'gate')],capture_output=True,text=True,timeout=30);log=run.stdout+run.stderr
  ok=run.returncode==0 and 'REPRODUCED_CLEAR_FAILURE old_count=1 new_present=0 new_count=1 expected_new_count=0' in log
  r=dict(status='REPRODUCED_ORIGINAL_COLLECTOR_CLEAR_FAILURE' if ok else 'FAIL_COUNTEREXAMPLE_FIXTURE',source_pins=pins,bench_sha256=hashlib.sha256(BENCH.encode()).hexdigest(),run_returncode=run.returncode,log=log,compile_log=c.stderr,scope='Actual unchanged K512/NSLOT64 service, 512 real ID input entries, one valid old peer row then new sel pulse allowed by original guard. Partial old epoch; not a safe admitted reselection or full-token numerical proof. No internal forces/source edits.',required_correction='Atomic selection clear priority plus no old collector writes/peer credits in-flight and all old jobs/writeowners/final consumer retired before selection admission',hardware_admission=False)
 assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n');print(log);return ok
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();raise SystemExit(0 if main(a.out) else 1)
