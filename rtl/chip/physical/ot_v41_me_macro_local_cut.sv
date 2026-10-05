`timescale 1ns/1ps
// One MP1 g_pos[0].g_c[0] cell of the selected ME activation store.
// It retains the input, bank-local write and bank-read-capture edges.
module ot_v41_me_macro_local_cut (
    input wire clk,
    input wire pre_v,
    input wire [12:0] pre_e,
    input wire [127:0] pre_d,
    input wire rq_v,
    input wire [13:0] rq_q,
    input wire [1:0] rq_plg,
    output reg [127:0] q_local_r
);
    reg pre_v_r,rq_v_r;
    reg [12:0] pre_e_r;
    reg [127:0] pre_d_r;
    reg [13:0] rq_q_r;
    reg [1:0] rq_plg_r;
    wire hit = pre_v_r && pre_e_r < 13'd5120;
    wire [6:0] wa = 7'(pre_e_r >> 6);
    wire [6:0] ra = rq_plg_r==0 ? 7'(rq_q_r>>3) :
                    rq_plg_r==1 ? 7'(rq_q_r>>2) :
                    rq_plg_r==2 ? 7'(rq_q_r>>1) : 7'(rq_q_r);
    reg hit_q;
    reg [6:0] wa_q;
    reg [127:0] wd_q,wm_q;
    wire [255:0] macro_q;

    always @(posedge clk) begin
        pre_v_r<=pre_v; pre_e_r<=pre_e; pre_d_r<=pre_d;
        rq_v_r<=rq_v; rq_q_r<=rq_q; rq_plg_r<=rq_plg;
        hit_q<=hit; wa_q<=wa; wd_q<=pre_d_r; wm_q<={128{hit}};
        q_local_r<=macro_q[127:0];
    end

    ot_sram_1r1w_128x256_m1_r2c2 u_sram (
        .clk(clk),.r_ce_in(rq_v_r && ra < 7'd80),.r_addr_in(ra),
        .rd_out(macro_q),.w_ce_in(hit_q),.w_addr_in(wa_q),
        .wd_in({128'b0,wd_q}),.w_mask_in({128'b0,wm_q}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0)
    );
endmodule
