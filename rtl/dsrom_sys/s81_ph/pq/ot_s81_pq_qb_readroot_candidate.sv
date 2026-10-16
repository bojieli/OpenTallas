`timescale 1ns/1ps
// Opt-in physical clock partition; same ideal phase and original two read edges.
// Actual root insertion, pin cuts and native timing remain unqualified.
// Canonical input SHA256 8bbde3ed38fd6d94ae99821c11d73e0f009881e084a35476206990a98c2294d1
module ot_s81_pq_qb_bankp_readroot (
 input wire clk,clk_rd,rst_n,input wire[6:0] wr0,wr1,input wire wq0,wq1,
 input wire[511:0] aq_q,input wire[15:0] i0,i1,input wire rq0,rq1,
 output reg[255:0] rd
);
 wire[0:0] rst_l;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr
 (.clk(clk),.rst_n_in(rst_n),.rst_n(rst_l));
 // Capture every incoming bank pin before decode, mux or SRAM access.
 reg[6:0] wr0_c,wr1_c;reg wq0_c,wq1_c,rq0_c,rq1_c;
 reg[511:0] aq_c;reg[15:0] i0_c,i1_c;
 always @(posedge clk) begin
   wr0_c<=wr0;wr1_c<=wr1;aq_c<=aq_q;i0_c<=i0;i1_c<=i1;
 end
 always @(posedge clk or negedge rst_l[0])
 if(!rst_l[0]) begin wq0_c<=0;wq1_c<=0;rq0_c<=0;rq1_c<=0; end
 else begin wq0_c<=wq0;wq1_c<=wq1;rq0_c<=rq0;rq1_c<=rq1; end
 wire[6:0] ra=rq0_c ? {i0_c[8:4],i0_c[2:1]} : {i1_c[8:4],i1_c[2:1]};
`ifdef OT_PQ_BENCH_TELEMETRY
 reg[95:0] rows_read;
 always @(posedge clk or negedge rst_l[0])
 if(!rst_l[0]) rows_read<=0;
 else if((rq0_c||rq1_c)&&ra<96) rows_read[ra]<=1;
`endif
 wire[6:0] wa=wq0_c ? wr0_c:wr1_c;
 wire[255:0] raw;
`ifdef OT_S81_PQ_QBX_MUT_ROW
 wire[255:0] wd=wq0_c ? aq_c[511:256]:aq_c[255:0];
`else
 wire[255:0] wd=wq0_c ? aq_c[255:0]:aq_c[511:256];
`endif
 ot_sram_1r1w_128x256_m1_r2c2 u_mem(
 .clk(clk),.r_ce_in(rq0_c||rq1_c),.r_addr_in(ra),.rd_out(raw),
 .w_ce_in(wq0_c||wq1_c),.w_addr_in(wa),.wd_in(wd),.w_mask_in({256{1'b1}}),
 .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 always @(posedge clk_rd) rd<=raw;
`ifndef SYNTHESIS
 always @(posedge clk) if(rst_l[0]) begin
   if(wq0_c&&wq1_c || rq0_c&&rq1_c) $fatal(1,"QB bank access collision");
   if((wq0_c||wq1_c)&&(rq0_c||rq1_c)&&wa==ra) $fatal(1,"QB read/write collision");
   if((wq0_c&&((rq0&&wr0_c=={i0[8:4],i0[2:1]})||(rq1&&wr0_c=={i1[8:4],i1[2:1]}))) ||
      (wq1_c&&((rq0&&wr1_c=={i0[8:4],i0[2:1]})||(rq1&&wr1_c=={i1[8:4],i1[2:1]}))))
      $fatal(1,"QB loader reads a row in the cycle after its write");
 end
`endif
endmodule

module ot_s81_pq_qb_pipe_readroot (
 input wire clk,rst_n,consume,input wire[3:0] clk_bank,clk_rd,
 input wire[9:0] aqi_d,input wire[511:0] aq_q,input wire[19:0] aq_e,input wire[9:0] aq_p,
 input wire[15:0] h_b0,h_b1,input wire[1:0] hw_sv,
 output wire[255:0] hq0,hq1,output wire[9:0] he0,he1,output wire fault
);
 wire[9:0] parity;
`ifdef OT_PQ_AQ_SIDE_PARITY
 assign parity=aq_p;
`else
 assign parity={^aq_e[19:10],^aq_q[511:448],^aq_q[447:384],^aq_q[383:320],^aq_q[319:256],
                ^aq_e[9:0],^aq_q[255:192],^aq_q[191:128],^aq_q[127:64],^aq_q[63:0]};
`endif
 wire[1023:0] rd;
 wire[6:0] wr0,wr1;wire[3:0] wq0,wq1,rq0,rq1;wire[15:0] i0,i1;
 ot_s81_pq_qb_headp_native u_head (.clk(clk),.rst_n(rst_n),.consume(consume),.aqi_d(aqi_d),
 .h_b0(h_b0),.h_b1(h_b1),.hw_sv(hw_sv),.rd_data(rd),.aq_e(aq_e),.aq_p(parity),
 .wr0(wr0),.wr1(wr1),.wq0(wq0),.wq1(wq1),.i0(i0),.i1(i1),.rq0(rq0),.rq1(rq1),
 .hq0(hq0),.hq1(hq1),.he0(he0),.he1(he1),.fault(fault));
 generate for(genvar b=0;b<4;b=b+1) begin:g_bank
 ot_s81_pq_qb_bankp_readroot u_bank(.clk(clk_bank[b]),.clk_rd(clk_rd[b]),.rst_n(rst_n),.wr0(wr0),.wr1(wr1),
 .wq0(wq0[b]),.wq1(wq1[b]),.aq_q(aq_q),.i0(i0),.i1(i1),.rq0(rq0[b]),.rq1(rq1[b]),.rd(rd[256*b+:256]));
 end endgenerate
endmodule

// Current production P10 parent; canonical SHA256 b1b2142eef1ad0da73bf3c363bc8084231e43f08d9b03ba7ab312067c8e9ff03
module ot_s81_pq_qb_pinread_readroot (
 input wire clk,rst_n,consume,input wire[3:0] clk_bank,clk_rd,
 input wire[9:0] aqi_d,input wire[511:0] aq_q,input wire[19:0] aq_e,input wire[9:0] aq_p,
 input wire[15:0] h_b0,h_b1,input wire[1:0] hw_sv,
 output wire[255:0] hq0,hq1,output wire[9:0] he0,he1,output wire fault
);
 wire[9:0] parity;
`ifdef OT_PQ_AQ_SIDE_PARITY
 assign parity=aq_p;
`else
 assign parity={^aq_e[19:10],^aq_q[511:448],^aq_q[447:384],^aq_q[383:320],^aq_q[319:256],
                ^aq_e[9:0],^aq_q[255:192],^aq_q[191:128],^aq_q[127:64],^aq_q[63:0]};
`endif
 wire[1023:0] rd;
 wire[6:0] wr0,wr1;wire[3:0] wq0,wq1,rq0,rq1;wire[15:0] i0,i1;
 ot_s81_pq_qb_headpc_native u_head (.clk(clk),.rst_n(rst_n),.consume(consume),.aqi_d(aqi_d),
 .h_b0(h_b0),.h_b1(h_b1),.hw_sv(hw_sv),.rd_data(rd),.aq_e(aq_e),.aq_p(parity),
 .wr0(wr0),.wr1(wr1),.wq0(wq0),.wq1(wq1),.i0(i0),.i1(i1),.rq0(rq0),.rq1(rq1),
 .hq0(hq0),.hq1(hq1),.he0(he0),.he1(he1),.fault(fault));
 generate for(genvar b=0;b<4;b=b+1) begin:g_bank
 ot_s81_pq_qb_bankp_readroot u_bank(.clk(clk_bank[b]),.clk_rd(clk_rd[b]),.rst_n(rst_n),.wr0(wr0),.wr1(wr1),
 .wq0(wq0[b]),.wq1(wq1[b]),.aq_q(aq_q),.i0(i0),.i1(i1),.rq0(rq0[b]),.rq1(rq1[b]),.rd(rd[256*b+:256]));
 end endgenerate
endmodule
