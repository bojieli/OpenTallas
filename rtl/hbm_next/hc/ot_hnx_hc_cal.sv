`timescale 1ns/1ps
`default_nettype none
// HC programme calendar (HUB-SAFE2 2026-10-20, kit hnx_hcq_hub_safe2_1020): the hc_<q> copy of ot_vms_calendar_static
// (same SRAM, capture rung, word protection, pc / loop / fault behaviour and internal names valid0 / macro_data) with
// two SAFE-DESIGN changes (item 3, fanout; zero added edges):
//  (a) only the ACTION bits of the calendar word (residual_launch [0], gather_phase [21], gather_launch [22],
//      store_slot [59]) are gated by valid1 && word_ok; the payload fields leave the capture register ungated (they are
//      read only under their action bit).  Before, one word_ok net gated all 111 calendar flops.
//  (b) the result store's bank routing is decoded here, from the CAPTURE register, on the SAME edge as the calendar
//      word: per sector j (0..2) the bank one-hot of s_j = base + position * row_stride + j (row_stride 0 = 3) as KEPT
//      copies, one per 32-bit data lane group (SG = 8 groups of a 256-bit sector), already gated by the store slot;
//      st_v[b] (bank b written) and st_hdr[b] (its sector address).  ot_hnx_hgi_hc_result_vm builds local_wq from them
//      with one AND-OR level, so no calendar flop drives the 768 x 8 store crossbar (census safe1019: decode nets with
//      736..800 loads, c[*] up to 100 loads).
// MUT_STRIDE (bench MUT 7 of ot_hnx_hc_q): the store ignores the row stride (s_j = base + position * 3 + j).
// st_hdr is NOT gated here (the result store gates it with st_v); st_sel copies are gated by the store slot.
module ot_hnx_hc_cal #(
    parameter integer W=111,
    parameter integer MUT=0, // 1 wrong wrap PC, 2 extra cycle at loop boundary (ot_vms_calendar_static)
    parameter integer MUT_STRIDE=0,
    parameter integer MUT_SBASE=0   // bench MUT 2 of ot_hnx_hc_q: the result store lands one sector late (base + 1)
)(
    input wire clk,rst_n,
    input wire cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output reg [W-1:0] calendar,
    output reg calendar_v,
    output reg [31:0] ordinal,
    output reg active,done,fault,
    // store routing (same edge as calendar)
    output reg [7:0] st_v,               // bank b is written by this word's store slot
    output reg [8*16-1:0] st_hdr,        // bank b's sector address (s_j of the sector that maps to b; 0 if none)
    output wire [3*8*8-1:0] st_sel,      // [(j*8+b)*8+g]: sector j -> bank b, copy for data lane group g (gated)
    output wire [15:0] gp_c,             // KEPT copies of calendar[21] (gather_phase): [b] lg_rq address select of bank b,
                                         // [8+b] its request-valid select + return-valid gates (HUB-SAFE3: was 8, 37 loads)
    output wire [5:0] lc_c               // HUB-SAFE3: KEPT copies of the action bits on the calendar edge:
                                         // [1:0] residual_launch (calendar[0]), [5:2] gather_launch (calendar[22])
);
// HUB-SAFE3 2026-10-20 (census safe2, zero added edges): valid1 has 3 kept copies (the gate fans out per consumer group:
// st routing / gp+lc copies / calendar action bits; word_ok drove 47), start_v_q 3 kept copies (start acceptance per
// register group: 42), running a kept copy for the 32-b issued counter.
    initial if(W!=111)$fatal(1,"ot_hnx_hc_cal: the hc_<q> calendar word is 111 bits");
    reg cfg_we_q,start_v_q;
    reg [9:0] cfg_addr_q,start_base_q;
    reg [255:0] cfg_data_q;
    reg [10:0] start_limit_q;
    reg [15:0] start_loops_q;
    always @(posedge clk)begin
        cfg_addr_q<=cfg_addr;cfg_data_q<=cfg_data;
        start_base_q<=start_base;start_limit_q<=start_limit;start_loops_q<=start_loops;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin cfg_we_q<=0;start_v_q<=0;sv_c<=0;end
        else begin cfg_we_q<=cfg_we;start_v_q<=start_v;sv_c<={3{start_v}};end
    reg running;
    reg [9:0] pc,base;
    reg [10:0] limit;
    reg [15:0] loops_left;
    reg [31:0] issued;
    reg valid0,valid1,last0,last1;
    (* keep = "true", dont_touch = "true" *) reg [2:0] v1_c;      // = valid1
    (* keep = "true", dont_touch = "true" *) reg [2:0] sv_c;      // = start_v_q
    (* keep = "true", dont_touch = "true" *) reg run_c;           // = running
    reg [9:0] pc0,pc1;
    reg [31:0] ord0,ord1;
    reg [255:0] captured;
    wire [255:0] macro_data;
    wire busy=running|valid0|valid1;
    wire legal_start=start_limit_q>{1'b0,start_base_q} && start_limit_q<=11'd1024 && start_loops_q!=0;
    wire final_issue=({1'b0,pc}+11'd1==limit) && loops_left==1;
    wire word_ok=captured[255:240]==16'hc7a1 && captured[233:224]==pc1 &&
                 captured[239:234]==0 && captured[223:W]==0;
    ot_sram_1r1w_1024x256_m2_r2c2 u_program(
        .clk(clk),.r_ce_in(running),.r_addr_in(pc),.rd_out(macro_data),
        .w_ce_in(cfg_we_q && !busy && !start_v_q),.w_addr_in(cfg_addr_q),.wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
        .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
    // ---- (a) action-bit gating
    wire gate=v1_c[2] && word_ok;            // calendar action bits
    wire gate_s=v1_c[0] && word_ok;          // store routing
    wire gate_c=v1_c[1] && word_ok;          // gp / lc copies
    localparam [W-1:0] ACT=(W'(1)<<0)|(W'(1)<<21)|(W'(1)<<22)|(W'(1)<<59);
    // ---- (b) store routing, decoded from the capture register
    wire slot=gate_s && captured[59];
    wire [15:0] sbase=captured[75:60]+16'(MUT_SBASE);
    wire [2:0] spos=captured[78:76];
    wire [15:0] srs=(captured[110:95]==16'd0||MUT_STRIDE!=0)?16'd3:captured[110:95];
    wire [15:0] s0=sbase+16'(spos)*srs;
    wire [15:0] sj[0:2];
    assign sj[0]=s0; assign sj[1]=s0+16'd1; assign sj[2]=s0+16'd2;
    reg [7:0] v_n; reg [8*16-1:0] h_n;
    always @*begin
        v_n=0;h_n=0;
        for(integer j=0;j<3;j=j+1)begin
            v_n[sj[j][2:0]]=slot;
            h_n[sj[j][2:0]*16+:16]=sj[j];
        end
    end
    // Payload, ordinal and address identity have dedicated, nonreset rungs.
    always @(posedge clk)begin
        captured<=macro_data;
        pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;
        calendar<=(captured[W-1:0]&~ACT)|(gate?(captured[W-1:0]&ACT):{W{1'b0}});
        ordinal<=ord1;
        st_hdr<=h_n;
    end
    // KEPT one-hot copies: one per (sector, bank, 32-bit lane group); every copy of a (j, b) has the same D (slot && the
    // sector's bank == b), so they are identical registers that synthesis must not fold (ot_keep_regs.tcl).
    for(genvar j=0;j<3;j=j+1)begin:g_sj
        for(genvar b=0;b<8;b=b+1)begin:g_sb
            wire d_sel=slot && sj[j][2:0]==3'(b);
            (* keep = "true", dont_touch = "true" *) reg [7:0] sel_c;
            always @(posedge clk)sel_c<={8{d_sel}};
            assign st_sel[(j*8+b)*8+:8]=sel_c;
        end
    end
    (* keep = "true", dont_touch = "true" *) reg [15:0] gp_r;
    always @(posedge clk)gp_r<={16{gate_c && captured[21]}};
    assign gp_c=gp_r;
    (* keep = "true", dont_touch = "true" *) reg [5:0] lc_r;
    always @(posedge clk)lc_r<={{4{gate_c && captured[22]}},{2{gate_c && captured[0]}}};
    assign lc_c=lc_r;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            running<=0;pc<=0;base<=0;limit<=0;loops_left<=0;issued<=0;
            valid0<=0;valid1<=0;v1_c<=0;last0<=0;last1<=0;calendar_v<=0;run_c<=0;
            active<=0;done<=0;fault<=0;st_v<=0;
        end else begin
            valid0<=running;valid1<=valid0;v1_c<={3{valid0}};last0<=running && final_issue;last1<=last0;
            calendar_v<=valid1;
            active<=busy;done<=valid1 && last1;
            st_v<=v_n;
            if(valid1 && !word_ok)fault<=1;
            if(cfg_we_q && (busy || start_v_q))fault<=1;
            if(start_v_q && (busy || cfg_we_q || !legal_start))fault<=1;
            if(sv_c[0] && !(busy || cfg_we_q || !legal_start))begin running<=1;run_c<=1;pc<=start_base_q;end
            if(sv_c[1] && !(busy || cfg_we_q || !legal_start))begin base<=start_base_q;limit<=start_limit_q;end
            if(sv_c[2] && !(busy || cfg_we_q || !legal_start))begin loops_left<=start_loops_q;issued<=0;end
            if(run_c)issued<=issued+1;
            if(running)begin
                if({1'b0,pc}+11'd1==limit)begin
                    if(loops_left==1)begin running<=0;run_c<=0;end
                    else begin
                        pc<=base + ((MUT==1)?10'd1:10'd0);
                        loops_left<=loops_left-1;
                        if(MUT==2)begin running<=0;run_c<=0;end
                    end
                end else pc<=pc+1;
            end
        end
endmodule
`default_nettype wire
