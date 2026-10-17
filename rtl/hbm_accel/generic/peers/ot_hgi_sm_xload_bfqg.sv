// BFQg: bank-local mask launch and a separate control-pin capture root.
// cl2h3 source531642618: shared mask_hi/lo -> SRAM w_mask_in worst -132.54ps;
// each mask flop drove1024 macro pins. Core boundary spread147.5ps.
// Preserve every data edge. Eight independently clocked local mask captures
// drive128 pins apiece. Literal per-bank input/clock pins belong beside that
// bank's outer mask face. The caller supplies identical mask copies at the
// same compiled edge; there is no arbitration or production backpressure.
module ot_hgi_sm_xload_cl2_bfqg (
    input wire clk, clk_n, clk_s, clk_ctrl,
    input wire clk_m0, clk_m1, clk_m2, clk_m3, clk_m4, clk_m5, clk_m6, clk_m7,
    input wire clk_l0, clk_l1, clk_l2, clk_l3, clk_l4, clk_l5, clk_l6, clk_l7,
    input wire rst_n,
    input wire [1023:0] c_d,
    input wire wce,
    input wire mhi0,mhi1,mhi2,mhi3,mhi4,mhi5,mhi6,mhi7,
    input wire mlo0,mlo1,mlo2,mlo3,mlo4,mlo5,mlo6,mlo7,
    input wire [6:0] wa,
    input wire [7:0] r_ce,
    input wire [6:0] r_a,
    output reg [255:0] rwq
);
    wire [7:0] mhi={mhi7,mhi6,mhi5,mhi4,mhi3,mhi2,mhi1,mhi0};
    wire [7:0] mlo={mlo7,mlo6,mlo5,mlo4,mlo3,mlo2,mlo1,mlo0};
    wire [7:0] cm = {clk_m7,clk_m6,clk_m5,clk_m4,clk_m3,clk_m2,clk_m1,clk_m0};
    wire [7:0] cl = {clk_l7,clk_l6,clk_l5,clk_l4,clk_l3,clk_l2,clk_l1,clk_l0};
    wire [0:0] rn_l;
    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst
        (.clk(clk_ctrl),.rst_n_in(rst_n),.rst_n(rn_l));
    (* keep = 1 *) reg [1023:0] cdq;
    (* keep = 1 *) reg [6:0] wa_q,ra_q;
    (* keep = 1 *) reg wce_q;
    always @(posedge clk_n) cdq <= c_d;
    always @(posedge clk_ctrl) begin
        wa_q <= wa; ra_q <= r_a;
        if (!rn_l[0]) wce_q <= 1'b0; else wce_q <= wce;
    end
    wire [255:0] cap [0:7];
    for (genvar gt=0;gt<8;gt=gt+1) begin:g_t
        (* keep = 1 *) reg mask_hi,mask_lo,rp_ce;
        reg rp_sel;
        reg [255:0] cq;
        wire [255:0] rd;
        always @(posedge cl[gt]) begin mask_hi <= mhi[gt]; mask_lo <= mlo[gt]; end
        always @(posedge clk_ctrl) begin
            if (!rn_l[0]) rp_ce <= 1'b0; else rp_ce <= r_ce[gt];
        end
        always @(posedge clk) begin
            if (!rn_l[0]) rp_sel <= 1'b0; else rp_sel <= rp_ce;
            cq <= rd & {256{rp_sel}};
        end
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(cm[gt]),
            .r_ce_in(rp_ce),.r_addr_in(ra_q),.rd_out(rd),
            .w_ce_in(wce_q),.w_addr_in(wa_q),
            .wd_in({cdq[gt*128+:128],cdq[gt*128+:128]}),
            .w_mask_in({{128{mask_hi}},{128{mask_lo}}}),
            .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
        assign cap[gt]=cq;
    end
    reg [255:0] or4a,or4b;
    always @(posedge clk) begin
        or4a <= cap[0]|cap[1]|cap[2]|cap[3];
        or4b <= cap[4]|cap[5]|cap[6]|cap[7];
    end
    always @(posedge clk_s) rwq <= or4a|or4b;
endmodule
