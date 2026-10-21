`timescale 1ns/1ps
`default_nettype none
// HBM-SVGREL8 2026-10-20: HARDENED copy of ot_smh_calendar_static_x (that module stays byte-identical), same ports and
// the same output on every edge.  Changes (native census of the r11 svg mapped netlist: pc0[10] bank select 513 loads,
// valid1 && word_ok gating 135..170 loads):
//   * reset only on control / valid state (rst_n[1:0] = ot_rst_relay leaves); pc / base / limit / loops / issued /
//     context / iteration are datapath (always (re)loaded by an accepted start before they are observed);
//   * the 2-macro read mux uses KEPT copies of the registered bank select (one per 32 b);
//   * word_ok is evaluated on the macro output one edge earlier (wok = f(macro_data, pc0), registered exactly where
//     captured / pc1 are) and gates calendar / ctx / iter through KEPT per-slice copies of wok and valid1.
module ot_smh_calendar_static_xh #(
    parameter integer W=135,
    parameter integer AW=11,
    parameter integer XW=1,
    parameter integer MUT=0 // 1 wrong wrap PC, 2 extra cycle at loop boundary, 3 context not captured (stale)
)(
    input wire clk,input wire[1:0]rst_n,
    input wire cfg_we,
    input wire [AW-1:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [AW-1:0] start_base,
    input wire [AW:0] start_limit,
    input wire [15:0] start_loops,
    input wire [XW-1:0] start_ctx,
    output reg [W-1:0] calendar,
    output reg [XW-1:0] calendar_ctx,
    output reg [15:0] calendar_iter,
    output reg calendar_lastit,
    output reg calendar_v,
    output reg [31:0] ordinal,
    output reg active,done,fault
);
`ifdef SVGH_MUT
 localparam integer HM=`SVGH_MUT;     // HBM-SVGREL8 bench negative controls (see the kit README)
`else
 localparam integer HM=0;
`endif
    initial begin
        if(W<1 || W>223)$fatal(1,"SM calendar width must fit protected programme payload");
        if(AW!=10 && AW!=11)$fatal(1,"programme store: 1,024 or 2,048 words");
    end
    localparam integer NCS=(W+31)/32, NXS=(XW+31)/32, NVK=NCS+NXS+1;
    reg cfg_we_q,start_v_q;
    reg [AW-1:0] cfg_addr_q,start_base_q;
    reg [255:0] cfg_data_q;
    reg [AW:0] start_limit_q;
    reg [15:0] start_loops_q;
    reg [XW-1:0] start_ctx_q;
    always @(posedge clk)begin
        cfg_addr_q<=cfg_addr;cfg_data_q<=cfg_data;
        start_base_q<=start_base;start_limit_q<=start_limit;start_loops_q<=start_loops;start_ctx_q<=start_ctx;
    end
    reg running;
    reg [AW-1:0] pc,base;
    reg [AW:0] limit;
    reg [15:0] loops_left;
    reg [31:0] issued;
    reg valid0,valid1,last0,last1;
    reg [AW-1:0] pc0,pc1;
    reg [31:0] ord0,ord1;
    reg [XW-1:0] ctx_r,ctx0,ctx1;
    reg [15:0] iter_r,it0,it1;
    reg lit0,lit1;
    reg [255:0] captured;
    wire [255:0] macro_data;
    (* keep="true",dont_touch="true" *) reg [7:0] bsel_k;        // = pc0[AW-1] (read-mux bank select)
    (* keep="true",dont_touch="true" *) reg [NCS:0] wok_k;       // = word_ok of `captured` (registered one edge early)
    (* keep="true",dont_touch="true" *) reg [NVK-1:0] v1_k;      // = valid1
    wire busy=running|valid0|valid1;
    wire legal_start=start_limit_q>{1'b0,start_base_q} && start_limit_q<=(1<<AW) && start_loops_q!=0;
    wire final_issue=({1'b0,pc}+1'b1==limit) && loops_left==1;
    wire [255:0] idmask=256'((1<<AW)-1)<<224;
    wire wok_d=macro_data[255:240]==16'hc7a1 && macro_data[224+:AW]==((HM==4)?pc1:pc0) &&
               (macro_data[239:224]&~idmask[239:224])==0 && macro_data[223:W]==0;
    wire word_ok=wok_k[NCS];
    wire wr_ok=cfg_we_q && !busy && !start_v_q;
    generate if(AW==10)begin:g_m1
        ot_sram_1r1w_1024x256_m2_r2c2 u_program(
            .clk(clk),.r_ce_in(running),.r_addr_in(pc[9:0]),.rd_out(macro_data),
            .w_ce_in(wr_ok),.w_addr_in(cfg_addr_q[9:0]),.wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
            .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
    end else begin:g_m2
        wire [255:0] rd_lo,rd_hi;
        ot_sram_1r1w_1024x256_m2_r2c2 u_program_lo(
            .clk(clk),.r_ce_in(running && !pc[AW-1]),.r_addr_in(pc[9:0]),.rd_out(rd_lo),
            .w_ce_in(wr_ok && !cfg_addr_q[AW-1]),.w_addr_in(cfg_addr_q[9:0]),.wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
            .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_program_hi(
            .clk(clk),.r_ce_in(running && pc[AW-1]),.r_addr_in(pc[9:0]),.rd_out(rd_hi),
            .w_ce_in(wr_ok && cfg_addr_q[AW-1]),.w_addr_in(cfg_addr_q[9:0]),.wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
            .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
        for(genvar s=0;s<8;s=s+1)begin:g_bs
            assign macro_data[s*32+:32]=bsel_k[s]?rd_hi[s*32+:32]:rd_lo[s*32+:32];
        end
    end endgenerate
    // datapath: payload, ordinal, context, identity (no reset), gated by the per-slice KEPT copies
    integer cb;
    always @(posedge clk)begin
        captured<=macro_data;wok_k<={(NCS+1){wok_d}};bsel_k<={8{pc[AW-1]}};
        pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;ctx0<=ctx_r;ctx1<=ctx0;
        it0<=iter_r;it1<=it0;lit0<=loops_left==1;lit1<=lit0;
        calendar_iter<=v1_k[NVK-1]?it1:16'd0;calendar_lastit<=v1_k[NVK-1]&&lit1;
        for(cb=0;cb<W;cb=cb+1)calendar[cb]<=v1_k[cb/32]&&wok_k[cb/32]&&captured[cb];
        for(cb=0;cb<XW;cb=cb+1)calendar_ctx[cb]<=v1_k[NCS+cb/32]&&ctx1[cb];
        ordinal<=ord1;
        if(start_v_q && !(busy || cfg_we_q || !legal_start))begin
            pc<=start_base_q;base<=start_base_q;limit<=start_limit_q;
            loops_left<=start_loops_q;issued<=0;iter_r<=0;
            if(MUT!=3)ctx_r<=start_ctx_q;
        end
        if(running)begin
            issued<=issued+1;
            if({1'b0,pc}+1'b1==limit)begin
                if(loops_left!=1)begin
                    pc<=base + ((MUT==1)?1'b1:1'b0);
                    loops_left<=loops_left-1;iter_r<=iter_r+1'b1;
                end
            end else pc<=pc+1'b1;
        end
    end
    // control (rst_n[0]: 11 flops; rst_n[1]: valid1 copies)
    always @(posedge clk or negedge rst_n[0])
        if(!rst_n[0])begin
            cfg_we_q<=0;start_v_q<=0;running<=0;
            valid0<=0;valid1<=0;last0<=0;last1<=0;calendar_v<=0;
            active<=0;done<=0;fault<=0;
        end else begin
            cfg_we_q<=cfg_we;start_v_q<=start_v;
            valid0<=running;valid1<=valid0;last0<=running && final_issue;last1<=last0;
            calendar_v<=valid1;
            active<=busy;done<=valid1 && last1;
            if(valid1 && !word_ok)fault<=1;
            if(cfg_we_q && (busy || start_v_q))fault<=1;
            if(start_v_q)begin
                if(busy || cfg_we_q || !legal_start)fault<=1;
                else running<=1;
            end
            if(running && {1'b0,pc}+1'b1==limit)begin
                if(loops_left==1)running<=0;
                else if(MUT==2)running<=0;
            end
        end
    always @(posedge clk or negedge rst_n[1])
        if(!rst_n[1])v1_k<=0;else v1_k<={NVK{valid0}};
endmodule
`default_nettype wire
