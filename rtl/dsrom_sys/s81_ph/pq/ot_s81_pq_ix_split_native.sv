`timescale 1ns/1ps
// Physical IX partition. Each old logical edge remains an edge; 8 SRAMs stay.
module ot_s81_pq_ix_ba_native (
    input wire clk, rst_n,
    input wire [1023:0] xw,
    input wire [7:0] bank_fault,
    output reg [511:0] ba_hi,
    output reg [31:0] ba_inc,
    output reg fault
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr
        (.clk(clk),.rst_n_in(rst_n),.rst_n(rst_l));
    integer k;
    always @(posedge clk) for(k=0;k<32;k=k+1) begin
        ba_hi[16*k +: 16] <= xw[32*k+16 +: 16];
        ba_inc[k] <= xw[32*k+15] & ((xw[32*k +: 15] != 15'd0) | xw[32*k+16]);
    end
    always @(posedge clk or negedge rst_l[0])
        if(!rst_l[0]) fault <= 0; else fault <= |bank_fault;
endmodule

module ot_s81_pq_ix_rg_native (
    input wire clk, rst_n, consume,
    input wire ba_wv,                // stage A write enable of THIS tile's block parity (registered in the controller)
    input wire [7:0] ba_blk,
    input wire [511:0] ba_hi,
    input wire [31:0] ba_inc,
    input wire [8:0] h_hi,
    input wire [2:0] hw_low,
    input wire hw_gate,
    output wire [63:0] bt_d,
    output wire [1:0] bank_fault
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr
        (.clk(clk),.rst_n_in(rst_n),.rst_n(rst_l));
    wire [511:0] bw_rn;
    reg [511:0] bw_d;
    genvar k;
    generate for(k=0;k<32;k=k+1) begin:g_round
        ot_v41_inc #(.W(16)) u_rn (.a(ba_hi[16*k +: 16]),.inc(ba_inc[k]),.y(bw_rn[16*k +: 16]),.co());
    end endgenerate
    always @(posedge clk) bw_d <= bw_rn;
    reg [7:0] write_blk;
    reg write_valid, consume_1, consume_2;
    always @(posedge clk or negedge rst_l[0]) begin
        if(!rst_l[0]) begin write_blk<=0;write_valid<=0;consume_1<=0;consume_2<=0;end
        else begin write_blk<=ba_blk;write_valid<=ba_wv;consume_1<=consume;consume_2<=consume_1;end
    end
    wire we=write_valid;             // the parity compare is done in the controller (ba_wv): no per-instance constant input
    wire [6:0] wa=write_blk[7:1];
    genvar gp,gl;
    generate for(gp=0;gp<2;gp=gp+1) begin:g_bank
        wire [12:0] p1;
        ot_v41_kreg #(.W(13),.AR(1)) u_p1
            (.clk(clk),.arst_n(rst_l[0]),.d({h_hi,hw_low,hw_gate}),.q(p1));
        wire [8:0] row=p1[12:4];
`ifdef OT_S81_PQ_IX_MUT_ROW
        wire [6:0] ra=7'd0;
`else
        wire [6:0] ra=row[6:0];
`endif
        wire re=p1[0]&&consume_1;
        wire [255:0] rd;
        wire [255:0] wd=bw_d[256*gp +: 256];
        ot_sram_1r1w_128x256_m1_r2c2 u_mem
            (.clk(clk),.r_ce_in(re),.r_addr_in(ra),.rd_out(rd),
             .w_ce_in(we),.w_addr_in(wa),.wd_in(wd),.w_mask_in({256{1'b1}}),
             .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
        reg [3:0] parity[0:95];
        reg [95:0] written;
        reg [3:0] expected;
        reg checked,sticky;
        wire [3:0] wp={^wd[255:192],^wd[191:128],^wd[127:64],^wd[63:0]};
        wire [3:0] rp={^rd[255:192],^rd[191:128],^rd[127:64],^rd[63:0]};
        always @(posedge clk or negedge rst_l[0]) begin
            if(!rst_l[0]) begin written<=0;checked<=0;sticky<=0;end
            else begin
                if(we&&wa<96) begin parity[wa]<=wp;written[wa]<=1'b1;end
                checked<=re&&row<96&&written[ra];
                if(re&&row<96) expected<=parity[ra];
                if(checked&&expected!=rp) sticky<=1;
                if(re&&(row>=96||!written[ra])) sticky<=1;
            end
        end
        assign bank_fault[gp]=sticky;
`ifdef OT_PQ_BENCH_TELEMETRY
        reg [95:0] rows_read;
        always @(posedge clk or negedge rst_l[0])
            if(!rst_l[0]) rows_read<=0;else if(re&&ra<96) rows_read[ra]<=1;
`endif
`ifndef SYNTHESIS
        always @(posedge clk) if(rst_l[0]) begin
            if(we&&wa>=96) $fatal(1,"IX write beyond production storage");
            if(re&&(row>=96||!written[ra])) $fatal(1,"IX read before loaded");
            if(we&&re&&wa==ra) $fatal(1,"IX read during write violates have protocol");
        end
`endif
        for(gl=0;gl<2;gl=gl+1) begin:g_lane
            wire [3:0] p2;
            ot_v41_kreg #(.W(4),.AR(1)) u_p2
                (.clk(clk),.arst_n(rst_l[0]),.d(p1[3:0]),.q(p2));
            reg [15:0] selected;
            always @(posedge clk)
                selected<=p2[0]&&consume_2 ? rd[128*gl+16*p2[3:1] +: 16] : 16'd0;
            assign bt_d[32*gp+16*gl +: 16]=selected;
        end
    end endgenerate
endmodule

// One original bank owns its SRAM, row/parity state, metadata, selector and final capture.
module ot_s81_pq_ix_rb_native (
    input wire clk, rst_n, consume,
    input wire ba_wv,                // stage A write enable of THIS tile's block parity (registered in the controller)
    input wire [7:0] ba_blk,
    input wire [255:0] ba_hi,
    input wire [15:0] ba_inc,
    input wire [8:0] h_hi,
    input wire [2:0] hw_low,
    input wire hw_gate,
    output wire [31:0] bt_d,
    output wire [0:0] bank_fault
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr
        (.clk(clk),.rst_n_in(rst_n),.rst_n(rst_l));
    wire [255:0] bw_rn;
    reg [255:0] bw_d;
    genvar k;
    generate for(k=0;k<16;k=k+1) begin:g_round
        ot_v41_inc #(.W(16)) u_rn (.a(ba_hi[16*k +: 16]),.inc(ba_inc[k]),.y(bw_rn[16*k +: 16]),.co());
    end endgenerate
    always @(posedge clk) bw_d <= bw_rn;
    reg [7:0] write_blk;
    reg write_valid, consume_1, consume_2;
    always @(posedge clk or negedge rst_l[0]) begin
        if(!rst_l[0]) begin write_blk<=0;write_valid<=0;consume_1<=0;consume_2<=0;end
        else begin write_blk<=ba_blk;write_valid<=ba_wv;consume_1<=consume;consume_2<=consume_1;end
    end
    wire we=write_valid;             // the parity compare is done in the controller (ba_wv): no per-instance constant input
    wire [6:0] wa=write_blk[7:1];
    genvar gp,gl;
    generate for(gp=0;gp<1;gp=gp+1) begin:g_bank
        wire [12:0] p1;
        ot_v41_kreg #(.W(13),.AR(1)) u_p1
            (.clk(clk),.arst_n(rst_l[0]),.d({h_hi,hw_low,hw_gate}),.q(p1));
        wire [8:0] row=p1[12:4];
`ifdef OT_S81_PQ_IX_MUT_ROW
        wire [6:0] ra=7'd0;
`else
        wire [6:0] ra=row[6:0];
`endif
        wire re=p1[0]&&consume_1;
        wire [255:0] rd;
        wire [255:0] wd=bw_d[256*gp +: 256];
        ot_sram_1r1w_128x256_m1_r2c2 u_mem
            (.clk(clk),.r_ce_in(re),.r_addr_in(ra),.rd_out(rd),
             .w_ce_in(we),.w_addr_in(wa),.wd_in(wd),.w_mask_in({256{1'b1}}),
             .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
        reg [3:0] parity[0:95];
        reg [95:0] written;
        reg [3:0] expected;
        reg checked,sticky;
        wire [3:0] wp={^wd[255:192],^wd[191:128],^wd[127:64],^wd[63:0]};
        wire [3:0] rp={^rd[255:192],^rd[191:128],^rd[127:64],^rd[63:0]};
        always @(posedge clk or negedge rst_l[0]) begin
            if(!rst_l[0]) begin written<=0;checked<=0;sticky<=0;end
            else begin
                if(we&&wa<96) begin parity[wa]<=wp;written[wa]<=1'b1;end
                checked<=re&&row<96&&written[ra];
                if(re&&row<96) expected<=parity[ra];
                if(checked&&expected!=rp) sticky<=1;
                if(re&&(row>=96||!written[ra])) sticky<=1;
            end
        end
        assign bank_fault[gp]=sticky;
`ifdef OT_PQ_BENCH_TELEMETRY
        reg [95:0] rows_read;
        always @(posedge clk or negedge rst_l[0])
            if(!rst_l[0]) rows_read<=0;else if(re&&ra<96) rows_read[ra]<=1;
`endif
`ifndef SYNTHESIS
        always @(posedge clk) if(rst_l[0]) begin
            if(we&&wa>=96) $fatal(1,"IX write beyond production storage");
            if(re&&(row>=96||!written[ra])) $fatal(1,"IX read before loaded");
            if(we&&re&&wa==ra) $fatal(1,"IX read during write violates have protocol");
        end
`endif
        for(gl=0;gl<2;gl=gl+1) begin:g_lane
            wire [3:0] p2;
            ot_v41_kreg #(.W(4),.AR(1)) u_p2
                (.clk(clk),.arst_n(rst_l[0]),.d(p1[3:0]),.q(p2));
            reg [15:0] selected;
            always @(posedge clk)
                selected<=p2[0]&&consume_2 ? rd[128*gl+16*p2[3:1] +: 16] : 16'd0;
            assign bt_d[32*gp+16*gl +: 16]=selected;
        end
    end endgenerate
endmodule

module ot_s81_pq_ix_split_native (
    input wire clk, rst_n, consume,
`ifdef OT_PQ_IX_BANK_SPLIT
    input wire [7:0] clk_read,
`else
    input wire [3:0] clk_read,
`endif
    input wire [1023:0] xw,
    input wire ba_wv,
    input wire [7:0] ba_blk,
    input wire [35:0] h_hi,
    input wire [6:0] hw7,
    output wire fault,
    output wire [255:0] bt_d
);
    wire [511:0] ba_hi;
    wire [31:0] ba_inc;
    wire [7:0] bank_fault;
    ot_s81_pq_ix_ba_native u_ba
        (.clk(clk),.rst_n(rst_n),.xw(xw),.bank_fault(bank_fault),.ba_hi(ba_hi),.ba_inc(ba_inc),.fault(fault));
    genvar gu;
    generate for(gu=0;gu<4;gu=gu+1) begin:g_rg
`ifdef OT_PQ_IX_BANK_SPLIT
        for(genvar gb=0;gb<2;gb=gb+1) begin:g_bankpart
            ot_s81_pq_ix_rb_native u_rb
                (.clk(clk_read[2*gu+gb]),.rst_n(rst_n),.consume(consume),.ba_wv(ba_wv),.ba_blk(ba_blk),
                 .ba_hi(ba_hi[256*gb +: 256]),.ba_inc(ba_inc[16*gb +: 16]),
                 .h_hi(h_hi[9*gu +: 9]),.hw_low(hw7[2:0]),.hw_gate(hw7[3+gu]),
                 .bt_d(bt_d[64*gu+32*gb +: 32]),.bank_fault(bank_fault[2*gu+gb +: 1]));
        end
`else
        ot_s81_pq_ix_rg_native u_rg
            (.clk(clk_read[gu]),.rst_n(rst_n),.consume(consume),.ba_wv(ba_wv),.ba_blk(ba_blk),
             .ba_hi(ba_hi),.ba_inc(ba_inc),.h_hi(h_hi[9*gu +: 9]),.hw_low(hw7[2:0]),.hw_gate(hw7[3+gu]),
             .bt_d(bt_d[64*gu +: 64]),.bank_fault(bank_fault[2*gu +: 2]));
`endif
    end endgenerate
endmodule
