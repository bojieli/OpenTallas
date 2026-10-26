`timescale 1ns/1ps
// HBMc/TILES 10-22: random differential lockstep (all outputs + both payload r_ce/w_ce every edge) of the issue-restructured
// lane vs the exact df174186f reference; biased-legal stimulus with 1/3000 malformed fields, reset every 3000 edges.
module tb_eq;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0; reg [2:0] bank_id=3;
 reg bv,bb,st,sb,lv; reg [15:0] bep,sep,base; reg [1:0] fv,fb; reg [11:0] fs; reg [31:0] fe; reg [511:0] fd;
 reg [7:0] f0a,f1a,pba; reg [61:0] cmd;
 wire [1:0] f0,f1,pb,bz,ft,ov; wire [1:0] br[0:1],dq_[0:1]; wire [2:0] db[0:1]; wire [280:0] ld[0:1],dq[0:1];
`define INST(M,i) M #(.NPC(2)) u``i(.clk(clk),.rst_n(rst_n),.bank_id(bank_id),.begin_v_i(bv),.begin_bank_i(bb),.begin_epoch_i(bep),\
 .start_i(st),.start_bank_i(sb),.start_epoch_i(sep),.start_base_sector_i(base),.fill_v_i(fv),.fill_bank_i(fb),.fill_slot_i(fs),\
 .fill_epoch_i(fe),.fill_data_i(fd),.full0_all(f0a),.full1_all(f1a),.pcbad_all(pba),.full0(f0[i]),.full1(f1[i]),.pcbad(pb[i]),\
 .block_ready(br[i]),.busy(bz[i]),.fault(ft[i]),.load_v_i(lv),.load_cmd_i(cmd),.load_dest_bank(db[i]),.load_dest_q(dq_[i]),\
 .load_dq(ld[i]),.load_out_v(ov[i]),.dq(dq[i]));
 `ifdef SPEC
 defparam u0.WCE_SPEC=1;
`endif
`ifdef SHPRE
 defparam u0.SHPRE=1;
`endif
`ifdef RPIPE
 defparam u0.RPIPE=1;
`endif
 // RPIPE (HBMc/TILES3 10-22): the DUT read port and dq / load outputs are one edge later than the reference: compare them
 // with the reference's previous-edge values; cycles where the reference fault changes are skipped (fault gates outputs
 // at the later edge), as are the 2 edges after a reset release.
 reg [1:0] p_rce; reg p_ov; reg [1:0] p_dqq; reg [2:0] p_db; reg [280:0] p_ld,p_dq; reg p_ft=0; integer p_rst=0;
 `INST(ot_hbm_svc_vmdel_lane_load_static,0)
 `INST(gold_ot_hbm_svc_vmdel_lane_load_static,1)
 integer cyc=0,err=0,rce=0,iss=0,nf=0; reg spec_f=0; reg [15:0] ep0,ep1;
 always @(negedge clk) begin
  cyc=cyc+1;
`ifdef SPEC
  // WCE_SPEC=1: exact until the first duplicate fill (reference pbad; payload contents diverge from then on, also
  // across resets); a w_ce difference is legal only on a duplicate edge (reference fill_base && seen_current).
  if(u1.pc[0].pbad||u1.pc[1].pbad) spec_f=1;
  if(rst_n && !spec_f && ((u0.pc[0].u_payload.w_ce_in!==u1.pc[0].u_payload.w_ce_in && !u1.pc[0].seen_current) ||
     (u0.pc[1].u_payload.w_ce_in!==u1.pc[1].u_payload.w_ce_in && !u1.pc[1].seen_current))) begin err=err+1; $display("SPEC_WCE_NON_DUP %0d",cyc); end
  if(rst_n && !spec_f && (u0.pc[0].u_payload.w_ce_in!==u1.pc[0].u_payload.w_ce_in || u0.pc[1].u_payload.w_ce_in!==u1.pc[1].u_payload.w_ce_in)) spec_f=1;
`endif
  if(rst_n && !spec_f) begin
`ifdef RPIPE
   if(p_rst>=2) begin
   if({u0.pc[0].u_payload.r_ce_in,u0.pc[1].u_payload.r_ce_in,u0.pc[0].u_payload.w_ce_in,u0.pc[1].u_payload.w_ce_in}!==
      {p_rce,u1.pc[0].u_payload.w_ce_in,u1.pc[1].u_payload.w_ce_in}) begin err=err+1; if(err<5)$display("CE_MISMATCH %0d",cyc); end
   if({f0[0],f1[0],pb[0],bz[0],ft[0],br[0]}!=={f0[1],f1[1],pb[1],bz[1],ft[1],br[1]} ||
      (ft[1]==p_ft && {ov[0],dq_[0],db[0],ld[0],dq[0]}!=={p_ov,p_dqq,p_db,p_ld,p_dq})) begin err=err+1; if(err<5)$display("OUT_MISMATCH %0d",cyc); end
   end
`else
   if({u0.pc[0].u_payload.r_ce_in,u0.pc[1].u_payload.r_ce_in,u0.pc[0].u_payload.w_ce_in,u0.pc[1].u_payload.w_ce_in}!==
      {u1.pc[0].u_payload.r_ce_in,u1.pc[1].u_payload.r_ce_in,u1.pc[0].u_payload.w_ce_in,u1.pc[1].u_payload.w_ce_in}) begin err=err+1; if(err<5)$display("CE_MISMATCH %0d",cyc); end
   if({f0[0],f1[0],pb[0],bz[0],ft[0],ov[0],br[0],dq_[0],db[0],ld[0],dq[0]}!=={f0[1],f1[1],pb[1],bz[1],ft[1],ov[1],br[1],dq_[1],db[1],ld[1],dq[1]}) begin err=err+1; if(err<5)$display("OUT_MISMATCH %0d",cyc); end
`endif
  nf=nf+(ft[1]!=0); rce=rce+u0.pc[0].u_payload.r_ce_in+u0.pc[1].u_payload.r_ce_in; iss=iss+u0.load_cmd_ok;
  end
  p_rce={u1.pc[0].u_payload.r_ce_in,u1.pc[1].u_payload.r_ce_in}; p_ov=ov[1]; p_dqq=dq_[1]; p_db=db[1]; p_ld=ld[1]; p_dq=dq[1]; p_ft=ft[1];
  p_rst=rst_n?p_rst+1:0;
  // stimulus: biased random; periodic resets clear sticky faults
  if(cyc%3000==0) rst_n=0; else if(cyc%3000==8) rst_n=1;
  bb=$urandom; bv=(($urandom%8)==0)&&((!u1.owned[bb]&&!u1.start)||($urandom%3000)==0); bep=bb?16'd2:16'd1;
  sb=$urandom; st=(($urandom%200)==0)&&(!u1.running&&!u1.start||($urandom%3000)==0); sep=(($urandom%3000)==0)?16'd3:(sb?16'd2:16'd1); base=(($urandom%3000)==0)?$urandom:16'($urandom%8)*32; if(!(u1.owned[sb]&&u1.block_ready_c[sb])&&($urandom%3000)!=0) st=0;
  fv=$urandom; fb=$urandom; fs={6'($urandom),6'($urandom)}; fe=(($urandom%20)==0)?{16'($urandom%4),16'($urandom%4)}:{fb[1]?16'd2:16'd1,fb[0]?16'd2:16'd1}; fd={$urandom,$urandom,$urandom,$urandom}<<($urandom%400);
  f0a=($urandom%3000)?8'hff:$urandom; f1a=($urandom%3000)?8'hff:$urandom; pba=($urandom%20000)?0:$urandom;
  cmd={$urandom,$urandom}; cmd[0]=$urandom; cmd[56]=(($urandom%40)==0); lv=(($urandom%3)==0)&&((!u1.running&&!st&&!u1.start&&u1.owned[cmd[0]]&&u1.block_ready_c[cmd[0]])||($urandom%3000)==0);
  cmd[16:1]=(($urandom%3000)==0)?16'd3:(cmd[0]?16'd2:16'd1); cmd[55:52]=(($urandom%3000)==0)?cmd[55:52]:4'(1+$urandom%8); cmd[51:49]=(($urandom%3000)==0)?cmd[51:49]:3'((cmd[55:52]<8)?$urandom%2:0); cmd[29:25]=(($urandom%3000)==0)?cmd[29:25]:5'd0; cmd[18:17]=(($urandom%3000)==0)?2'd3:2'($urandom%2);
  cmd[32:30]=(($urandom%3000)==0)?3'd3:3'($urandom%3);
 end
 reg seen_f=0; integer nfd=0;
 always @(posedge clk) begin if(!rst_n) seen_f<=0; else if(!seen_f && rst_n && ((u1.load_v&&!u1.command_ok)||(u1.begin_v&&u1.owned[u1.begin_bank])||(u1.lstart&&!u1.start_ok))) begin seen_f<=1; nfd=nfd+1; if(nfd<12) $display("FIRST_MALFORMED cyc=%0d sticky=%b bad=%b lv=%b cok=%b lc0=%b off=%h sub=%h lf=%h g=%h rdy=%b ep=%h e0=%h e1=%h ln=%h| bv=%b own=%b lstart=%b sok=%b st=%b run=%b",cyc,u1.sticky,u1.bad,u1.load_v,u1.command_ok,u1.load_cmd[0],u1.load_cmd[29:25],u1.load_cmd[51:49],u1.load_cmd[32:30],u1.load_cmd[18:17],u1.block_ready_c,u1.load_cmd[16:1],u1.epoch0,u1.epoch1,u1.load_cmd[55:52],u1.begin_v,u1.owned,u1.lstart,u1.start_ok,u1.start,u1.running); end end
 initial begin #4000000; $display("EQ_DONE cycles=%0d err=%0d rce=%0d load_cmd_ok=%0d fault_cycles=%0d",cyc,err,rce,iss,nf); if(err)$fatal(1,"EQ FAIL"); $display("DMA_EQ PASS"); $finish; end
endmodule
