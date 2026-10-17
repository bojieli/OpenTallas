`timescale 1ns/1ps
`default_nettype none
// ot_hgi_sfu_program_stripe_rc (H-SU r7c 2026-10-16): ot_hgi_sfu_program_stripe_sreset with the SRAM write port fed by
// REGISTERED, NON-MERGED copies and the launch arithmetic precomputed; NO added cycle.
// Root cause of r6 TT -89.42 (reg->macro wd_in, 1586 ps arrival through 11 placement buffers): every stripe's
// cfg_data_q / cfg_addr_q was logically identical, so synthesis merged them into ONE register that fanned out to all
// 16 programme macros (and one for the 6 IO macros) across the 1 mm tile. r7c: the calendar holds one (* keep *)
// registered copy per stripe pair (beside the pair's macro rows) and the stripe uses it directly as its *_q stage
// (same edge as before). The start legality / span = limit - base / loops==1 are computed in front of the existing
// launch registers (r6 TT -41.6 class start_limit_q -> issued/loops_left), and rem/loops_one replace the
// pc+1==limit / loops==1 compares. SRAM address in (pc register) and Q out (captured) stay registered.
// Synchronous reset (this stripe's regional relay); data / launch-argument registers unreset. Outputs and cycles are
// identical to ot_hgi_sfu_program_stripe_static.
module ot_hgi_sfu_program_stripe_rc #(
    parameter integer PAGE_AW=1, AW=10+PAGE_AW, W=222,
    parameter integer MUT=0 // 1 wrong wrap PC, 2 extra cycle at loop boundary
)(
    input wire clk,rst_n,
    input wire cfg_we_q,                 // registered by the calendar (this stripe selected), reset by this stripe's relay
    input wire [AW-1:0] cfg_addr_q,      // registered pair copy
    input wire [255:0] cfg_data_q,       // registered pair copy (* keep *)
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
    reg start_v_q,legal_q,loops_one_q;
    reg [AW-1:0] start_base_q;
    reg [AW:0] span_q;
    reg [15:0] start_loops_q;
    always @(posedge clk)begin
        start_base_q<=start_base;start_loops_q<=start_loops;
        legal_q<=start_limit>{1'b0,start_base} && start_limit<=(1<<AW) && start_loops!=0;
        span_q<=start_limit-{1'b0,start_base};
        loops_one_q<=start_loops==16'd1;
    end
    always @(posedge clk)
        if(!rst_n)start_v_q<=0;
        else start_v_q<=start_v;
    reg running,loops_one;
    reg [AW-1:0] pc,base;
    reg [AW:0] rem,span;
    reg [15:0] loops_left;
    reg [31:0] issued;
    reg valid0,valid1,last0,last1;
    reg [AW-1:0] pc0,pc1;
    reg [31:0] ord0,ord1;
    reg [255:0] captured;
    wire [255:0] macro_data;
    wire busy=running|valid0|valid1;
    wire final_issue=(rem=={{AW{1'b0}},1'b1}) && loops_one;
    wire word_ok=captured[255:240]==16'hc7a1 && captured[233:PCLO]==pc1 &&
                 captured[239:234]==0 && captured[PCLO-1:W]==0;
    wire [255:0] page_data[0:PAGES-1];
    reg [PAGE_AW-1:0] read_page;
    always @(posedge clk)read_page<=pc[AW-1:10];
    assign macro_data=page_data[read_page];
    for(genvar p=0;p<PAGES;p=p+1)begin:g_page
     ot_sram_1r1w_1024x256_m2_r2c2 u_program(
        .clk(clk),.r_ce_in(running && pc[AW-1:10]==p),.r_addr_in(pc[9:0]),.rd_out(page_data[p]),
        .w_ce_in(cfg_we_q && !busy && !start_v_q && cfg_addr_q[AW-1:10]==p),.w_addr_in(cfg_addr_q[9:0]),
        .wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
        .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
    end
    always @(posedge clk)begin
        captured<=macro_data;
        pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;
        calendar<=valid1 && word_ok?captured[W-1:0]:{W{1'b0}};
        ordinal<=ord1;
    end
    always @(posedge clk)
        if(!rst_n)begin
            running<=0;issued<=0;
            valid0<=0;valid1<=0;last0<=0;last1<=0;calendar_v<=0;
            active<=0;done<=0;fault<=0;
        end else begin
            valid0<=running;valid1<=valid0;last0<=running && final_issue;last1<=last0;
            calendar_v<=valid1;
            active<=busy;done<=valid1 && last1;
            if(valid1 && !word_ok)fault<=1;
            if(cfg_we_q && (busy || start_v_q))fault<=1;
            if(start_v_q)begin
                if(busy || cfg_we_q || !legal_q)fault<=1;
                else begin
                    running<=1;pc<=start_base_q;base<=start_base_q;rem<=span_q;span<=span_q;
                    loops_left<=start_loops_q;loops_one<=loops_one_q;issued<=0;
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
