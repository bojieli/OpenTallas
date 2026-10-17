`timescale 1ns/1ps
`default_nettype none
// ot_hgi_sfu_program_stripe_pipe (H-SU r7b 2026-10-16): ot_hgi_sfu_program_stripe_sreset with the SRAM pipelined and the
// launch arithmetic precomputed. r6 route hbm_sfu_programme_store_r6_1016-r6-4faed2823 NEEDS_RTL TT -89 / FF -69:
// classes cfg_data_q -> SRAM wd_in (10-13 levels across the stripe), SRAM rd_out -> page mux -> captured, start_limit_q
// -> legal/issued/loops_left (14 levels), issued increment (17 levels).
// Changes (all fixed latency, no dynamic path):
//   WRITE: per-page registered write port (w_ce/w_addr/wd one register beside each macro): the macro write lands one
//          edge after the original (configuration only; gating decision taken at the same edge as before).
//   START: one launch stage (start_v_q2 + legal / span = limit-base / loops==1 precomputed into registers): +1 edge.
//   READ:  registered read address (ra_ce/ra_addr) and a registered Q per page (q_pg, no mux before the register),
//          page mux into `captured` after it: +2 edges. Identity/valid/last/ordinal chains lengthened to match.
//   PC wrap: remaining-count `rem` (== limit - pc) replaces the pc+1==limit compare; loops_one flag replaces loops==1.
// Net: every output (calendar, calendar_v, ordinal, active, done) is the original's delayed by exactly LAT_ADD = 3 edges.
// Synchronous reset (rst_n = this stripe's regional relay); data / launch-argument registers unreset.
module ot_hgi_sfu_program_stripe_pipe #(
    parameter integer PAGE_AW=1, AW=10+PAGE_AW, W=222,
    parameter integer MUT=0 // 1 wrong wrap PC, 2 extra cycle at loop boundary
)(
    input wire clk,rst_n,
    input wire cfg_we,
    input wire [AW-1:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [AW-1:0] start_base,
    input wire [AW:0] start_limit,
    input wire [15:0] start_loops,
    output reg [W-1:0] calendar,
    output reg calendar_v,
    output reg [31:0] ordinal,
    output reg active,done,fault
);
    localparam integer PCLO=234-AW, MAXW=PCLO-1, PAGES=1<<PAGE_AW;
    initial if(W<1 || W>MAXW || PAGE_AW<1 || PAGE_AW>2)$fatal(1,"SFU paged programme geometry invalid");
    // ---- pin-side input registers (as before)
    reg cfg_we_q,start_v_q;
    reg [AW-1:0] cfg_addr_q,start_base_q;
    reg [255:0] cfg_data_q;
    reg [AW:0] start_limit_q;
    reg [15:0] start_loops_q;
    always @(posedge clk)begin
        cfg_addr_q<=cfg_addr;cfg_data_q<=cfg_data;
        start_base_q<=start_base;start_limit_q<=start_limit;start_loops_q<=start_loops;
    end
    always @(posedge clk)
        if(!rst_n)begin cfg_we_q<=0;start_v_q<=0;end
        else begin cfg_we_q<=cfg_we;start_v_q<=start_v;end
    // ---- launch stage (+1): legality / span / loop flag precomputed
    reg start_v_q2,cfg_we_q2,legal_q2,loops_one_q2;
    reg [AW-1:0] base_q2;
    reg [AW:0] span_q2;
    reg [15:0] loops_q2;
    always @(posedge clk)begin
        legal_q2<=start_limit_q>{1'b0,start_base_q} && start_limit_q<=(1<<AW) && start_loops_q!=0;
        span_q2<=start_limit_q-{1'b0,start_base_q};
        base_q2<=start_base_q;loops_q2<=start_loops_q;loops_one_q2<=start_loops_q==16'd1;
    end
    always @(posedge clk)
        if(!rst_n)begin start_v_q2<=0;cfg_we_q2<=0;end
        else begin start_v_q2<=start_v_q;cfg_we_q2<=cfg_we_q;end
    reg running,loops_one;
    reg [AW-1:0] pc,base;
    reg [AW:0] rem,span;
    reg [15:0] loops_left;
    reg [31:0] issued;
    reg valid0,valid1,valid2,valid3,last0,last1,last2,last3;
    reg [AW-1:0] pc0,pc1,pc2,pc3;
    reg [31:0] ord0,ord1,ord2,ord3;
    reg [255:0] captured;
    wire busy=running|valid0|valid1|valid2|valid3;
    wire final_issue=(rem=={{AW{1'b0}},1'b1}) && loops_one;
    wire word_ok=captured[255:240]==16'hc7a1 && captured[233:PCLO]==pc3 &&
                 captured[239:234]==0 && captured[PCLO-1:W]==0;
    // ---- SRAM pages: registered write port, registered read address, registered Q
    wire [255:0] page_data[0:PAGES-1];
    reg [255:0] q_pg[0:PAGES-1];
    reg [PAGE_AW-1:0] rp0,rp1,rp2;
    always @(posedge clk)begin rp0<=pc[AW-1:10];rp1<=rp0;rp2<=rp1;end
    for(genvar p=0;p<PAGES;p=p+1)begin:g_page
     reg w_ce,r_ce; reg [9:0] w_addr,r_addr; reg [255:0] wd;
     always @(posedge clk)
        if(!rst_n)begin w_ce<=0;r_ce<=0;end
        else begin
            w_ce<=cfg_we_q && !busy && !start_v_q && !start_v_q2 && cfg_addr_q[AW-1:10]==p;
            r_ce<=running && pc[AW-1:10]==p;
        end
     always @(posedge clk)begin w_addr<=cfg_addr_q[9:0];wd<=cfg_data_q;r_addr<=pc[9:0];q_pg[p]<=page_data[p];end
     ot_sram_1r1w_1024x256_m2_r2c2 u_program(
        .clk(clk),.r_ce_in(r_ce),.r_addr_in(r_addr),.rd_out(page_data[p]),
        .w_ce_in(w_ce),.w_addr_in(w_addr),.wd_in(wd),.w_mask_in({256{1'b1}}),
        .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
    end
    // Payload, ordinal and address identity have dedicated, nonreset rungs.
    always @(posedge clk)begin
        captured<=q_pg[rp2];
        pc0<=pc;pc1<=pc0;pc2<=pc1;pc3<=pc2;ord0<=issued;ord1<=ord0;ord2<=ord1;ord3<=ord2;
        calendar<=valid3 && word_ok?captured[W-1:0]:{W{1'b0}};
        ordinal<=ord3;
    end
    always @(posedge clk)
        if(!rst_n)begin
            running<=0;issued<=0;
            valid0<=0;valid1<=0;valid2<=0;valid3<=0;last0<=0;last1<=0;last2<=0;last3<=0;calendar_v<=0;
            active<=0;done<=0;fault<=0;
        end else begin
            valid0<=running;valid1<=valid0;valid2<=valid1;valid3<=valid2;
            last0<=running && final_issue;last1<=last0;last2<=last1;last3<=last2;
            calendar_v<=valid3;
            active<=valid1|valid2|valid3;   // = the original's active delayed by exactly 3 edges
            done<=valid3 && last3;
            if(valid3 && !word_ok)fault<=1;
            if(cfg_we_q && (busy || start_v_q || start_v_q2))fault<=1;
            if(start_v_q2)begin
                if(busy || cfg_we_q2 || !legal_q2)fault<=1;
                else begin
                    running<=1;pc<=base_q2;base<=base_q2;rem<=span_q2;span<=span_q2;
                    loops_left<=loops_q2;loops_one<=loops_one_q2;issued<=0;
                end
            end
            if(running)begin
                issued<=issued+1;
                if(rem=={{AW{1'b0}},1'b1})begin
                    if(loops_one)running<=0;
                    else begin
                        pc<=base + ((MUT==1)?{{(AW-1){1'b0}},1'b1}:{AW{1'b0}});
                        rem<=span;loops_left<=loops_left-1;loops_one<=loops_left==16'd2;
                        if(MUT==2)running<=0;
                    end
                end else begin pc<=pc+1;rem<=rem-1; end
            end
        end
endmodule
`default_nettype wire
