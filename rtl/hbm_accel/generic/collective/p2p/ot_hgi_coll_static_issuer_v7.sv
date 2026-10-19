`timescale 1ns/1ps
`default_nettype none
// HBM-COLL256-KITS (10-19, coordinator HANDOFF 0ky + owner SAFE-DESIGN checklist): the 256-row COLL issuer.
//
// Why a new core: ot_hgi_coll_static_issuer_v6 at ROWS 256 keeps the row metadata, the per-row loop copies and the
// pre-decoded counts in flops (meta 256x64 + rowloops 256x32 + rowcm1 256x32 = 32 kb, runtime-indexed, three 256:1 x 64b
// successor muxes, a 256-way lid compare on every loop edge): checklist items 3/4/5 fail. v6 ROWS 256 stays in the tree
// only as the cycle reference of this core (miter tb_hgi_coll_static_issuer_v7_miter.sv).
//
// Structure (same ISA, same cfg37 protocol, same edges on every port as v6 ROWS 256 for every programme that meets the
// two constraints below):
//  * programme words: 3 banks x 2 x ot_sram_1r1w_256x256 (ot_hgi_coll_static_program_bank256; low/high 256 b of the
//    512-b bank word, no row select at all) instead of 12 x 64x512 (coordinator 0ky).
//  * row metadata: 4 identical copies in ot_sram_1rw_256x64 macros (written together by cfg modes 2/3 with a half-word
//    mask). The core keeps the CURRENT row (C), both successors (CT = row C.target, CN = row C.next) in registers and
//    reads the four grand-successors (CT.target, CT.next, CN.target, CN.next) from the four copies every edge; the
//    loop decision (flops only) selects which two words become the new CT/CN. The only path through a macro is
//    macro Q -> 2:1 (decision) -> macro address of the next read (no SRAM -> logic -> SRAM chain).
//  * loop counters by loop id: NL (32) x 32-b counters L1[lid] = loops+1 (1 kb), replacing the 256 per-row copies.
//    The decision is one compare of two flops (lp1 < count  <=>  v6 has && loops < count-1).
//  * row-valid bits stay flops (5 x 256 b, single-bit 256:1 reads from the pc register).
//  * priming: while no programme runs, the core reads row start_pc, then its two successors, then its four
//    grand-successors (3 edges) into C/CT/CN shadow registers (PR_*), and re-primes after any metadata write or
//    start_pc change. start copies PR_* into C/CT/CN, so the first fetch edge has everything in registers.
// Programme constraints (v6 had: start never on the edge after a metadata write):
//  (a) start_pc stable and no metadata write (cfg mode 2/3) during the 4 edges before start. The COLL programme
//      target at ROWS 256 sets issuer_start_pc at descriptor accept (>= ROWS+2 edges before launch) and drains 53 edges
//      after the last metadata write, so the F20 protocol always meets it. A start that violates it FAULTS (no launch).
//  (b) loop ids < NL (cfg mode 3 with lid >= NL faults and writes nothing). The compilers map their loop ids densely
//      (tools/hbm_coll_static/argmax_rows.py --rows 256).
// Spare-bit check: v6 faults at fetch on meta[63:57] != 0; mode 3 refuses those bits, so they are 0 on every row whose
// metadata is valid (an invalid row faults on the same edge through the valid bits) -> not repeated here.
module ot_hgi_coll_static_issuer_v7 #(
    parameter integer MUT_DATA=0, MUT_BRANCH=0, MUT_RELOAD=0, parameter integer NL=32
)(
    input wire clk_control,
    input wire [2:0] clk_mem,
    input wire rst_n,
    input wire [36:0] cfg,
    input wire start,
    input wire [7:0] start_pc,
    output reg busy,done,fault,
    output reg uop_v,
    output wire [1535:0] uop,
    output reg [31:0] iteration,
    output reg [7:0] uop_pc
);
    localparam integer LW=(NL<=2)?1:$clog2(NL);
    // ---- metadata field decode (v6 ROWS 256 positions)
    function automatic [7:0] f_next(input [63:0] x); f_next={x[54],x[51],x[5:0]}; endfunction
    function automatic [7:0] f_tgt(input [63:0] x); f_tgt={x[55],x[52],x[11:6]}; endfunction
    function automatic [7:0] f_lid8(input [63:0] x); f_lid8={x[56],x[53],x[50:45]}; endfunction
    // registered row record {next 8, target 8, lid LW, halt, has, count 32}
    localparam integer RW=8+8+LW+1+1+32;
    function automatic [RW-1:0] f_rec(input [63:0] x);
        reg [7:0] l;
        begin l=f_lid8(x);f_rec={f_next(x),f_tgt(x),l[LW-1:0],x[44],|x[43:12],x[43:12]}; end
    endfunction
    function automatic [7:0] r_next(input [RW-1:0] r); r_next=r[RW-1-:8]; endfunction
    function automatic [7:0] r_tgt(input [RW-1:0] r); r_tgt=r[RW-9-:8]; endfunction
    function automatic [LW-1:0] r_lid(input [RW-1:0] r); r_lid=r[33+LW:34]; endfunction
    function automatic r_halt(input [RW-1:0] r); r_halt=r[33]; endfunction
    function automatic r_has(input [RW-1:0] r); r_has=r[32]; endfunction
    function automatic [31:0] r_cnt(input [RW-1:0] r); r_cnt=r[31:0]; endfunction

    // ---- cfg37 programming state (as v6)
    reg [255:0] word_valid[0:2];
    reg [255:0] meta_lo_valid,meta_hi_valid;
    reg [7:0] cfg_row,pc;
    reg [1:0] cfg_bank;
    reg cfg_selected;
    reg [3:0] fragment;
    reg [511:0] assemble;
    reg [2:0] write_v;
    reg [7:0] write_row;
    reg [511:0] write_data;
    reg fetching,fetch_v,v1,h0,h1;
    reg [7:0] fetch_pc,pc1;
    reg [31:0] it0,it1;
    for(genvar b=0;b<3;b=b+1)begin:g_mem
        ot_hgi_coll_static_program_bank256 #(.MUT_DATA(MUT_DATA && b==0)) u_bank(
            .clk(clk_mem[b]),.read_v(fetch_v),.read_row(fetch_pc),
            .write_v(write_v[b]),.write_row(write_row),.write_data(write_data),
            .data(uop[b*512+:512]));
    end

    // ---- current row, successors, priming shadows, loop counters (data registers: no reset, loaded before use)
    reg [RW-1:0] rc,rt,rn;          // C, CT, CN
    reg [RW-1:0] pr_c,pr_t,pr_n;    // primed C/CT/CN for start_pc
    reg [31:0] lp1;                 // loops+1 of the current row's lid
    reg [31:0] L1[0:NL-1];
    reg [1:0] ph;                   // priming phase (3 = pr_* valid for sp_q)
    reg [7:0] sp_q;

    // ---- the decision (flops only)
`ifdef OT_COLL_ISS7_MUT_RELOAD
    localparam integer MRL=1;
`else
    localparam integer MRL=MUT_RELOAD;
`endif
    wire take=r_has(rc) && ((MRL!=0) ? (lp1<=r_cnt(rc)) : (lp1<r_cnt(rc))) && MUT_BRANCH==0;
    wire [31:0] nlp=take ? lp1+32'd1 : 32'd1;                     // L1[lid(C)] after this visit (when has)
    wire advance=fetching && !r_halt(rc);
    wire upd=advance && r_has(rc) && MUT_BRANCH==0;
`ifdef OT_COLL_ISS7_MUT_NOFWD
    wire [31:0] l_t=L1[r_lid(rt)],l_n=L1[r_lid(rn)];             // mutant: successor sharing the lid reads the stale counter
`else
    wire [31:0] l_t=(upd && r_lid(rt)==r_lid(rc)) ? nlp : L1[r_lid(rt)];
    wire [31:0] l_n=(upd && r_lid(rn)==r_lid(rc)) ? nlp : L1[r_lid(rn)];
`endif

    // ---- metadata copies: write port (cfg modes 2/3) and the four read addresses
    wire meta_op=cfg[36] && !(busy || start) && (cfg[35:32]==4'd2 || cfg[35:32]==4'd3);
    wire [7:0] lid_hi={cfg[24],cfg[21],cfg[18:13]};                  // lid field of a mode-3 word
    wire m2_ok=cfg_selected && fragment==0;
    wire m3_ok=cfg_selected && fragment==0 && cfg[31:25]==0 && lid_hi<NL;
    wire mw=meta_op && ((cfg[35:32]==4'd2) ? m2_ok : m3_ok);        // a metadata half is written this edge
    wire [63:0] mw_d=(cfg[35:32]==4'd2) ? {32'd0,cfg[31:0]} : {cfg[31:0],32'd0};
    wire [63:0] mw_m=(cfg[35:32]==4'd2) ? {32'd0,{32{1'b1}}} : {{32{1'b1}},32'd0};
    wire [255:0] mo_all;                                              // copy k read data = mo_all[k*64+:64]
    wire [63:0] mo0=mo_all[0+:64],mo1=mo_all[64+:64],mo2=mo_all[128+:64],mo3=mo_all[192+:64];
    wire mism=start_pc!=sp_q;
    wire [1:0] phe=mism ? 2'd0 : ph;                                  // effective priming phase
    // run: the new CT/CN words (take selects the grand-successor pair of the chosen successor)
`ifdef OT_COLL_ISS7_MUT_SWAP
    wire [63:0] nt_w=take ? mo2 : mo0, nn_w=take ? mo3 : mo1;   // mutant: pairs swapped
`else
    wire [63:0] nt_w=take ? mo0 : mo2, nn_w=take ? mo1 : mo3;
`endif
    reg [31:0] ra;reg [3:0] rce;                                      // copy k address = ra[k*8+:8]
    always @*begin
        ra=32'd0;rce=4'd0;
        if(mw)ra={4{cfg_row}};
        else if(advance)begin rce=4'hf;ra={f_next(nn_w),f_tgt(nn_w),f_next(nt_w),f_tgt(nt_w)};end
        else case(phe)
            2'd0:begin rce=4'h1;ra={24'd0,start_pc};end
            2'd1:begin rce=4'h3;ra={16'd0,f_next(mo0),f_tgt(mo0)};end
            2'd2:begin rce=4'hf;ra={f_next(mo1),f_tgt(mo1),f_next(mo0),f_tgt(mo0)};end
            default:begin rce=4'hf;ra={r_next(pr_n),r_tgt(pr_n),r_next(pr_t),r_tgt(pr_t)};end
        endcase
    end
    for(genvar k=0;k<4;k=k+1)begin:g_meta
        ot_sram_1rw_256x64_m4_r2c2 u_sram(.clk(clk_control),.ce_in(mw || rce[k]),.we_in(mw),.addr_in(ra[k*8+:8]),
            .wd_in(mw_d),.w_mask_in(mw_m),.rd_out(mo_all[k*64+:64]),
            .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(12'b0));
    end
    wire ready=ph==2'd3 && !mism;

    // ---- data registers without reset
    always @(posedge clk_control)begin
        sp_q<=start_pc;
        if(!mw && !advance)begin
            if(phe==2'd1)pr_c<=f_rec(mo0);
            if(phe==2'd2)begin pr_t<=f_rec(mo0);pr_n<=f_rec(mo1);end
        end
        if(start && !(busy || cfg[36] || fragment!=0) && ready)begin
            for(integer i=0;i<NL;i=i+1)L1[i]<=32'd1;
            rc<=pr_c;rt<=pr_t;rn<=pr_n;lp1<=32'd1;
        end
        if(advance)begin
            if(upd)L1[r_lid(rc)]<=nlp;
            rc<=take ? rt : rn;
            lp1<=take ? l_t : l_n;
            rt<=f_rec(nt_w);rn<=f_rec(nn_w);
        end
    end
    // ---- control (async reset, as v6)
    always @(posedge clk_control or negedge rst_n)begin
        if(!rst_n)begin
            busy<=0;done<=0;fault<=0;fetching<=0;fetch_v<=0;v1<=0;uop_v<=0;
            h0<=0;h1<=0;cfg_selected<=0;fragment<=0;write_v<=0;ph<=2'd0;
            meta_lo_valid<=0;meta_hi_valid<=0;iteration<=0;uop_pc<=0;
            for(integer b=0;b<3;b=b+1)word_valid[b]<=0;
        end else begin
            done<=0;write_v<=0;fetch_v<=0;
            v1<=fetch_v;uop_v<=v1;
            pc1<=fetch_pc;uop_pc<=pc1;it1<=it0;iteration<=it1;h1<=h0;
            if(v1 && h1)begin busy<=0;done<=1;end
            // priming phase
            if(mw)ph<=2'd0;
            else if(advance)begin if(mism)ph<=2'd0;end
            else ph<=(phe==2'd3) ? 2'd3 : phe+2'd1;
            if(start)begin
                if(busy || cfg[36] || fragment!=0 || !ready)fault<=1;
                else begin
                    pc<=start_pc;busy<=1;fetching<=1;
                end
            end
            if(fetching)begin
                if(!word_valid[0][pc] || !word_valid[1][pc] || !word_valid[2][pc] ||
                   !meta_lo_valid[pc] || !meta_hi_valid[pc])fault<=1;
                fetch_v<=1;fetch_pc<=pc;it0<=lp1-32'd1;h0<=r_halt(rc);
                if(r_halt(rc))fetching<=0;
`ifdef OT_COLL_ISS_MUT_PCWRAP
                else pc<=(take ? r_tgt(rc) : r_next(rc)) & 8'h7f;      // mutant: pc MSB dropped (wraps at 128)
`else
                else pc<=take ? r_tgt(rc) : r_next(rc);
`endif
            end
            if(cfg[36])begin
                if(busy || start)fault<=1;
                else case(cfg[35:32])
                    4'd0:begin
                        if(fragment!=0 || cfg[31:10]!=0 || cfg[7:6]==3)fault<=1;
                        cfg_row<={cfg[9:8],cfg[5:0]};cfg_bank<=cfg[7:6];cfg_selected<=cfg[7:6]!=3;
                        fragment<=0;
                    end
                    4'd1:begin
                        if(!cfg_selected || cfg_bank==3)fault<=1;
                        else begin
                            assemble[fragment*32+:32]<=cfg[31:0];fragment<=fragment+1'b1;
                            if(fragment==15)begin
                                write_v[cfg_bank]<=1;write_row<=cfg_row;
                                write_data<={cfg[31:0],assemble[479:0]};
                                word_valid[cfg_bank][cfg_row]<=1;
                            end
                        end
                    end
                    4'd2:begin
                        if(!m2_ok)fault<=1;
                        else meta_lo_valid[cfg_row]<=1;
                    end
                    4'd3:begin
                        if(!m3_ok)fault<=1;
                        else meta_hi_valid[cfg_row]<=1;
                    end
                    default:fault<=1;
                endcase
            end
        end
    end
endmodule

// 512-b programme bank of the 256-row issuer: two ot_sram_1r1w_256x256 (bits 255:0 / 511:256), same read timing as
// ot_hgi_coll_static_program_bank (macro read at the fetch edge, data registered on the next edge).
module ot_hgi_coll_static_program_bank256 #(parameter integer MUT_DATA=0)(
    input wire clk,read_v,write_v,
    input wire [7:0] read_row,write_row,
    input wire [511:0] write_data,
    output reg [511:0] data
);
    wire [255:0] rq_lo,rq_hi;
    ot_sram_1r1w_256x256_m2_r2c2 u_sram_lo(
        .clk(clk),.r_ce_in(read_v),.r_addr_in(read_row),.rd_out(rq_lo),
        .w_ce_in(write_v),.w_addr_in(write_row),.wd_in(write_data[255:0]),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    ot_sram_1r1w_256x256_m2_r2c2 u_sram_hi(
        .clk(clk),.r_ce_in(read_v),.r_addr_in(read_row),.rd_out(rq_hi),
        .w_ce_in(write_v),.w_addr_in(write_row),.wd_in(write_data[511:256]),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    always @(posedge clk)data<={rq_hi,rq_lo}^(MUT_DATA?512'b1:512'b0);
endmodule

// The 256-row issuer leaf: ot_hgi_coll_issuer_m (ot_hfd_coll_q_hard_v5.sv) with the v7 core; same ports/edges at PW 8.
module ot_hgi_coll_issuer_m256 #(parameter integer PIN_REGS=1)(
 input wire clk_control,input wire rst_n,
 input wire [36:0] cfg,input wire start,input wire [7:0] start_pc,
 output wire busy,done,fault,uop_v,
 output wire [7:0] uop_pc,
 output reg [1535:0] uop_d1,
 output reg busy_d3,done_d3,start_d3,
 output reg busy_d2,start_d2,
 output wire [31:0] tap_iteration,
 output wire [87:0] tap_steps
);
 wire [1535:0] raw,uop;wire [31:0] iteration;
 reg rst_l;
 always @(posedge clk_control or negedge rst_n) if(!rst_n)rst_l<=1'b0;else rst_l<=1'b1;
 wire [36:0] cfg_i;wire start_i;wire [7:0] start_pc_i;wire busy_c;
`ifdef OT_COLL_ISS_MUT_NOPIN
 localparam integer PR=0;
`else
 localparam integer PR=PIN_REGS;
`endif
 generate if(PR!=0)begin:g_pin
  reg [35:0] cfg_q;reg cfgv_q,start_q;reg [7:0] start_pc_q;
  always @(posedge clk_control)begin cfg_q<=cfg[35:0];start_pc_q<=start_pc;end
  always @(posedge clk_control or negedge rst_l) if(!rst_l)begin cfgv_q<=1'b0;start_q<=1'b0;end
   else begin cfgv_q<=cfg[36];start_q<=start;end
  assign cfg_i={cfgv_q,cfg_q};assign start_i=start_q;assign start_pc_i=start_pc_q;
`ifdef OT_COLL_ISS_MUT_NOHOLD
  assign busy=busy_c;
`else
  assign busy=busy_c|start_q;
`endif
 end else begin:g_nopin
  assign cfg_i=cfg;assign start_i=start;assign start_pc_i=start_pc;assign busy=busy_c;
 end endgenerate
 ot_hgi_coll_static_issuer_v7 u_issuer(.clk_control(clk_control),.clk_mem({3{clk_control}}),.rst_n(rst_l),
  .cfg(cfg_i),.start(start_i),.start_pc(start_pc_i),.busy(busy_c),.done(done),.fault(fault),
  .uop_v(uop_v),.uop(raw),.iteration(iteration),.uop_pc(uop_pc));
`ifdef OT_COLL_V5_MUT_NOMASK
 assign uop=raw;
`else
 assign uop=uop_v?raw:1536'd0;
`endif
 assign tap_iteration=iteration;
 assign tap_steps={uop[1407+:8],uop[1318+:16],uop[1350+:16],uop[1366+:16],uop[1302+:16],uop[1334+:16]};
 reg busy_d1,done_d1,done_d2,start_d1;
 always @(posedge clk_control)uop_d1<=uop;
 always @(posedge clk_control or negedge rst_l)
  if(!rst_l)begin busy_d1<=0;busy_d2<=0;busy_d3<=0;done_d1<=0;done_d2<=0;done_d3<=0;start_d1<=0;start_d2<=0;start_d3<=0;end
  else begin busy_d1<=busy_c;busy_d2<=busy_d1;busy_d3<=busy_d2;done_d1<=done;done_d2<=done_d1;done_d3<=done_d2;
   start_d1<=start_i;start_d2<=start_d1;start_d3<=start_d2;end
endmodule
`default_nettype wire
