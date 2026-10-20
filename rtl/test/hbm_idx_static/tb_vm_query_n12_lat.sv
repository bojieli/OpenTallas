`timescale 1ns/1ps
// HBM-BANKLAT-IDX 2026-10-19: the IDX operand-reader master ot_hbm_idx_vm_query_static_n12 at its d4g GEN2c BUDGET
// VM_RT_EXTRA (results/arch/hbm_banklat_1019/idx_budget.json, default 171) on the actual VM banks (ot_vms_bank_static)
// behind the d4g faces PIN FLOP (hfd_vms_bank_native_q0_faces: one register on every bank input -> read n+7, commit n+4)
// and die lanes of register stages, UNEQUAL per bank in rq / rr split but padded to the budget (as the die binds them).
// Downstream: the unchanged query/quant core (exact data check, as tb_vm_query_n12).
//   VIA_CTL 0 (op_SE / op_NE / op_NW-style, direct): per bank b rq lanes LQ0+3b, rr lanes = VMRT-3 - rq.
//   VIA_CTL 1 (op_SW): reader -> LOP relays -> the IDX root share ot_hbm_idx_rootctl_static_am #(VM_RT CTLRT, CR_RT 36,
//     SEL_LAT 30) index face -> rq4 lanes + pin -> banks -> rr4 lanes -> share; per bank b rq 20+2b, rr = CTLRT-1 - rq;
//     LOP = VMRT-4-CTLRT split rq/rr (die pads op_SW <-> ctl to that sum).
// MUT 0 pass; 1 the reader at the old default (n12 VM_RT_EXTRA 4) on the same lanes; 2 bank 5's rr lane one stage short
// (an unpadded lane); 3 reader VMRT-1; 4 (VIA_CTL) the share at the am_pin value VM_RT 1 on the same lanes.
module tb_vm_query_n12_lat;
`ifndef RSTL_P
`define RSTL_P 0   // L2H-IDX g2d: 1 = rootctl_am RSTL (kit-landed reset, no in-RTL relay)
`endif
`ifndef VMRT
`define VMRT 171
`endif
`ifndef CTLRT
`define CTLRT 65
`endif
`ifndef VIA_CTL
`define VIA_CTL 0
`endif
`ifndef MUT
`define MUT 0
`endif
 localparam integer MUT=`MUT, VIA=`VIA_CTL;
 localparam integer DUTRT=(MUT==1)?4:(MUT==3)?`VMRT-1:`VMRT;
 localparam integer CTLP=(MUT==4)?1:`CTLRT;
 localparam integer TOT=VIA?(`CTLRT-1):(`VMRT-3);            // bank lanes rq + rr (excluding the faces pin flop)
 localparam integer LOPQ=(`VMRT-4-`CTLRT)/2, LOPR=(`VMRT-4-`CTLRT)-LOPQ;
 localparam integer MAXD=256;
 function automatic integer lq(input integer b); lq=VIA?(20+2*b):(60+3*b); endfunction
 function automatic integer lr(input integer b); lr=TOT-lq(b)-((MUT==2&&b==5)?1:0); endfunction
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,weight_slot=0,query_slot=0;reg[6:0]query_index=0;
 reg[15:0]weight_sector=512,query_sector=0;
 wire[135:0]vm_rq;wire[2055:0]vm_rr;wire block_v;wire[4:0]block_head;wire[1:0]block_number;
 wire[1023:0]block_data;wire[15:0]head_weight;wire operand_fault;
 reg[2247:0]wr=0;wire[143:0]status;
 ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(DUTRT)) operand(.clk(clk),.rst_n(rst_n),.sid(2'd0),.weight_slot(weight_slot),
  .query_slot(query_slot),.query_index(query_index),.weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(vm_rq),.vm_rr(vm_rr),
  .block_v(block_v),.block_head(block_head),.block_number(block_number),.block_data(block_data),.head_weight(head_weight),.fault(operand_fault));
 // ---- the requester seen by the banks (reader direct, or the root share's vm_rq) and the response it receives
 wire[135:0]src_rq;wire[2055:0]src_rr;wire share_fault;
 generate if(VIA)begin:g_ctl
  reg[135:0]oq[0:MAXD];reg[2055:0]orr[0:MAXD];wire[2055:0]irr;
  initial for(integer d=0;d<=MAXD;d=d+1)begin oq[d]=0;orr[d]=0;end  // die relays power up as 0 in the bench
  always @(posedge clk)begin oq[0]<=vm_rq;orr[0]<=irr;for(integer d=1;d<=MAXD;d=d+1)begin oq[d]<=oq[d-1];orr[d]<=orr[d-1];end end
  wire[135:0]ctl_irq=rst_n?((LOPQ==0)?vm_rq:oq[LOPQ-1]):136'd0;
  assign vm_rr=(LOPR==0)?irr:orr[LOPR-1];
  ot_hbm_idx_rootctl_static_am #(.VM_RT(CTLP),.CR_RT(36),.SEL_LAT(30),.RSTL(`RSTL_P)) ctl(.clk(clk),.rst_n(rst_n),.program_we(1'b0),.program_addr(8'd0),
   .program_data(256'd0),.start(1'b0),.length(12'd0),.sel_op(),.sel_pass(),.sel_addr(),.link_flush(),.link_emit(),.link_group(),
   .link_clear(),.selected_v(4'h0),.ingest_v(),.tree_ev(4'h0),.qfault(4'h0),.sf(1'b0),.lf(1'b0),.done(),.fault(),.topk_go(1'b0),
   .topk_k(4'd0),.topk_order(1'b0),.topk_n(20'd0),.topk_m(20'd0),.topk_a_mirror(1'b0),.topk_a_base(18'd0),.topk_a_str(18'd0),
   .topk_o_mirror(1'b0),.topk_o_base(18'd0),.topk_o_str(18'd0),.topk_has_r(1'b0),.topk_r_base(18'd0),.topk_r_str(18'd0),
   .cq(),.cq_seq(),.cr(274'd0),.topk_busy(),.topk_done(),.topk_fault(),.index_rq(ctl_irq),.index_rr(irr),
   .argmax_rq(136'd0),.argmax_m(),.vm_rq(src_rq),.vm_rr(src_rr),.share_fault(share_fault));
 end else begin:g_dir
  assign src_rq=vm_rq;assign vm_rr=src_rr;assign share_fault=1'b0;
 end endgenerate
 // ---- per-bank die lanes (register stages, no reset) + the faces pin flop on every bank input
 for(genvar b=0;b<8;b=b+1)begin:bank
  reg[16:0]q[0:MAXD];reg[256:0]r[0:MAXD];reg[16:0]pin_rq;reg[280:0]pin_wq;
  wire[256:0]rr_bank;
  initial begin for(integer d=0;d<=MAXD;d=d+1)begin q[d]=0;r[d]=0;end pin_rq=0;pin_wq=0;end
  always @(posedge clk)begin
   q[0]<=src_rq[b*17+:17];r[0]<=rr_bank;
   for(integer d=1;d<=MAXD;d=d+1)begin q[d]<=q[d-1];r[d]<=r[d-1];end
  end
  wire[16:0]lane_rq=(lq(b)==0)?src_rq[b*17+:17]:q[lq(b)-1];
  // the relay contents are X before the first edges: the bank input pin flop holds 0 during reset
  always @(posedge clk)begin pin_rq<=rst_n?lane_rq:17'd0;pin_wq<=wr[b*281+:281];end
  assign src_rr[b*257+:257]=(lr(b)==0)?rr_bank:r[lr(b)-1];
  wire done,dqd,kqd,xd,x2d;wire[275:0]eg;wire[265:0]pr;
  ot_vms_bank_static #(.RG(1),.WG(1))mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),.rslot_v(pin_rq[16]),.rslot(1'b0),
   .wslot_v(pin_wq[280]),.wslot(3'd0),.rq(pin_rq),.rr(rr_bank),.wq(pin_wq),.wq_done(done),
   .dq(281'd0),.dq_done(dqd),.kq(281'd0),.kq_done(kqd),.xq(276'd0),.xq_done(xd),.xq2(276'd0),.xq2_done(x2d),.eg(eg),.pq(285'd0),.pr(pr),.status(status[b*18+:18]));
 end
 reg frame_start=0,emit_v=0;reg[4:0]emit_head=0;
 wire ql_v;wire[7:0]ql_head;wire[511:0]ql_codes;wire[31:0]ql_sc;wire[15:0]ql_w;wire query_fault;
 ot_hbm_idx_query_static_core quant(.clk(clk),.clk_quant(clk),.clk_quant_delay(clk),.clk_bank({4{clk}}),.rst_n(rst_n),.frame_start(frame_start),
  .block_v(block_v),.block_head(block_head),.block_number(block_number),.block_data(block_data),.head_weight(head_weight),
  .emit_v(emit_v),.emit_head(emit_head),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.fault(query_fault));
 reg[1023:0]x[0:127];reg[559:0]gold[0:31];reg[255:0]data;
 integer blocks=0,checked=0,errors=0,reads=0,commits=0;
 integer cycle=0,start=-1,firstblock=-1,lastblock=-1,firstquant=-1,minl=1<<30,maxl=0;
 always @(posedge clk)cycle<=cycle+1;
 always @(negedge clk)begin
  for(integer b=0;b<8;b=b+1)begin if(src_rq[b*17+16]&&rst_n)reads++;if(wr[b*281+280])commits++;end
  if(rst_n&&block_v===1'b1)begin
   blocks++;if(firstblock<0)firstblock=cycle;lastblock=cycle;
   if(block_data!==x[{block_head,block_number}]||head_weight!==16'h3f00+16'(block_head))errors++;
  end
  if(ql_v)begin
   checked++;if(firstquant<0)firstquant=cycle;
   if({ql_w,ql_sc,ql_codes}!==gold[ql_head])errors++;
  end
 end
 initial begin
  for(integer b=0;b<8;b=b+1)begin if(lq(b)+lr(b)<minl)minl=lq(b)+lr(b);if(lq(b)+lr(b)>maxl)maxl=lq(b)+lr(b);end
  $readmemh("query.hex",x);$readmemh("gold.hex",gold);
  repeat(4)@(negedge clk);rst_n=1;frame_start=1;
  @(negedge clk);frame_start=0;
  for(integer row=0;row<64;row=row+1)begin
   for(integer b=0;b<8;b=b+1)begin
    data=x[(row*8+b)/4][((row*8+b)%4)*256+:256];
    wr[b*281+:281]={1'b1,1'b0,2'd0,10'(row),3'(b),data,8'hff};
   end
   @(negedge clk);
  end
  wr=0;
  for(integer b=0;b<2;b=b+1)begin
   for(integer w=0;w<16;w=w+1)data[w*16+:16]=16'h3f00+16'(16*b+w);
   wr[b*281+:281]={1'b1,1'b0,2'd0,10'd64,3'(b),data,8'hff};
  end
  @(negedge clk);wr=0;repeat(8)@(negedge clk);
  weight_slot=1;start=cycle;@(negedge clk);weight_slot=0;repeat(16+`VMRT)@(negedge clk);
  for(integer q=0;q<128;q=q+1)begin query_slot=1;query_index=7'(q);@(negedge clk);end
  query_slot=0;repeat(40+`VMRT)@(negedge clk);
  for(integer h=0;h<32;h=h+1)begin emit_v=1;emit_head=5'(h);@(negedge clk);end
  emit_v=0;repeat(4)@(negedge clk);
  $display("IDX_VM_QUERY_N12_LAT MUT%0d via_ctl%0d vmrt%0d dut%0d ctl%0d bank_lanes%0d..%0d commits%0d reads%0d blocks%0d quant%0d errors%0d fault%0d share_fault%0d firstblock%0d",
   MUT,VIA,`VMRT,DUTRT,VIA?CTLP:0,minl,maxl,commits,reads,blocks,checked,errors,(operand_fault===1'b1)||query_fault||(|status),share_fault===1'b1,firstblock-start);
  if(errors||(operand_fault!==1'b0)||query_fault||(|status)||(share_fault!==1'b0)||blocks!=128||checked!=32||reads!=514||commits!=514)begin
   $display("IDX_VM_QUERY_N12_LAT FAIL");$fatal(1,"n12 at the d4g budget: query/weight/quant/latency mismatch");
  end
  $display("IDX_VM_QUERY_N12_LAT PASS");
  $finish;
 end
endmodule
