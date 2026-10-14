`timescale 1ns/1ps
// Production KMAX6144 FP8 operand buffer: four real SRAM banks.
// Bank={logical_index[3],logical_index[0]}, row={index[8:4],index[2:1]}.
// A legal two-word write differs in bit0; concurrent q reads differ in bit3.
// Macro output is the original bt_q register, so no cycle is added.
module ot_s81_pq_qb_sram (
    input wire clk, rst_n, consume,
    input wire [9:0] aqi_d,
    input wire [511:0] aq_q,
    input wire [19:0] aq_e,
`ifdef OT_PQ_AQ_SIDE_PARITY
    input wire [9:0] aq_p,
`endif
    input wire [15:0] h_b0, h_b1,
    input wire [1:0] hw_sv,
    output reg [255:0] hq0, hq1,
    output reg [9:0] he0, he1,
    output wire fault
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr
        (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    reg [9:0] aqi;
    reg [8:0] w0, w1;
    reg wv;
    always @(posedge clk or negedge rst_l[0]) begin
        if (!rst_l[0]) begin aqi <= 0; w0 <= 0; w1 <= 0; wv <= 0; end
        else begin
            aqi <= aqi_d;
            w0 <= (aqi[0] ? 9'd192 : 9'd0) + {1'b0, aqi[8:1]};
            w1 <= (aqi[0] ? 9'd192 : 9'd0) + {1'b0, aqi[8:1]} + 9'd1;
            wv <= aqi[9];
        end
    end
    reg [15:0] i0, i1;
    reg [1:0] gates;
    reg consume_1;
    always @(posedge clk or negedge rst_l[0])
        if (!rst_l[0]) begin i0 <= 0; i1 <= 0; gates <= 0; consume_1 <= 0; end
        else begin i0 <= h_b0; i1 <= h_b1; gates <= hw_sv; consume_1 <= consume; end
    wire [1:0] bank0 = {i0[3], i0[0]}, bank1 = {i1[3], i1[0]};
    wire [6:0] row0 = {i0[8:4], i0[2:1]}, row1 = {i1[8:4], i1[2:1]};
    wire [255:0] rd [0:3];
    reg [9:0] erd [0:3];
    wire [3:0] bfault;
    reg [1:0] selected0, selected1, g2;
    reg fault_pin;
    always @(posedge clk or negedge rst_l[0]) begin
        if (!rst_l[0]) begin selected0 <= 0; selected1 <= 0; g2 <= 0; fault_pin <= 0; end
        else begin selected0 <= bank0; selected1 <= bank1; g2 <= gates & {2{consume_1}}; fault_pin <= |bfault; end
    end
    assign fault = fault_pin;
    always @(posedge clk) begin
        hq0 <= g2[0] ? rd[selected0] : 256'd0;
`ifdef OT_S81_PQ_QB_MUT_ROW
        // Wrong logical read index: q1 consumes q0's bank as well as its row.
        hq1 <= g2[1] ? rd[selected0] : 256'd0;
`else
        hq1 <= g2[1] ? rd[selected1] : 256'd0;
`endif
        he0 <= g2[0] ? erd[selected0] : 10'd0;
        he1 <= g2[1] ? erd[selected1] : 10'd0;
    end
    genvar b;
    generate for (b = 0; b < 4; b = b + 1) begin : g_bank
        wire a = wv && {w0[3],w0[0]} == 2'(b);
        wire z = wv && {w1[3],w1[0]} == 2'(b);
        wire we = a || z;
        wire [8:0] wi = a ? w0 : w1;
        wire [6:0] wa = {wi[8:4],wi[2:1]};
        wire [255:0] wd = a ? aq_q[255:0] : aq_q[511:256];
        wire [9:0] ew = a ? aq_e[9:0] : aq_e[19:10];
        wire r0 = consume_1 && gates[0] && bank0 == 2'(b);
        wire r1 = consume_1 && gates[1] && bank1 == 2'(b);
        wire re = r0 || r1;
`ifdef OT_S81_PQ_QB_MUT_ROW
        wire [6:0] ra = row0;
`else
        wire [6:0] ra = r0 ? row0 : row1;
`endif
`ifdef OT_PQ_BENCH_TELEMETRY
        reg [95:0] rows_read;
        always @(posedge clk or negedge rst_l[0])
            if (!rst_l[0]) rows_read <= 0;
            else if (re && ra < 96) rows_read[ra] <= 1'b1;
`endif
        ot_sram_1r1w_128x256_m1_r2c2 u_mem (
            .clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(rd[b]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        reg [9:0] exponent [0:95];
        reg [4:0] parity [0:95];
        reg [95:0] written;
        reg [4:0] expected;
        reg checked, sticky;
`ifdef OT_PQ_AQ_SIDE_PARITY
        wire [4:0] wp = a ? aq_p[4:0] : aq_p[9:5];
`else
        wire [4:0] wp = {^ew, ^wd[255:192], ^wd[191:128], ^wd[127:64], ^wd[63:0]};
`endif
        wire [4:0] rp = {^erd[b], ^rd[b][255:192], ^rd[b][191:128], ^rd[b][127:64], ^rd[b][63:0]};
        always @(posedge clk or negedge rst_l[0]) begin
            if (!rst_l[0]) begin written <= 0; checked <= 0; sticky <= 0; end
            else begin
                if (we && wa < 96) begin exponent[wa] <= ew; parity[wa] <= wp; written[wa] <= 1'b1; end
                if (re && ra < 96) begin erd[b] <= exponent[ra]; expected <= parity[ra]; end
                checked <= re && ra < 96 && written[ra];
                if (checked && expected != rp) sticky <= 1'b1;
                if (re && (ra >= 96 || !written[ra])) sticky <= 1'b1;
            end
        end
        assign bfault[b] = sticky;
`ifndef SYNTHESIS
        always @(posedge clk) if (rst_l[0]) begin
            if (we && wa >= 96) $fatal(1, "QB write beyond production storage");
            if (a && z) $fatal(1, "QB writes collide in one bank");
            if (r0 && r1) $fatal(1, "QB reads collide in one bank");
            if (re && (ra >= 96 || !written[ra])) $fatal(1, "QB read before loaded");
            if (we && re && wa == ra) $fatal(1, "QB read during write violates have protocol");
        end
`endif
    end endgenerate
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_l[0]) begin
        if (consume_1 && gates[0] && i0 >= 384) $fatal(1, "QB q0 index beyond production storage");
        if (consume_1 && gates[1] && i1 >= 384) $fatal(1, "QB q1 index beyond production storage");
        if (aqi[9] && (aqi[8:1] >= 192 || aqi[1])) $fatal(1, "QB write pair outside legal loader protocol");
    end
`endif
endmodule
