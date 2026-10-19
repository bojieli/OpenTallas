`timescale 1ns/1ps
`default_nettype none
// HBM-SMBUDGET 2026-10-19 (coordinator decision 0jx, option P2 + 2,048-word store): ot_smh_calendar_static with
//   * AW-bit programme address (AW 10 = 1,024 words = one ot_sram_1r1w_1024x256 macro, exactly the old leaf; AW 11 =
//     2,048 words = two such macros banked on pc[10], read mux on the registered bank select);
//   * a launch CONTEXT sideband (XW bits, start_ctx) that travels with every word of the run it was launched with
//     (calendar_ctx is aligned with calendar), so a consumer can relocate a shape-generic programme per launch (P2:
//     the SM service feed adds the descriptor's row offset / tag base and takes its epoch / cache bank);
//   * the LOOP ITERATION of every word (calendar_iter = 0 .. loops-1, calendar_lastit = final iteration), aligned with
//     calendar, so a looped body (P2: one group-slot t step of 8 issue slots, loops = 8) can be relocated per iteration.
// Programme word: magic[255:240]=c7a1, reserved zero [239:224+AW], PC identity [224+AW-1:224], calendar [W-1:0],
// reserved zero [223:W].  Everything else (fixed range [base,limit) x loops, no ready / arrival observation, faults on a
// bad word, a write while busy, an illegal or overlapping start) is ot_smh_calendar_static unchanged.
module ot_hbm_xcal_calendar_native #(
    parameter integer W=135,
    parameter integer AW=11,
    parameter integer XW=1,
    parameter integer MUT=0 // 1 wrong wrap PC, 2 extra cycle at loop boundary, 3 context not captured (stale)
)(
    input wire clk,rst_n,rst_raw_n,reset_phase0,
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
    initial begin
        if(W<1 || W>223)$fatal(1,"SM calendar width must fit protected programme payload");
        if(AW!=10 && AW!=11)$fatal(1,"programme store: 1,024 or 2,048 words");
    end
    wire [5:0] reset_branch;
    for(genvar g=0;g<6;g=g+1)begin:g_reset_branch
      (* keep = 1 *) ot_hbm_xcal_reset_branch u_reset(.clk(clk),.rst_n(rst_raw_n),.phase0(reset_phase0),.q(reset_branch[g]));
    end
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
    always @(posedge clk or negedge reset_branch[0])
        if(!reset_branch[0])begin cfg_we_q<=0;start_v_q<=0;end
        else begin cfg_we_q<=cfg_we;start_v_q<=start_v;end
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
    wire busy=running|valid0|valid1;
    wire legal_start=start_limit_q>{1'b0,start_base_q} && start_limit_q<=(1<<AW) && start_loops_q!=0;
    wire final_issue=({1'b0,pc}+1'b1==limit) && loops_left==1;
    wire [255:0] idmask=256'((1<<AW)-1)<<224;
    wire word_ok=captured[255:240]==16'hc7a1 && captured[224+:AW]==pc1 &&
                 (captured[239:224]&~idmask[239:224])==0 && captured[223:W]==0;
    wire wr_ok=cfg_we_q && !busy && !start_v_q;
    generate if(AW==10)begin:g_m1
        ot_sram_1r1w_1024x256_m2_r2c2 u_program(
            .clk(clk),.r_ce_in(running),.r_addr_in(pc[9:0]),.rd_out(macro_data),
            .w_ce_in(wr_ok),.w_addr_in(cfg_addr_q[9:0]),.wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
            .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
    end else begin:g_m2
        // two 1024-word macros, bank = pc[10]; the macro output of the read issued at pc is selected by pc0[10]
        wire [255:0] rd_lo,rd_hi;
        ot_sram_1r1w_1024x256_m2_r2c2 u_program_lo(
            .clk(clk),.r_ce_in(running && !pc[AW-1]),.r_addr_in(pc[9:0]),.rd_out(rd_lo),
            .w_ce_in(wr_ok && !cfg_addr_q[AW-1]),.w_addr_in(cfg_addr_q[9:0]),.wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
            .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_program_hi(
            .clk(clk),.r_ce_in(running && pc[AW-1]),.r_addr_in(pc[9:0]),.rd_out(rd_hi),
            .w_ce_in(wr_ok && cfg_addr_q[AW-1]),.w_addr_in(cfg_addr_q[9:0]),.wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
            .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
        for(genvar slice=0;slice<16;slice=slice+1)begin:g_read_slice
            wire bank_q;
            (* keep = 1 *) ot_hbm_xcal_kept_bit u_bank(.clk(clk),.d(pc[AW-1]),.q(bank_q));
            assign macro_data[16*slice+:16]=bank_q?rd_hi[16*slice+:16]:rd_lo[16*slice+:16];
        end
    end endgenerate
    // Payload, ordinal, context and address identity have dedicated, nonreset rungs.
    always @(posedge clk)begin
        captured<=macro_data;
        pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;ctx0<=ctx_r;ctx1<=ctx0;
        it0<=iter_r;it1<=it0;lit0<=loops_left==1;lit1<=lit0;
        calendar_iter<=valid1?it1:16'd0;calendar_lastit<=valid1&&lit1;
        calendar_ctx<=valid1?ctx1:{XW{1'b0}};
        ordinal<=ord1;
    end
    // Compute the identical identity predicate in parallel with captured/pc1.
    // Kept copies feed at most16 calendar bits each, without adding an edge.
    wire incoming_ok=macro_data[255:240]==16'hc7a1 && macro_data[224+:AW]==pc0 &&
      (macro_data[239:224]&~idmask[239:224])==0 && macro_data[223:W]==0;
    for(genvar slice=0;slice<(W+15)/16;slice=slice+1)begin:g_calendar_slice
      localparam integer BW=(W-16*slice<16)?W-16*slice:16;
      wire word_ok_q,valid_q;
      (* keep = 1 *) ot_hbm_xcal_kept_bit u_ok(.clk(clk),.d(incoming_ok),.q(word_ok_q));
      (* keep = 1 *) ot_hbm_xcal_kept_rbit u_valid(.clk(clk),.rst_n(reset_branch[5]),.d(valid0),.q(valid_q));
      always @(posedge clk)calendar[16*slice+:BW]<=valid_q&&word_ok_q?captured[16*slice+:BW]:{BW{1'b0}};
    end
    wire [4:0] start_copy;
    wire [4:0] accept_start;
    for(genvar g=0;g<5;g=g+1)begin:g_start_copy
      (* keep = 1 *) ot_hbm_xcal_kept_rbit u_start(.clk(clk),.rst_n(reset_branch[5]),.d(start_v),.q(start_copy[g]));
      assign accept_start[g]=start_copy[g]&&!busy&&!cfg_we_q&&legal_start;
    end
    wire end_word=({1'b0,pc}+1'b1==limit);
    wire [31:0] issued_inc=issued+1;
    wire [1:0] running_copy;
    wire next_running=(running&&!(end_word&&(loops_left==1||MUT==2)))||accept_start[0];
    for(genvar g=0;g<2;g=g+1)begin:g_running_copy
      (* keep = 1 *) ot_hbm_xcal_kept_rbit u_running(.clk(clk),.rst_n(reset_branch[5]),.d(next_running),.q(running_copy[g]));
    end
    always @(posedge clk or negedge reset_branch[1])
      if(!reset_branch[1])begin running<=0;pc<=0;base<=0;end
      else begin
        if(accept_start[0])begin running<=1;pc<=start_base_q;base<=start_base_q;end
        if(running)begin
          if(end_word)begin
            if(loops_left==1)running<=0;
            else begin pc<=base+((MUT==1)?1'b1:1'b0);if(MUT==2)running<=0;end
          end else pc<=pc+1'b1;
        end
      end
    always @(posedge clk or negedge reset_branch[2])
      if(!reset_branch[2])begin limit<=0;loops_left<=0;end
      else begin
        if(accept_start[1])limit<=start_limit_q;
        if(accept_start[4])loops_left<=start_loops_q;
        if(running&&end_word&&loops_left!=1)loops_left<=loops_left-1'b1;
      end
    always @(posedge clk or negedge reset_branch[3])
      if(!reset_branch[3])begin issued[15:0]<=0;iter_r<=0;end
      else begin
        if(accept_start[2])begin issued[15:0]<=0;iter_r<=0;end
        if(running_copy[0])begin issued[15:0]<=issued_inc[15:0];if(end_word&&loops_left!=1)iter_r<=iter_r+1'b1;end
      end
    always @(posedge clk or negedge reset_branch[4])
      if(!reset_branch[4])begin issued[31:16]<=0;ctx_r<=0;end
      else begin
        if(accept_start[3])begin issued[31:16]<=0;if(MUT!=3)ctx_r<=start_ctx_q;end
        if(running_copy[1])issued[31:16]<=issued_inc[31:16];
      end
    always @(posedge clk or negedge reset_branch[5])
        if(!reset_branch[5])begin
            valid0<=0;valid1<=0;last0<=0;last1<=0;calendar_v<=0;
            active<=0;done<=0;fault<=0;
        end else begin
            valid0<=running;valid1<=valid0;last0<=running && final_issue;last1<=last0;
            calendar_v<=valid1;
            active<=busy;done<=valid1 && last1;
            if(valid1 && !word_ok)fault<=1;
            if(cfg_we_q && (busy || start_v_q))fault<=1;
            if(start_v_q && (busy || cfg_we_q || !legal_start))fault<=1;
        end
endmodule
`default_nettype wire
