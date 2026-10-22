`timescale 1ns/1ps
module vehicle(input clk,rst_n,input wv,input[9:0]wa,input[255:0]wd,input tj_set,tj_w,input launch,input cw_v,input[9:0]cw_a,output[767:0]bases,output[95:0]scales,output tbl_f,output reg fault);
`ifdef FIXED
localparam TABLE_LIFETIME_SAFE=1;
`else
localparam TABLE_LIFETIME_SAFE=0;
`endif
localparam NSET=2; wire[15:0]rr={16{rst_n}}; wire[2:0]ln_c={3{launch}}; genvar g;
        // job select ranks: 8 kept rank-1 copies, then 25 kept rank-2 copies: 12 bank read addresses, 12 scale bytes
        // (8-bit 4:1 each), 1 for the lifetime check.  Each copy drives <= ~20 loads.
        for (g = 0; g < 8; g = g + 1) begin : g_tj1
            (* keep = "true" *) reg s, w;
            always @(posedge clk) begin s <= tj_set; w <= tj_w; end
        end
        wire [24:0] ss, sw;
        for (g = 0; g < 25; g = g + 1) begin : g_tj2
            (* keep = "true" *) reg s, w;
            always @(posedge clk) begin s <= g_tj1[g % 8].s; w <= g_tj1[g % 8].w; end
            assign ss[g] = s; assign sw[g] = w;
        end
        // base table: 12 banks.  Config row o = wa[5:0] - 56 (0..5): which = o >= 3, bank group o % 3 (banks 4 (o % 3)
        // .. + 3, bank 4 (o % 3) + k <- wd[64 k +: 64]), set = wa[8]; physical row {set, which}.
        wire [5:0] wo = wa[5:0] - 6'd56;
        wire wbase = wv && !wa[9] && wa[5:0] >= 6'd56 && wa[5:0] < 6'd62;
        wire [1:0] wrow = {wa[8], wo >= 6'd3};
        for (g = 0; g < 12; g = g + 1) begin : g_bank
            wire wce = wbase && (wo == 6'(g / 4) || wo == 6'(g / 4 + 3));
            wire [63:0] rd;
            ot_sram_1r1w2c_32x64_m1 u_m (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in({3'b000, ss[g], sw[g]}),
                .rd_out(rd), .w_ce_in(wce), .w_addr_in({3'b000, wrow}), .wd_in(wd[64 * (g % 4) +: 64]),
                .w_mask_in({64{1'b1}}));
            always @(*) bases[64 * g +: 64] = rd;          // the macro's read register IS the bases capture
        end
        // scales: 4 x 96 flops; 16 kept write enables (24 bits each) predicted from the cw pins (= wv && !wa[9] &&
        // wa[5:0] == 62 && wa[8] == set, one edge early, same reset region as wv's peers).
        reg [95:0] scl_t [0:NSET*2-1];
        wire scw_d0 = cw_v && !cw_a[9] && cw_a[5:0] == 6'd62 && !cw_a[8];
        wire scw_d1 = cw_v && !cw_a[9] && cw_a[5:0] == 6'd62 &&  cw_a[8];
        for (g = 0; g < 32; g = g + 1) begin : g_scw
            wire we;
            (* keep = 1 *) dsdv_gunit_control_first u_q (.clk(clk), .rst_n((g % 2) ? rr[13] : rr[2]), .d((g / 16) ? scw_d1 : scw_d0), .q(we));
            // copy g: scale word (g / 8) = 2 set + half, bits 12 (g % 8) +: 12; half h <- wd[96 h +: 96]
            always @(posedge clk) if (we) scl_t[g / 8][12 * (g % 8) +: 12] <= wd[96 * ((g / 8) % 2) + 12 * (g % 8) +: 12];
        end
        for (g = 0; g < 12; g = g + 1) begin : g_sc
            always @(posedge clk) scales[8 * g +: 8] <= scl_t[2 * ss[12 + g] + sw[12 + g]][8 * g +: 8];
        end
        // lifetime check: a base write to the currently selected word arms a 4-edge window; the tail taking the bases
        // (ln) inside it is a sticky fault.
        if (TABLE_LIFETIME_SAFE) begin : g_lifetime_safe
            // Four independent logical-row histories: writes remain visible across selector changes.
            // +9 FF, same capture age; reject a simultaneous selected write without relying on SRAM collision order.
            reg [2:0] recent [0:3];
            for (genvar lr = 0; lr < 4; lr = lr + 1) begin : g_row
                always @(posedge clk or negedge rr[3])
                    if (!rr[3]) recent[lr] <= 3'd0;
                    else if (wbase && wrow == 2'(lr)) recent[lr] <= 3'd4;
                    else if (recent[lr] != 3'd0) recent[lr] <= recent[lr] - 3'd1;
            end
            assign tbl_f = ln_c[0] && ((recent[{ss[24], sw[24]}] != 3'd0) ||
                (wbase && wrow == {ss[24], sw[24]}));
        end else begin : g_lifetime_legacy
        reg [2:0] hit;
        always @(posedge clk or negedge rr[3])
            if (!rr[3]) hit <= 3'd0;
            else if (wbase && wrow == {ss[24], sw[24]}) hit <= 3'd4;
            else if (hit != 3'd0) hit <= hit - 3'd1;
        assign tbl_f = ln_c[0] && hit != 3'd0;
        end
always @(posedge clk or negedge rst_n) if(!rst_n) fault<=0; else if(tbl_f) fault<=1;
endmodule
module dsdv_gunit_control_first(input clk,rst_n,d,output reg q); always @(posedge clk or negedge rst_n) if(!rst_n)q<=0;else q<=d; endmodule
