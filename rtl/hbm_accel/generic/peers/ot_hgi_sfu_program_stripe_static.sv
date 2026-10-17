`timescale 1ns/1ps
`default_nettype none
// Paged programme SRAM is written before launch; global PC identity crosses pages. A launch executes the fixed range
// [base,limit), repeated loops times. Nothing observes datapath arrival/ready.
// Each programme word: magic[255:240]=c7a1, global PC[233:234-AW], calendar[W-1:0];
// all reserved bits zero. The independent capture rung is the macro's only load.
module ot_hgi_sfu_program_stripe_static #(
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
    reg cfg_we_q,start_v_q;
    reg [AW-1:0] cfg_addr_q,start_base_q;
    reg [255:0] cfg_data_q;
    reg [AW:0] start_limit_q;
    reg [15:0] start_loops_q;
    always @(posedge clk)begin
        cfg_addr_q<=cfg_addr;cfg_data_q<=cfg_data;
        start_base_q<=start_base;start_limit_q<=start_limit;start_loops_q<=start_loops;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin cfg_we_q<=0;start_v_q<=0;end
        else begin cfg_we_q<=cfg_we;start_v_q<=start_v;end
    reg running;
    reg [AW-1:0] pc,base;
    reg [AW:0] limit;
    reg [15:0] loops_left;
    reg [31:0] issued;
    reg valid0,valid1,last0,last1;
    reg [AW-1:0] pc0,pc1;
    reg [31:0] ord0,ord1;
    reg [255:0] captured;
    wire [255:0] macro_data;
    wire busy=running|valid0|valid1;
    wire legal_start=start_limit_q>{1'b0,start_base_q} && start_limit_q<=(1<<AW) && start_loops_q!=0;
    wire final_issue=({1'b0,pc}+{{AW{1'b0}},1'b1}==limit) && loops_left==1;
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
    // Payload, ordinal and address identity have dedicated, nonreset rungs.
    always @(posedge clk)begin
        captured<=macro_data;
        pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;
        calendar<=valid1 && word_ok?captured[W-1:0]:{W{1'b0}};
        ordinal<=ord1;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            running<=0;pc<=0;base<=0;limit<=0;loops_left<=0;issued<=0;
            valid0<=0;valid1<=0;last0<=0;last1<=0;calendar_v<=0;
            active<=0;done<=0;fault<=0;
        end else begin
            valid0<=running;valid1<=valid0;last0<=running && final_issue;last1<=last0;
            calendar_v<=valid1;
            active<=busy;done<=valid1 && last1;
            if(valid1 && !word_ok)fault<=1;
            if(cfg_we_q && (busy || start_v_q))fault<=1;
            if(start_v_q)begin
                if(busy || cfg_we_q || !legal_start)fault<=1;
                else begin
                    running<=1;pc<=start_base_q;base<=start_base_q;limit<=start_limit_q;
                    loops_left<=start_loops_q;issued<=0;
                end
            end
            if(running)begin
                issued<=issued+1;
                if({1'b0,pc}+{{AW{1'b0}},1'b1}==limit)begin
                    if(loops_left==1)running<=0;
                    else begin
                        pc<=base + ((MUT==1)?{{(AW-1){1'b0}},1'b1}:{AW{1'b0}});
                        loops_left<=loops_left-1;
                        if(MUT==2)running<=0;
                    end
                end else pc<=pc+1;
            end
        end
endmodule
`default_nettype wire
