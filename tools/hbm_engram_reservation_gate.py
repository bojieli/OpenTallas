#!/usr/bin/env python3
"""Real shared ownership drain/reservation guard, one physical controller only."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TB=r'''`timescale 1ps/1fs
module tb;
parameter integer EARLY=0;
reg clk=0;always #512 clk=~clk;reg rst_n=0,reserve=0;
reg[63:0]ov=0;wire[63:0]ordy,rv,ack;wire[31:0]idle;wire fault;
wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;
wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;
ot_hbm_engram_home_shared_stack dut(.core_clk(clk),.hbm_clk(clk),.pc_clk({32{clk}}),.rst_n(rst_n),.epoch_begin(1'b0),
 .engram_reservation(reserve),.owner_idle(idle),.other_k_v(ov),.other_k_we(64'h1),.other_k_rdy(ordy),
 .other_k_addr(1920'h28800000),.other_k_len(256'h1),.other_k_tag(1088'h10000),.other_k_wdata(16384'h1234),.other_k_wstrb(2048'hffffffff),
 .other_kr_v(rv),.other_kr_rdy(64'hffffffffffffffff),.other_k_wr_done(ack),
 .descriptor_v(1'b0),.descriptor_rank(7'd0),.descriptor_index(5'd0),.descriptor_address(37'd0),.fetch_start(1'b0),
 .read_v(1'b0),.read_row(5'd0),.read_sector(4'd0),.local_read_v(1'b0),.local_read_slot(2'd0),.local_read_sector(4'd0),
 .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),
 .col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(fault));
ot_hbm_svc_command_dram_pipeline_fixture dram(.clk(clk),.rst_n(rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
 .col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
integer cycle=0;always @(posedge clk)begin cycle<=cycle+1;if(cycle>1000)$fatal(1,"reservation timeout");end
initial begin
 repeat(4)@(negedge clk);rst_n=1;ov=1;
 do @(posedge clk);while(!ordy[0]);@(negedge clk);ov=0;
 if(EARLY)begin
  if(idle==32'hffffffff)$fatal(1,"missing actual outstanding native owner");
  reserve=1;repeat(5)@(negedge clk);
  if(!fault)$fatal(1,"missing reservation entry drain protection");
  $display("PASS actual busy owner reservation entry rejected");$finish;
 end
 wait(ack[0]);@(negedge clk);repeat(2)@(negedge clk);
 if(idle!=32'hffffffff || fault || dram.writes!=1)$fatal(1,"actual WR drain/trueACK precondition");
 reserve=1;ov=1;repeat(20)begin @(negedge clk);if(ordy!=0 || ack!=0 || fault || dram.writes!=1)$fatal(1,"other client admitted during exclusive reservation");end
 ov=0;reserve=0;repeat(4)@(negedge clk);
 if(fault)$fatal(1,"legal reservation release failed");
 $display("PASS actual native WR trueACK drain then exclusive reservation blocks other clients");$finish;
end
endmodule
'''
def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);tb=out/'tb.sv';tb.write_text(TB)
 paths=['rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_gather.sv','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_stream_pc_lease.sv','rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_sector_owned_stack.sv','rtl/hbm_accel/loader/service_native/tb_hbm_svc_command_dram_pipeline_fixture.sv','rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv','rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_row_store_decode.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_client.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_native_client_mux.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_shared_stack.sv']
 runs=[]
 for name,early,mut in [('legal_drained_entry',0,False),('busy_entry_rejected',1,False),('missing_guard_mutant',1,True)]:
  src=[str(ROOT/p)for p in paths]
  if mut:
   old='if(engram_reservation && !reserved_q && owner_idle!=32\'hffffffff)';text=Path(src[-1]).read_text();assert old in text
   mutant=out/'unguarded.sv';mutant.write_text(text.replace(old,'if(1\'b0)'));src[-1]=str(mutant)
  exe=out/name;cp=subprocess.run(['iverilog','-g2012','-s','tb',f'-Ptb.EARLY={early}','-o',str(exe),*src,str(tb)],capture_output=True,text=True);(out/(name+'.build.log')).write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout+cp.stderr
  rp=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(out/(name+'.run.log')).write_text(rp.stdout+rp.stderr);assert (rp.returncode==0)==(not mut),rp.stdout+rp.stderr;runs.append(dict(name=name,returncode=rp.returncode,output=rp.stdout.strip()))
 result=dict(schema='opentallas.hbm.engram.actual_reservation.v1',status='pass',runs=runs,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in paths},scope='Actual source-owned reservation/drain component with sole native bank/REF controller, true physical WR posted completion, real owner queues. Physical bank/open/REF timing state is deliberately retained. No universal service deadline, active Engram operation, upstream DMA producer or whole-kernel calendar qualification.')
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();run(a.out)
