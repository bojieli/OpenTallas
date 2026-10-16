`timescale 1ns/1ps
// P5 candidate: capture all1024 incoming bank-data bits before4:1selection.
// Matching valid/select/metadata stage adds exactly1normal read edge; original P4 source stays intact.
module ot_s81_pq_qb_headpc_native (
 input wire clk,rst_n,consume,input wire[9:0] aqi_d,
 input wire[15:0] h_b0,h_b1,input wire[1:0] hw_sv,
 input wire[1023:0] rd_data,input wire[19:0] aq_e,input wire[9:0] aq_p,
 // Registered per-bank write enables (wq*[k] = wv && bank(w*) == k) and write rows, same edge as
 // the former w0/w1/wv: no bank compares a bank-index constant, so ONE bank master serves all four.
 output reg[6:0] wr0,wr1,output reg[3:0] wq0,wq1,
 output reg[15:0] i0,i1,
 // Per-bank read enables share the registered index edge. P9: decoded from the pin-capture flops
 // (consume_1, gates, i0/i1 bank bits) at the output instead of from the pins, same edge, so every
 // head input pin loads one capture flop (P8 native audit: h_b*/consume/hw_sv captures up to 244.6 ps).
 output wire[3:0] rq0,rq1,
 output reg[255:0] hq0,hq1,output reg[9:0] he0,he1,output wire fault
);
    reg [1:0] gates; reg consume_1;
    // Reset: region 0 = index/enable/pipe control, regions 1..4 = the written[] bits of bank 0..3 (96 each).
    // The 6,144 metadata flops carry no reset (gate p1: one relay drove 8,103 loads through the meta enables).
    wire [4:0] rst_l;
    ot_rst_relay #(.REGIONS(5), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr
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
        if (!rst_l[0]) begin i0 <= 0; i1 <= 0; gates <= 0; consume_1 <= 0; end
        else begin i0 <= h_b0; i1 <= h_b1; gates <= hw_sv; consume_1 <= consume; end
    assign rq0 = {4{consume_1 & gates[0]}} & (4'b1 << {i0[3], i0[0]});
    assign rq1 = {4{consume_1 & gates[1]}} & (4'b1 << {i1[3], i1[0]});
    wire [1:0] bank0 = {i0[3], i0[0]}, bank1 = {i1[3], i1[0]};
    wire [6:0] row0 = {i0[8:4], i0[2:1]}, row1 = {i1[8:4], i1[2:1]};
    // Mutable metadata belongs beside the head read-index registers. Each bank
    // still has exactly 96 rows, with exponent/parity/written = 16 bits/row.
    reg [15:0] meta [0:3][0:95];
    wire [95:0] written [0:3];
    reg [1:0] selected0[0:3], selected1[0:3], valid[0:3];
    reg [15:0] m0[0:3],m1[0:3];
    reg sticky,check0,check1;
    reg [4:0] expected0,expected1;
    integer k,j;
    // Metadata write stage (gate p1: aq_e/aq_p ports fanned out to 391-418 enable-mux loads): the AQ metadata
    // word and the registered write enables/rows are captured once more, one copy per bank, and the head-local
    // metadata commits one edge after the bank data (bank wq/wr outputs unchanged). Rows are written by the loader
    // before any read of the same row (loader contract: the +2 read pipeline already orders reads after writes).
    wire [15:0] rd0_b [0:3], rd1_b [0:3];
    reg [29:0] aqm_q [0:3];
    reg [6:0] wr0_d [0:3], wr1_d [0:3];
    reg wq0_d [0:3], wq1_d [0:3];
    genvar gb;
    generate for (gb = 0; gb < 4; gb = gb + 1) begin : g_meta
        always @(posedge clk) begin
            aqm_q[gb] <= {aq_p, aq_e};
            wr0_d[gb] <= wr0; wr1_d[gb] <= wr1;
            wq0_d[gb] <= wq0[gb]; wq1_d[gb] <= wq1[gb];
            if (wq0_d[gb]) meta[gb][wr0_d[gb]] <= {1'b1, aqm_q[gb][24:20], aqm_q[gb][9:0]};
            if (wq1_d[gb]) meta[gb][wr1_d[gb]] <= {1'b1, aqm_q[gb][29:25], aqm_q[gb][19:10]};
        end
        reg [95:0] wbits;
        always @(posedge clk or negedge rst_l[gb+1]) begin
            if (!rst_l[gb+1]) wbits <= 96'd0;
            else begin
                if (wq0_d[gb]) wbits[wr0_d[gb]] <= 1'b1;
                if (wq1_d[gb]) wbits[wr1_d[gb]] <= 1'b1;
            end
        end
        assign written[gb] = wbits;
        // Per-bank read-index copies (gate p2: i0/i1[2:1] drove ~3,600 read-mux loads each): each bank's 96:1
        // metadata read uses its own register copy, loaded on the same edge as i0/i1 (0 cycles); the i0/i1
        // output pins keep their own flops.
        // P6 (10-15): the four per-bank copies were identical registers; synthesis folded them into ONE flop per
        // bit (gate P5: g_meta[1].r0c[0] 5,900 loads). Now (* keep *) (ot_keep_regs.tcl keeps the flop cells) and
        // four copies per bank, each selecting one 4-bit slice of the 16-bit row (~370 loads per bit), same edge.
        // P9 (10-15): the copies load from the i0/i1 capture flops one edge later (were 16 direct loads per
        // h_b* pin); the edge is absorbed by the m*[1] pure-delay stage below, 0 added cycles.
        (* keep *) reg [6:0] r0c [0:3];
        (* keep *) reg [6:0] r1c [0:3];
`ifdef OT_S81_PQ_HEADPC_MUT_R0C
        // Mutant: copies load from the pins as in P8 while the metadata line is shortened (one edge early).
        wire [6:0] r0n = {h_b0[8:4], h_b0[2:1]}, r1n = {h_b1[8:4], h_b1[2:1]};
`else
        wire [6:0] r0n = row0, r1n = row1;
`endif
        always @(posedge clk) begin
            r0c[0] <= r0n; r0c[1] <= r0n; r0c[2] <= r0n; r0c[3] <= r0n;
            r1c[0] <= r1n; r1c[1] <= r1n; r1c[2] <= r1n; r1c[3] <= r1n;
        end
        assign rd0_b[gb] = {written[gb][r0c[3]], meta[gb][r0c[3]][14:12], meta[gb][r0c[2]][11:8],
                            meta[gb][r0c[1]][7:4], meta[gb][r0c[0]][3:0]};
        assign rd1_b[gb] = {written[gb][r1c[3]], meta[gb][r1c[3]][14:12], meta[gb][r1c[2]][11:8],
                            meta[gb][r1c[1]][7:4], meta[gb][r1c[0]][3:0]};
    end endgenerate
    // P7 (10-15, P6 route TT -90.64: r0c/r1c -> per-bank 96:1 metadata read -> 4:1 bank select (i0/i1 bank bits) ->
    // m0/m1[0] enable flop in one edge). The per-bank read results are registered first (mb*_q, 2 x 4 x 16 FF) and the
    // 4:1 bank select moves into the next stage, which REPLACES the first stage of the m0/m1 alignment delay line
    // (m*[0] -> m*[1] was a pure delay): the metadata reaches m*[3] on the same edge as before, 0 added cycles.
    // m*[0]'s hold-when-idle enable is dropped: m* are consumed only under valid[3].
    reg [15:0] mb0_q [0:3], mb1_q [0:3];
    integer gq;
    always @(posedge clk) for (gq = 0; gq < 4; gq = gq + 1) begin mb0_q[gq] <= rd0_b[gq]; mb1_q[gq] <= rd1_b[gq]; end
    always @(posedge clk or negedge rst_l[0]) begin
      if(!rst_l[0]) begin
        sticky<=0;check0<=0;check1<=0;
        for(j=0;j<4;j=j+1) begin valid[j]<=0;selected0[j]<=0;selected1[j]<=0; end
      end else begin
        selected0[0]<=bank0; selected1[0]<=bank1;
        valid[0]<=gates & {2{consume_1}};
        // P9: the per-bank read is one edge later (r0c from i0), so the bank select lands in m*[2] with
        // selected*[1]; m*[1] is no longer a stage. m*[3] holds the same row on the same edge as P8.
        m0[2]<=mb0_q[selected0[1]]; m1[2]<=mb1_q[selected1[1]];
        for(j=1;j<4;j=j+1) begin
          selected0[j]<=selected0[j-1];selected1[j]<=selected1[j-1];
          valid[j]<=valid[j-1];
          if(j>2) begin m0[j]<=m0[j-1];m1[j]<=m1[j-1]; end
        end
        check0<=valid[3][0];check1<=valid[3][1];
        expected0<=m0[3][14:10];expected1<=m1[3][14:10];
        if((valid[3][0]&&!m0[3][15]) || (valid[3][1]&&!m1[3][15])) sticky<=1;
        if(check0 && expected0!={^he0,^hq0[255:192],^hq0[191:128],^hq0[127:64],^hq0[63:0]}) sticky<=1;
        if(check1 && expected1!={^he1,^hq1[255:192],^hq1[191:128],^hq1[127:64],^hq1[63:0]}) sticky<=1;
      end
    end
    assign fault=sticky;
    reg[1023:0]rd_data_q;
    always @(posedge clk)rd_data_q<=rd_data;
    wire[1023:0]selected_data;
`ifdef OT_S81_PQ_PINREAD_MUT_BYPASS
    assign selected_data=rd_data;
`else
    assign selected_data=rd_data_q;
`endif
    always @(posedge clk) begin
      hq0<=valid[3][0] ? selected_data[256*selected0[3]+:256] : 256'd0;
`ifdef OT_S81_PQ_QB_HEAD_MUT
      hq1<=valid[3][1] ? selected_data[256*selected0[3]+:256] : 256'd0;
`else
      hq1<=valid[3][1] ? selected_data[256*selected1[3]+:256] : 256'd0;
`endif
      he0<=valid[3][0] ? m0[3][9:0] : 10'd0;
      he1<=valid[3][1] ? m1[3][9:0] : 10'd0;
    end
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_l[0]) begin
      if(consume_1&&gates[0]&&i0>=384) $fatal(1,"QB q0 index beyond production storage");
      if(consume_1&&gates[1]&&i1>=384) $fatal(1,"QB q1 index beyond production storage");
      if(aqi[9]&&(aqi[8:1]>=192||aqi[1])) $fatal(1,"QB write pair outside legal loader protocol");
    end
`endif
endmodule

module ot_s81_pq_qb_pinread_native (
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
 ot_s81_pq_qb_headpc_native u_head (.clk(clk),.rst_n(rst_n),.consume(consume),.aqi_d(aqi_d),
 .h_b0(h_b0),.h_b1(h_b1),.hw_sv(hw_sv),.rd_data(rd),.aq_e(aq_e),.aq_p(parity),
 .wr0(wr0),.wr1(wr1),.wq0(wq0),.wq1(wq1),.i0(i0),.i1(i1),.rq0(rq0),.rq1(rq1),
 .hq0(hq0),.hq1(hq1),.he0(he0),.he1(he1),.fault(fault));
 generate for(genvar b=0;b<4;b=b+1) begin:g_bank
 ot_s81_pq_qb_bankp_native u_bank(.clk(clk_bank[b]),.rst_n(rst_n),.wr0(wr0),.wr1(wr1),
 .wq0(wq0[b]),.wq1(wq1[b]),.aq_q(aq_q),.i0(i0),.i1(i1),.rq0(rq0[b]),.rq1(rq1[b]),.rd(rd[256*b+:256]));
 end endgenerate
endmodule
