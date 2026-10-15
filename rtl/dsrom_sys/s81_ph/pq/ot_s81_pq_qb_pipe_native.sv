`timescale 1ns/1ps
// Opt-in physical QB successor: read address capture + SRAM output register = +2 cycles.
// Metadata stays in head; bank writes commit one cycle later under asserted loader contract.
module ot_s81_pq_qb_headp_native (
 input wire clk,rst_n,consume,input wire[9:0] aqi_d,
 input wire[15:0] h_b0,h_b1,input wire[1:0] hw_sv,
 input wire[1023:0] rd_data,input wire[19:0] aq_e,input wire[9:0] aq_p,
 // Registered per-bank write enables (wq*[k] = wv && bank(w*) == k) and write rows, same edge as
 // the former w0/w1/wv: no bank compares a bank-index constant, so ONE bank master serves all four.
 output reg[6:0] wr0,wr1,output reg[3:0] wq0,wq1,
 output reg[15:0] i0,i1,
 // Per-bank read enables share the registered index edge.
 output reg[3:0] rq0,rq1,
 output reg[255:0] hq0,hq1,output reg[9:0] he0,he1,output wire fault
);
    reg [1:0] gates; reg consume_1;
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr
        (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    reg [9:0] aqi;
    wire [8:0] w0n = (aqi[0] ? 9'd192 : 9'd0) + {1'b0, aqi[8:1]};
    wire [8:0] w1n = w0n + 9'd1;
    always @(posedge clk or negedge rst_l[0]) begin
        if (!rst_l[0]) begin aqi <= 0; wr0 <= 0; wr1 <= 0; wq0 <= 0; wq1 <= 0; end
        else begin
            aqi <= aqi_d;
`ifdef OT_S81_PQ_QBW_MUT_BANK
            wr0 <= {w1n[8:4], w1n[2:1]};
            wr1 <= {w0n[8:4], w0n[2:1]};
`else
            wr0 <= {w0n[8:4], w0n[2:1]};
            wr1 <= {w1n[8:4], w1n[2:1]};
`endif
`ifdef OT_S81_PQ_QBW_MUT_BANK
            // Mutant: the two write ports' bank enables and rows exchanged (q0's word lands at q1's row).
            wq0 <= {4{aqi[9]}} & (4'b1 << {w1n[3], w1n[0]});
            wq1 <= {4{aqi[9]}} & (4'b1 << {w0n[3], w0n[0]});
`else
            wq0 <= {4{aqi[9]}} & (4'b1 << {w0n[3], w0n[0]});
            wq1 <= {4{aqi[9]}} & (4'b1 << {w1n[3], w1n[0]});
`endif
        end
    end
    always @(posedge clk or negedge rst_l[0])
        if (!rst_l[0]) begin i0 <= 0; i1 <= 0; gates <= 0; consume_1 <= 0;
            rq0 <= 0; rq1 <= 0; end
        else begin i0 <= h_b0; i1 <= h_b1; gates <= hw_sv; consume_1 <= consume;
            rq0 <= {4{consume & hw_sv[0]}} & (4'b1 << {h_b0[3], h_b0[0]});
            rq1 <= {4{consume & hw_sv[1]}} & (4'b1 << {h_b1[3], h_b1[0]});
        end
    wire [1:0] bank0 = {i0[3], i0[0]}, bank1 = {i1[3], i1[0]};
    wire [6:0] row0 = {i0[8:4], i0[2:1]}, row1 = {i1[8:4], i1[2:1]};
    // Mutable metadata belongs beside the head read-index registers. Each bank
    // still has exactly 96 rows, with exponent/parity/written = 16 bits/row.
    reg [15:0] meta [0:3][0:95];
    reg [95:0] written [0:3];
    reg [1:0] selected0[0:2], selected1[0:2], valid[0:2];
    reg [15:0] m0[0:2],m1[0:2];
    reg sticky,check0,check1;
    reg [4:0] expected0,expected1;
    integer k,j;
    always @(posedge clk or negedge rst_l[0]) begin
      if(!rst_l[0]) begin
        sticky<=0;check0<=0;check1<=0;
        for(k=0;k<4;k=k+1) written[k]<=0;
        for(j=0;j<3;j=j+1) begin valid[j]<=0;selected0[j]<=0;selected1[j]<=0; end
      end else begin
        for(k=0;k<4;k=k+1) begin
          if(wq0[k]) begin meta[k][wr0]<={1'b1,aq_p[4:0],aq_e[9:0]}; written[k][wr0]<=1; end
          if(wq1[k]) begin meta[k][wr1]<={1'b1,aq_p[9:5],aq_e[19:10]}; written[k][wr1]<=1; end
        end
        selected0[0]<=bank0; selected1[0]<=bank1;
        valid[0]<=gates & {2{consume_1}};
        if(consume_1&&gates[0]) m0[0]<={written[bank0][row0],meta[bank0][row0][14:0]};
        if(consume_1&&gates[1]) m1[0]<={written[bank1][row1],meta[bank1][row1][14:0]};
        for(j=1;j<3;j=j+1) begin
          selected0[j]<=selected0[j-1];selected1[j]<=selected1[j-1];
          valid[j]<=valid[j-1];m0[j]<=m0[j-1];m1[j]<=m1[j-1];
        end
        check0<=valid[2][0];check1<=valid[2][1];
        expected0<=m0[2][14:10];expected1<=m1[2][14:10];
        if((valid[2][0]&&!m0[2][15]) || (valid[2][1]&&!m1[2][15])) sticky<=1;
        if(check0 && expected0!={^he0,^hq0[255:192],^hq0[191:128],^hq0[127:64],^hq0[63:0]}) sticky<=1;
        if(check1 && expected1!={^he1,^hq1[255:192],^hq1[191:128],^hq1[127:64],^hq1[63:0]}) sticky<=1;
      end
    end
    assign fault=sticky;
    always @(posedge clk) begin
      hq0<=valid[2][0] ? rd_data[256*selected0[2]+:256] : 256'd0;
`ifdef OT_S81_PQ_QB_HEAD_MUT
      hq1<=valid[2][1] ? rd_data[256*selected0[2]+:256] : 256'd0;
`else
      hq1<=valid[2][1] ? rd_data[256*selected1[2]+:256] : 256'd0;
`endif
      he0<=valid[2][0] ? m0[2][9:0] : 10'd0;
      he1<=valid[2][1] ? m1[2][9:0] : 10'd0;
    end
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_l[0]) begin
      if(consume_1&&gates[0]&&i0>=384) $fatal(1,"QB q0 index beyond production storage");
      if(consume_1&&gates[1]&&i1>=384) $fatal(1,"QB q1 index beyond production storage");
      if(aqi[9]&&(aqi[8:1]>=192||aqi[1])) $fatal(1,"QB write pair outside legal loader protocol");
    end
`endif
endmodule

module ot_s81_pq_qb_bankp_native (
 input wire clk,rst_n,input wire[6:0] wr0,wr1,input wire wq0,wq1,
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
 always @(posedge clk) rd<=raw;
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
module ot_s81_pq_qb_pipe_native (
 input wire clk,rst_n,consume,input wire[3:0] clk_bank,
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
 ot_s81_pq_qb_bankp_native u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.wr0(wr0),.wr1(wr1),
 .wq0(wq0[b]),.wq1(wq1[b]),.aq_q(aq_q),.i0(i0),.i1(i1),.rq0(rq0[b]),.rq1(rq1[b]),.rd(rd[256*b+:256]));
 end endgenerate
endmodule

// Separate physical leaf; core stays wires-only. Two fixed stages align the
// unchanged IX data and CTL broadcast fields with the pipelined QB response.
module ot_s81_pq_qb_align_native (
 input wire clk,rst_n,input wire[609:0] bc_hr,input wire[1023:0] bt_d,
 output wire[609:0] bc_hr_q,output wire[1023:0] bt_d_q
);
 wire[0:0] rst_l;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr
 (.clk(clk),.rst_n_in(rst_n),.rst_n(rst_l));
 reg[609:0] hr[0:1];reg[1023:0] bt[0:1];
 always @(posedge clk or negedge rst_l[0])
 if(!rst_l[0]) begin hr[0]<=0;hr[1]<=0;end
 else begin hr[0]<=bc_hr;hr[1]<=hr[0];end
 always @(posedge clk) begin bt[0]<=bt_d;bt[1]<=bt[0];end
 assign bc_hr_q=hr[1];assign bt_d_q=bt[1];
endmodule
