`timescale 1ns/1ps
`default_nettype none
// HBM-COLLQ3-V7 (10-19, LEAD3-HBM decision "SRAM v7", SAFE-DESIGN item 5): the 128-row COLL issuer with every
// runtime-indexed table in SRAM macros. Successor of ot_hgi_coll_static_issuer_v6 #(ROWS 128) inside the q2/q3 SAFE COLL
// parents (ot_hfd_coll_{q2,q3}_lp_ars leaf ot_hgi_coll_issuer_m_r128), whose 16 kb of flop loop tables (meta 128x64,
// rowloops 128x32, rowcm1 128x32: three 128:1 x 64/32-b successor muxes + a 128-way lid compare per loop edge) failed the
// checklist. Structure = the 256-row v7 core (ot_hgi_coll_static_issuer_v7.sv, HBM-COLL256-KITS; header there) at PW 7:
//  * programme words: 3 banks x 2 x ot_sram_1r1w_128x256_m1_r2c2_p192_mir (low/high 256 b of the 512-b word, no row
//    select, read at the fetch edge, data registered on the next edge = v6 bank timing);
//  * row metadata: 4 identical copies in ot_sram_1rw_128x64_m2_r2c2_p192_mir (written together by cfg modes 2/3 with a
//    half-word mask). Registers hold the CURRENT row C and both successors CT = C.target / CN = C.next; the four copies
//    read the four grand-successors every edge; the loop decision (flops only) picks which pair becomes CT/CN. The only
//    path through a macro: macro Q -> 2:1 (decision) -> next macro address (no SRAM -> logic -> SRAM chain);
//  * loop counters by loop id: NL (32) x 32 b L1[lid] = loops+1 (1 kb flops, 32:1 read from a flop index);
//  * row-valid bits stay flops (5 x 128 b, single-bit reads from the pc register);
//  * priming: with no programme running the core reads row start_pc, its two successors, its four grand-successors
//    (3 edges) into PR_* shadows and re-primes after any metadata write / start_pc change.
// Ports, ISA, cfg37 protocol and EVERY port edge are those of v6 #(ROWS 128) (miter tb_hgi_coll_static_issuer_v7r128_miter)
// for programmes that meet the two v7 constraints:
//  (a) start_pc stable and no metadata write (cfg mode 2/3) in the 4 edges before start (else the start FAULTS, no launch).
//      The COLL programme target (fj_n2s1 / fj_q2 ROWS 128) sets issuer_start_pc at descriptor accept, >= ROWS+2 edges
//      before launch, and drains >= 53 edges after the last metadata write -> always met (parent lockstep proves it).
//  (b) loop ids < NL (a mode-3 word with lid >= NL faults and writes nothing); compilers map loop ids densely.
// Metadata fields at ROWS 128 (v6): next = {m[51], m[5:0]}, target = {m[52], m[11:6]}, lid = {m[53], m[50:45]};
// mode 0 row = {cfg[8], cfg[5:0]} (cfg[31:9] must be 0), mode 3 cfg[31:22] must be 0 (v6's fetch-time spare-bit fault
// m[63:54] != 0 is therefore unreachable on a valid row and is not repeated).
// Static schedule: no added edge on any port -> 0 cycles to the DS / Qwen token schedule (the macro read edges sit inside
// the same v6 issue timeline: metadata lookahead is two rows ahead of the fetch, programme read = the v6 bank edge).
module ot_hgi_coll_static_issuer_v7_r128 #(
    parameter integer MUT_DATA=0, MUT_BRANCH=0, MUT_RELOAD=0, parameter integer NL=32
)(
    input wire clk_control,
    input wire [2:0] clk_mem,
    input wire rst_n,
    input wire [36:0] cfg,
    input wire start,
    input wire [6:0] start_pc,
    output reg busy,done,fault,
    output reg uop_v,
    output wire [1535:0] uop,
    output reg [31:0] iteration,
    output reg [6:0] uop_pc
);
    localparam integer LW=(NL<=2)?1:$clog2(NL);
    // ---- metadata field decode (v6 ROWS 128 positions)
    function automatic [6:0] f_next(input [63:0] x); f_next={x[51],x[5:0]}; endfunction
    function automatic [6:0] f_tgt(input [63:0] x); f_tgt={x[52],x[11:6]}; endfunction
    function automatic [6:0] f_lid7(input [63:0] x); f_lid7={x[53],x[50:45]}; endfunction
    // registered row record {next 7, target 7, lid LW, halt, has, count 32}
    localparam integer RW=7+7+LW+1+1+32;
    function automatic [RW-1:0] f_rec(input [63:0] x);
        reg [6:0] l;
        begin l=f_lid7(x);f_rec={f_next(x),f_tgt(x),l[LW-1:0],x[44],|x[43:12],x[43:12]}; end
    endfunction
    function automatic [6:0] r_next(input [RW-1:0] r); r_next=r[RW-1-:7]; endfunction
    function automatic [6:0] r_tgt(input [RW-1:0] r); r_tgt=r[RW-8-:7]; endfunction
    function automatic [LW-1:0] r_lid(input [RW-1:0] r); r_lid=r[33+LW:34]; endfunction
    function automatic r_halt(input [RW-1:0] r); r_halt=r[33]; endfunction
    function automatic r_has(input [RW-1:0] r); r_has=r[32]; endfunction
    function automatic [31:0] r_cnt(input [RW-1:0] r); r_cnt=r[31:0]; endfunction

    // ---- cfg37 programming state (as v6)
    reg [127:0] word_valid[0:2];
    reg [127:0] meta_lo_valid,meta_hi_valid;
    reg [6:0] cfg_row,pc;
    reg [1:0] cfg_bank;
    reg cfg_selected;
    reg [3:0] fragment;
    reg [511:0] assemble;
    reg [2:0] write_v;
    reg [6:0] write_row;
    reg [511:0] write_data;
    reg fetching,fetch_v,v1,h0,h1;
    reg [6:0] fetch_pc,pc1;
    reg [31:0] it0,it1;
    for(genvar b=0;b<3;b=b+1)begin:g_mem
        ot_hgi_coll_static_program_bank128 #(.MUT_DATA(MUT_DATA && b==0)) u_bank(
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
    reg [6:0] sp_q;

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
    wire [6:0] lid_hi={cfg[21],cfg[18:13]};                          // lid field of a mode-3 word
    wire m2_ok=cfg_selected && fragment==0;
    wire m3_ok=cfg_selected && fragment==0 && cfg[31:22]==0 && lid_hi<NL;
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
    reg [27:0] ra;reg [3:0] rce;                                      // copy k address = ra[k*7+:7]
    always @*begin
        ra=28'd0;rce=4'd0;
        if(mw)ra={4{cfg_row}};
        else if(advance)begin rce=4'hf;ra={f_next(nn_w),f_tgt(nn_w),f_next(nt_w),f_tgt(nt_w)};end
        else case(phe)
            2'd0:begin rce=4'h1;ra={21'd0,start_pc};end
            2'd1:begin rce=4'h3;ra={14'd0,f_next(mo0),f_tgt(mo0)};end
            2'd2:begin rce=4'hf;ra={f_next(mo1),f_tgt(mo1),f_next(mo0),f_tgt(mo0)};end
            default:begin rce=4'hf;ra={r_next(pr_n),r_tgt(pr_n),r_next(pr_t),r_tgt(pr_t)};end
        endcase
    end
    for(genvar k=0;k<4;k=k+1)begin:g_meta
        ot_sram_1rw_128x64_m2_r2c2_p192_mir u_sram(.clk(clk_control),.ce_in(mw || rce[k]),.we_in(mw),.addr_in(ra[k*7+:7]),
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
                else pc<=(take ? r_tgt(rc) : r_next(rc)) & 7'h3f;      // mutant: pc MSB dropped (wraps at 64)
`else
                else pc<=take ? r_tgt(rc) : r_next(rc);
`endif
            end
            if(cfg[36])begin
                if(busy || start)fault<=1;
                else case(cfg[35:32])
                    4'd0:begin
                        if(fragment!=0 || cfg[31:9]!=0 || cfg[7:6]==3)fault<=1;
                        cfg_row<={cfg[8],cfg[5:0]};cfg_bank<=cfg[7:6];cfg_selected<=cfg[7:6]!=3;
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

// 512-b programme bank of the 128-row issuer: two ot_sram_1r1w_128x256_m1_r2c2_p192_mir (bits 255:0 / 511:256), the
// read timing of ot_hgi_coll_static_program_bank (macro read at the fetch edge, data registered on the next edge).
module ot_hgi_coll_static_program_bank128 #(parameter integer MUT_DATA=0)(
    input wire clk,read_v,write_v,
    input wire [6:0] read_row,write_row,
    input wire [511:0] write_data,
    output reg [511:0] data
);
    wire [255:0] rq_lo,rq_hi;
    ot_sram_1r1w_128x256_m1_r2c2_p192_mir u_sram_lo(
        .clk(clk),.r_ce_in(read_v),.r_addr_in(read_row),.rd_out(rq_lo),
        .w_ce_in(write_v),.w_addr_in(write_row),.wd_in(write_data[255:0]),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    ot_sram_1r1w_128x256_m1_r2c2_p192_mir u_sram_hi(
        .clk(clk),.r_ce_in(read_v),.r_addr_in(read_row),.rd_out(rq_hi),
        .w_ce_in(write_v),.w_addr_in(write_row),.wd_in(write_data[511:256]),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    always @(posedge clk)data<={rq_hi,rq_lo}^(MUT_DATA?512'b1:512'b0);
endmodule

// The 128-row issuer leaf with the v7 core: ot_hgi_coll_issuer_m #(ROWS 128) (ot_hfd_coll_q_hard_v5.sv) port for port and
// edge for edge (PIN_REGS 1: cfg/start/start_pc pin registers, raw busy = busy_c | start_q, d1 uop bank, d2/d3 control).
module ot_hgi_coll_issuer_m128v7 #(parameter integer PIN_REGS=1)(
 input wire clk_control,input wire rst_n,
 input wire [36:0] cfg,input wire start,input wire [6:0] start_pc,
 output wire busy,done,fault,uop_v,
 output wire [6:0] uop_pc,
 output reg [1535:0] uop_d1,
 output reg busy_d3,done_d3,start_d3,
 output reg busy_d2,start_d2,
 output wire [31:0] tap_iteration,
 output wire [87:0] tap_steps
);
 wire [1535:0] raw,uop;wire [31:0] iteration;
 reg rst_l;
 always @(posedge clk_control or negedge rst_n) if(!rst_n)rst_l<=1'b0;else rst_l<=1'b1;
 wire [36:0] cfg_i;wire start_i;wire [6:0] start_pc_i;wire busy_c;
`ifdef OT_COLL_ISS_MUT_NOPIN
 localparam integer PR=0;
`else
 localparam integer PR=PIN_REGS;
`endif
 generate if(PR!=0)begin:g_pin
  reg [35:0] cfg_q;reg cfgv_q,start_q;reg [6:0] start_pc_q;
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
 ot_hgi_coll_static_issuer_v7_r128 u_issuer(.clk_control(clk_control),.clk_mem({3{clk_control}}),.rst_n(rst_l),
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


`default_nettype none
// =====================================================================================================================
// HBM-COLLQ6-ISS (10-20): ot_hgi_coll_issuer_m128v8 = the 128-row issuer leaf body rebuilt for the mapped native census
// (no driver above 32 loads, reset included) on the v7 storage plan (6 x 128x256 programme SRAMs, 4 x 128x64 metadata
// SRAM copies, 32 loop-id counters).  Port for port and edge for edge = ot_hgi_coll_issuer_m #(ROWS 128) (v6) and
// ot_hgi_coll_issuer_m128v7 under the two v7 programme constraints (header of ot_hgi_coll_static_issuer_v7_r128).
// The v7 leaf mapped with 56 census violations (uop_v mask 1,537 loads, start accept / L1 init 1,111, write_data enable
// 1,031, rst_l 799, loop decision 529, pc 192, ...).  v8 structure (every wide select is a FLOP that drives its per-bit
// cells directly, so mapping cannot fold a shared gate into a wide cone):
//  * the control predicates the datapath muxes on (start accept, advance, metadata write, priming enables, effective
//    phase, loop decision, L1 write one-hots, counter forwarding, assembly enables) are computed one edge EARLY from the
//    next-state functions and the pin inputs and registered as KEPT copies (<= 16 mux bits per copy);
//  * loop counters in the visits domain q = v7 lp1 - 1: a row stores q+1 with a "zero" flag (written as !take) and a valid
//    bit cleared at start (start no longer loads 1,024 flops); reads are AND-ORs over registered one-hot selects that
//    already include valid / zero; q is kept in 4 copies (state, L1 write rows 0-15 / 16-31, forwarding);
//  * the uop_v mask is folded into the bank data register (data <= v1 ? word : 0, 16 kept v1 copies per bank);
//    write_data is dropped (the macro write port reads the assembly register: equal at the write edge);
//  * row-valid bits are set one edge after their cfg word (registered one-hot row + group enables); they are read only by
//    the fetch check, >= 2 edges after any cfg word, through 4 kept pc copies (32 rows each);
//  * decoders are explicit 2+3 predecodes; reset: 32 kept release copies (one edge = v7 rst_l), each clearing / holding <= 32 flops.
// Mutants: OT_COLL_ISS8_MUT_RELOAD (decision off by one), _NOFWD (no counter forwarding), _SWAP (grand-successor pairs).
module ot_hgi_coll_issuer_m128v8 (
 input wire clk_control,input wire rst_n,
 input wire [36:0] cfg,input wire start,input wire [6:0] start_pc,
 output wire busy,done,fault,uop_v,
 output wire [6:0] uop_pc,
 output reg [1535:0] uop_d1,
 output reg busy_d3,done_d3,start_d3,
 output reg busy_d2,start_d2,
 output wire [31:0] tap_iteration,
 output wire [87:0] tap_steps
);
 localparam integer NR=32;
 wire clk=clk_control;
 // ---------------- reset release copies (each = v7 rst_l) ----------------
 (* keep = "true" *) reg [NR-1:0] rcp;
 always @(posedge clk or negedge rst_n) if(!rst_n) rcp<={NR{1'b0}}; else rcp<={NR{1'b1}};
 // ---------------- helpers ----------------
 function automatic [6:0] f_next(input [63:0] x); f_next={x[51],x[5:0]}; endfunction
 function automatic [6:0] f_tgt(input [63:0] x); f_tgt={x[52],x[11:6]}; endfunction
 // record {next 7 [52:46], tgt 7 [45:39], lid 5 [38:34], halt [33], has [32], cm1 32 [31:0]}; cm1 = count - 1
 localparam integer RW=53;
 function automatic [RW-1:0] f_rec(input [63:0] x);
  f_rec={f_next(x),f_tgt(x),x[49:45],x[44],|x[43:12],x[43:12]-32'd1};
 endfunction
 function automatic [6:0] r_next(input [RW-1:0] r); r_next=r[52:46]; endfunction
 function automatic [6:0] r_tgt(input [RW-1:0] r); r_tgt=r[45:39]; endfunction
 function automatic [4:0] r_lid(input [RW-1:0] r); r_lid=r[38:34]; endfunction
 function automatic r_has(input [RW-1:0] r); r_has=r[32]; endfunction
 function automatic [31:0] r_cm1(input [RW-1:0] r); r_cm1=r[31:0]; endfunction
 // loop decision, visits domain: take = has && (q < count-1)   (reload mutant: q <= count-1 = v7 lp1 <= count)
 function automatic f_take(input has,input [31:0] qv,input [31:0] cm1);
`ifdef OT_COLL_ISS8_MUT_RELOAD
  f_take=has && (qv<=cm1);
`else
  f_take=has && (qv<cm1);
`endif
 endfunction
 // explicit 2+3 predecoded 5->32 one-hot (with enable)
 function automatic [31:0] f_dec(input en,input [4:0] a);
  reg [3:0] pa;reg [7:0] pb;
  begin
   pa=en ? (4'd1<<a[4:3]) : 4'd0;pb=8'd1<<a[2:0];
   for(integer i=0;i<32;i=i+1)f_dec[i]=pa[i/8] & pb[i%8];
  end
 endfunction
 // ---------------- pin registers (as v7: cfg / start / start_pc registered, +1 issue edge) ----------------
 reg [35:0] cfg_q;reg [6:0] start_pc_q;reg cfgv_q,start_q;
 reg [3:0] md_q;                               // md_q[k] = cfg[36] && mode == k, registered beside cfg_q
 (* keep = "true" *) reg [3:0] mlo_c,mhi_c;    // metadata write masks per macro: lo = (mode == 2), hi = (mode != 2)
 (* keep = "true" *) reg wdl_c,wdh_c;          // metadata write data gates: lo = (mode == 2), hi = (mode != 2)
 always @(posedge clk)begin
  cfg_q<=cfg[35:0];start_pc_q<=start_pc;
  mlo_c<={4{cfg[35:32]==4'd2}};mhi_c<={4{cfg[35:32]!=4'd2}};
  wdl_c<=cfg[35:32]==4'd2;wdh_c<=cfg[35:32]!=4'd2;
 end
 // ---------------- state ----------------
 reg busy_r,done_r,fault_r,v1,uop_v_r,h0,h1,cfg_selected;
 reg [3:0] fragment;reg [2:0] write_v;reg [1:0] ph;
 (* keep = "true" *) reg [2:0] fch_c;          // fetching: [0] control, [1] it0 lo, [2] it0 hi + fetch_pc
 (* keep = "true" *) reg [3:0] fv_c;           // fetch_v: [b] bank b read enable + its v1 mask copies, [3] v1
 (* keep = "true" *) reg [15:0] vm0,vm1,vm2;   // v1 copies: bank data mask (32 bits each)
 reg [6:0] uop_pc_r;reg [31:0] iteration;
 reg [6:0] cfg_row;reg [1:0] cfg_bank;reg [511:0] assemble;reg [6:0] write_row;
 reg [6:0] pc;(* keep = "true" *) reg [4:0] pcm0,pcm1,pcm2,pcm3;
 reg [6:0] fetch_pc,pc1;reg [31:0] it0,it1;reg [6:0] sp_q;
 reg [20:0] rc;                                // {next [20:14], tgt [13:7], lid [6:2], halt [1], has [0]} of C
 reg [RW-1:0] rt,rn,pr_c,pr_t,pr_n;
 reg [31:0] q;(* keep = "true" *) reg [31:0] qa,qb,qf;   // visits (= v7 lp1 - 1): state / L1 write lo rows / hi rows / fwd
 reg [31:0] L1q[0:31];reg [31:0] L1v,L1z;       // stored q+1, valid (cleared at start), zero (stored value is 0)
 // registered predicates (kept copies)
 (* keep = "true" *) reg [14:0] sacc_c;        // start accepted this edge
 (* keep = "true" *) reg [14:0] adv_c;         // advance (fetching && !halt(C))
 (* keep = "true" *) reg [18:0] tk_c;          // loop decision
 (* keep = "true" *) reg [2:0] mw_c;           // metadata write this edge
 (* keep = "true" *) reg [3:0] pe1_c;          // prime C (phe == 1, no mw / advance)
 (* keep = "true" *) reg [7:0] pe2_c;          // prime CT / CN (phe == 2)
 (* keep = "true" *) reg [1:0] p0_c,p1_c,p2_c; // effective priming phase (macros 0-1 / 2-3)
 (* keep = "true" *) reg [1:0] fwt_c,fwn_c;    // counter forwarding into the CT / CN reads (lo / hi bits)
 (* keep = "true" *) reg [31:0] stl,sth,snl,snh;   // one-hot lid(CT) / lid(CN) & valid & !zero, lo / hi bit copies
 (* keep = "true" *) reg [31:0] wlc,whc;       // L1 write one-hot (update && lid(C)), lo / hi bit copies
 (* keep = "true" *) reg [15:0] aen_c;         // assembly fragment enables
 reg [31:0] rh_q;reg [3:0] en_w0,en_w1,en_w2,en_ml,en_mh;   // registered row-valid set: one-hot row[4:0], group enables
 // ---------------- current-edge conditions ----------------
 wire sacc=sacc_c[0],adv=adv_c[0],take=tk_c[0],mw=mw_c[0];
 wire nbs=!(busy_r || start_q);
 wire c0=md_q[0] && nbs,c1=md_q[1] && nbs,c2=md_q[2] && nbs,c3=md_q[3] && nbs;
 wire cbad=cfgv_q && (busy_r || start_q || cfg_q[35:32]>4'd3);   // cfg word while busy / start, or an unknown mode
 wire m2_ok=cfg_selected && fragment==4'd0;
 wire m3_ok=cfg_selected && fragment==4'd0 && cfg_q[31:22]==10'd0 && !cfg_q[21] && !cfg_q[18];   // lid < 32
 wire m1ok=c1 && cfg_selected && cfg_bank!=2'd3;
 wire fw=m1ok && fragment==4'd15;                                    // a full programme word is written
 wire mism=start_pc_q!=sp_q;
 wire [1:0] phe=mism ? 2'd0 : ph;
 // ---------------- metadata macros ----------------
 wire [255:0] mo_all;
 wire [63:0] mo0=mo_all[0+:64],mo1=mo_all[64+:64],mo2=mo_all[128+:64],mo3=mo_all[192+:64];
 // CT / CN successor words: take picks the grand-successor pair of the chosen successor (16-bit take copies)
 wire [63:0] nt_w,nn_w;
 for(genvar k=0;k<4;k=k+1)begin:g_ntw
`ifdef OT_COLL_ISS8_MUT_SWAP
  assign nt_w[k*16+:16]=tk_c[3+k] ? mo2[k*16+:16] : mo0[k*16+:16];
  assign nn_w[k*16+:16]=tk_c[7+k] ? mo3[k*16+:16] : mo1[k*16+:16];
`else
  assign nt_w[k*16+:16]=tk_c[3+k] ? mo0[k*16+:16] : mo2[k*16+:16];
  assign nn_w[k*16+:16]=tk_c[7+k] ? mo1[k*16+:16] : mo3[k*16+:16];
`endif
 end
 wire [63:0] mw_d={{32{wdh_c}} & cfg_q[31:0],{32{wdl_c}} & cfg_q[31:0]};
 for(genvar k=0;k<4;k=k+1)begin:g_meta
  wire mwk=mw_c[1+k/2],advk=adv_c[13+k/2],p0k=p0_c[k/2],p1k=p1_c[k/2],p2k=p2_c[k/2];
  reg [6:0] a;reg rce;
  always @*begin
   if(mwk)begin a=cfg_row;rce=1'b1;end
   else if(advk)begin a=(k==0) ? f_tgt(nt_w) : (k==1) ? f_next(nt_w) : (k==2) ? f_tgt(nn_w) : f_next(nn_w);rce=1'b1;end
   else if(p0k)begin a=(k==0) ? start_pc_q : 7'd0;rce=(k==0);end
   else if(p1k)begin a=(k==0) ? f_tgt(mo0) : (k==1) ? f_next(mo0) : 7'd0;rce=(k<2);end
   else if(p2k)begin a=(k==0) ? f_tgt(mo0) : (k==1) ? f_next(mo0) : (k==2) ? f_tgt(mo1) : f_next(mo1);rce=1'b1;end
   else begin a=(k==0) ? r_tgt(pr_t) : (k==1) ? r_next(pr_t) : (k==2) ? r_tgt(pr_n) : r_next(pr_n);rce=1'b1;end
  end
  ot_sram_1rw_128x64_m2_r2c2_p192_mir u_sram(.clk(clk),.ce_in(rce),.we_in(mwk),.addr_in(a),
   .wd_in(mw_d),.w_mask_in({{32{mhi_c[k]}},{32{mlo_c[k]}}}),.rd_out(mo_all[k*64+:64]),
   .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(12'b0));
 end
 // ---------------- programme banks (data <= v1 ? word : 0 = the v7 uop_v mask) ----------------
 wire [1535:0] uop;
 wire [15:0] vmb[0:2];assign vmb[0]=vm0;assign vmb[1]=vm1;assign vmb[2]=vm2;
 for(genvar b=0;b<3;b=b+1)begin:g_mem
  ot_hgi_coll_program_bank128m u_bank(.clk(clk),.read_v(fv_c[b]),.read_row(fetch_pc),.write_v(write_v[b]),
   .write_row(write_row),.write_data(assemble),.vm(vmb[b]),.data(uop[b*512+:512]));
 end
 // ---------------- loop counter reads ----------------
 wire [31:0] inca=qa+32'd1,incb=qb+32'd1,incf=qf+32'd1;
 reg [31:0] aot,aon;
 always @*begin
  aot=32'd0;aon=32'd0;
  for(integer i=0;i<32;i=i+1)begin
   aot=aot | ({{16{sth[i]}},{16{stl[i]}}} & L1q[i]);
   aon=aon | ({{16{snh[i]}},{16{snl[i]}}} & L1q[i]);
  end
 end
 wire [31:0] nft={{16{tk_c[15]}} & incf[31:16],{16{tk_c[16]}} & incf[15:0]};   // forwarded q+1 / 0 (CT read)
 wire [31:0] nfn={{16{tk_c[17]}} & incf[31:16],{16{tk_c[18]}} & incf[15:0]};   // (CN read)
`ifdef OT_COLL_ISS8_MUT_NOFWD
 wire [31:0] l_t=aot,l_n=aon;
`else
 wire [31:0] l_t={fwt_c[1] ? nft[31:16] : aot[31:16],fwt_c[0] ? nft[15:0] : aot[15:0]};
 wire [31:0] l_n={fwn_c[1] ? nfn[31:16] : aon[31:16],fwn_c[0] ? nfn[15:0] : aon[15:0]};
`endif
 wire tt=f_take(r_has(rt),l_t,r_cm1(rt)),tn=f_take(r_has(rn),l_n,r_cm1(rn));
 // ---------------- data next state (per-bit select copies) ----------------
 wire [RW-1:0] rec_nt=f_rec(nt_w),rec_nn=f_rec(nn_w),rec_m0=f_rec(mo0),rec_m1=f_rec(mo1);
 wire [20:0] rc_n;wire [RW-1:0] rt_n,rn_n;wire [31:0] q_n;
 for(genvar i=0;i<21;i=i+1)begin:g_rcn
  assign rc_n[i]=sacc_c[1+i/11] ? pr_c[32+i] : adv_c[1+i/11] ? (tk_c[1+i/11] ? rt[32+i] : rn[32+i]) : rc[i];
 end
 for(genvar i=0;i<RW;i=i+1)begin:g_rtn
  assign rt_n[i]=sacc_c[3+i/14] ? pr_t[i] : adv_c[3+i/14] ? rec_nt[i] : rt[i];
  assign rn_n[i]=sacc_c[7+i/14] ? pr_n[i] : adv_c[7+i/14] ? rec_nn[i] : rn[i];
 end
 for(genvar i=0;i<32;i=i+1)begin:g_qn
  assign q_n[i]=sacc_c[11+i/16] ? 1'b0 : adv_c[11+i/16] ? (tk_c[11+i/16] ? l_t[i] : l_n[i]) : q[i];
 end
 always @(posedge clk)begin
  rc<=rc_n;rt<=rt_n;rn<=rn_n;q<=q_n;qa<=q_n;qb<=q_n;qf<=q_n;sp_q<=start_pc_q;
 end
 for(genvar i=0;i<RW;i=i+1)begin:g_pr
  always @(posedge clk)begin
   if(pe1_c[i/14])pr_c[i]<=rec_m0[i];
   if(pe2_c[i/14])pr_t[i]<=rec_m0[i];
   if(pe2_c[4+i/14])pr_n[i]<=rec_m1[i];
  end
 end
 // loop counters: written at the update edge (registered one-hot write copies); valid cleared by start
 wire [31:0] L1v_n,L1z_n;
 for(genvar i=0;i<32;i=i+1)begin:g_l1
  wire [31:0] wd=(i<16) ? inca : incb;
  assign L1v_n[i]=sacc_c[13+i/16] ? 1'b0 : wlc[i] ? 1'b1 : L1v[i];
  assign L1z_n[i]=wlc[i] ? !tk_c[13+i/16] : L1z[i];
  always @(posedge clk)begin
   if(wlc[i])L1q[i][15:0]<=wd[15:0];
   if(whc[i])L1q[i][31:16]<=wd[31:16];
   L1v[i]<=L1v_n[i];L1z[i]<=L1z_n[i];
  end
 end
 // ---------------- control next state (the v7 sequential block, explicit) ----------------
 wire halt_c=rc[1];
 wire sbad=start_q && !sacc;                                   // a start that faults (busy / cfg / fragment / not ready)
 wire rok;                                                     // row pc fully written (fetch check)
 wire busy_n=sacc ? 1'b1 : (v1 && h1) ? 1'b0 : busy_r;
 wire fch_n=sacc ? 1'b1 : (fch_c[0] && halt_c) ? 1'b0 : fch_c[0];
 wire [1:0] ph_n=mw ? 2'd0 : adv ? (mism ? 2'd0 : ph) : (phe==2'd3 ? 2'd3 : phe+2'd1);
 wire sel_n=c0 ? (cfg_q[7:6]!=2'd3) : cfg_selected;
 wire [1:0] bank_n=c0 ? cfg_q[7:6] : cfg_bank;
 wire [3:0] frag_n=c0 ? 4'd0 : m1ok ? fragment+4'd1 : fragment;
 wire [6:0] pc_n=sacc ? start_pc_q : adv ? (take ? rc[13:7] : rc[20:14]) : pc;
 wire fault_n=fault_r || sbad || (fch_c[0] && !rok) || cbad ||
              (c0 && (fragment!=4'd0 || cfg_q[31:9]!=23'd0 || cfg_q[7:6]==2'd3)) ||
              (c1 && !(cfg_selected && cfg_bank!=2'd3)) || (c2 && !m2_ok) || (c3 && !m3_ok);
 // ---------------- predicates of the NEXT edge (from the next state + the pin inputs) ----------------
 wire mism_x=start_pc!=start_pc_q;
 wire [1:0] phe_x=mism_x ? 2'd0 : ph_n;
 wire nbs_x=!(busy_n || start);
 wire sacc_x=start && !(busy_n || cfg[36] || frag_n!=4'd0) && phe_x==2'd3;
 wire adv_x=fch_n && !rc_n[1];
 wire mw_x=cfg[36] && nbs_x && sel_n && frag_n==4'd0 &&
           (cfg[35:32]==4'd2 || (cfg[35:32]==4'd3 && cfg[31:22]==10'd0 && !cfg[21] && !cfg[18]));
 wire m1ok_x=cfg[36] && cfg[35:32]==4'd1 && nbs_x && sel_n && bank_n!=2'd3;
 wire upd_x=adv_x && rc_n[0];
 wire take_x=sacc ? (r_has(pr_c) && f_take(1'b1,32'd0,r_cm1(pr_c))) : adv ? (take ? tt : tn) : take;
 wire [31:0] oht_x=f_dec(1'b1,r_lid(rt_n)),ohn_x=f_dec(1'b1,r_lid(rn_n)),wr_x=f_dec(upd_x,rc_n[6:2]);
 wire [15:0] aen_x;
 for(genvar f=0;f<16;f=f+1)begin:g_aenx assign aen_x[f]=m1ok_x && frag_n==f; end
 // pc copies for the 128-row fetch check (32 rows each)
 wire [127:0] rowok;wire [3:0] rsel;
 assign rsel[0]=rowok[{2'd0,pcm0}];assign rsel[1]=rowok[{2'd1,pcm1}];
 assign rsel[2]=rowok[{2'd2,pcm2}];assign rsel[3]=rowok[{2'd3,pcm3}];
 assign rok=rsel[pc[6:5]];
 always @(posedge clk)begin
  // free data registers (they hold while reset: written only under reset-cleared enables)
  pc<=pc_n;pcm0<=pc_n[4:0];pcm1<=pc_n[4:0];pcm2<=pc_n[4:0];pcm3<=pc_n[4:0];
  if(c0)begin cfg_row<={cfg_q[8],cfg_q[5:0]};cfg_bank<=cfg_q[7:6];end
  if(fw)write_row<=cfg_row;
  if(fch_c[1])it0[15:0]<=q[15:0];
  if(fch_c[2])begin it0[31:16]<=q[31:16];fetch_pc<=pc;end
  tk_c<={19{take_x}};
  stl<=oht_x & L1v_n & ~L1z_n;sth<=oht_x & L1v_n & ~L1z_n;snl<=ohn_x & L1v_n & ~L1z_n;snh<=ohn_x & L1v_n & ~L1z_n;
  wlc<=wr_x;whc<=wr_x;
  rh_q<=f_dec(1'b1,cfg_row[4:0]);
 end
 for(genvar f=0;f<16;f=f+1)begin:g_asm
  always @(posedge clk) if(aen_c[f])assemble[f*32+:32]<=cfg_q[31:0];
 end
 always @(posedge clk) if(rcp[29])begin pc1<=fetch_pc;it1[15:0]<=it0[15:0];end
 always @(posedge clk) if(rcp[30])it1[31:16]<=it0[31:16];
 // G0: control + pin + delay chains
 reg busy_d1,done_d1,done_d2,start_d1;
 always @(posedge clk or negedge rcp[0])
  if(!rcp[0])begin
   busy_r<=0;done_r<=0;fault_r<=0;v1<=0;uop_v_r<=0;h0<=0;h1<=0;cfg_selected<=0;fragment<=0;write_v<=0;ph<=0;
   cfgv_q<=0;start_q<=0;busy_d1<=0;busy_d2<=0;busy_d3<=0;done_d1<=0;done_d2<=0;done_d3<=0;start_d1<=0;start_d2<=0;start_d3<=0;
  end else begin
   busy_r<=busy_n;done_r<=v1 && h1;fault_r<=fault_n;v1<=fv_c[3];uop_v_r<=v1;
   if(fch_c[0])h0<=halt_c;
   h1<=h0;cfg_selected<=sel_n;fragment<=frag_n;
   write_v<={fw && cfg_bank==2'd2,fw && cfg_bank==2'd1,fw && cfg_bank==2'd0};ph<=ph_n;
   cfgv_q<=cfg[36];start_q<=start;
   busy_d1<=busy_r;busy_d2<=busy_d1;busy_d3<=busy_d2;done_d1<=done_r;done_d2<=done_d1;done_d3<=done_d2;
   start_d1<=start_q;start_d2<=start_d1;start_d3<=start_d2;
  end
 // G1: fetch copies, uop_pc, mode predecode, metadata valid-set enables
 always @(posedge clk or negedge rcp[1])
  if(!rcp[1])begin fch_c<=0;fv_c<=0;uop_pc_r<=0;md_q<=0;en_ml<=0;en_mh<=0;end
  else begin
   fch_c<={3{fch_n}};fv_c<={4{fch_c[0]}};uop_pc_r<=pc1;
   md_q<={cfg[36] && cfg[35:32]==4'd3,cfg[36] && cfg[35:32]==4'd2,cfg[36] && cfg[35:32]==4'd1,cfg[36] && cfg[35:32]==4'd0};
   for(integer g=0;g<4;g=g+1)begin
    en_ml[g]<=c2 && m2_ok && cfg_row[6:5]==g;en_mh[g]<=c3 && m3_ok && cfg_row[6:5]==g;
   end
  end
 // G2/G3: iteration halves
 always @(posedge clk or negedge rcp[2]) if(!rcp[2])iteration[15:0]<=0;else iteration[15:0]<=it1[15:0];
 always @(posedge clk or negedge rcp[3]) if(!rcp[3])iteration[31:16]<=0;else iteration[31:16]<=it1[31:16];
 // G4..G6: bank masks + programme-word valid-set enables
 always @(posedge clk or negedge rcp[4])
  if(!rcp[4])begin vm0<=0;en_w0<=0;end
  else begin vm0<={16{fv_c[0]}};for(integer g=0;g<4;g=g+1)en_w0[g]<=fw && cfg_bank==2'd0 && cfg_row[6:5]==g;end
 always @(posedge clk or negedge rcp[5])
  if(!rcp[5])begin vm1<=0;en_w1<=0;end
  else begin vm1<={16{fv_c[1]}};for(integer g=0;g<4;g=g+1)en_w1[g]<=fw && cfg_bank==2'd1 && cfg_row[6:5]==g;end
 always @(posedge clk or negedge rcp[6])
  if(!rcp[6])begin vm2<=0;en_w2<=0;end
  else begin vm2<={16{fv_c[2]}};for(integer g=0;g<4;g=g+1)en_w2[g]<=fw && cfg_bank==2'd2 && cfg_row[6:5]==g;end
 // G7: start-accept / advance copies
 always @(posedge clk or negedge rcp[7])
  if(!rcp[7])begin sacc_c<=0;adv_c<=0;end
  else begin sacc_c<={15{sacc_x}};adv_c<={15{adv_x}};end
 // G8: metadata write, priming enables, effective phase, forwarding
 always @(posedge clk or negedge rcp[8])
  if(!rcp[8])begin mw_c<=0;pe1_c<=0;pe2_c<=0;p0_c<=2'b11;p1_c<=0;p2_c<=0;fwt_c<=0;fwn_c<=0;end
  else begin
   mw_c<={3{mw_x}};
   pe1_c<={4{!mw_x && !adv_x && phe_x==2'd1}};pe2_c<={8{!mw_x && !adv_x && phe_x==2'd2}};
   p0_c<={2{phe_x==2'd0}};p1_c<={2{phe_x==2'd1}};p2_c<={2{phe_x==2'd2}};
   fwt_c<={2{upd_x && r_lid(rt_n)==rc_n[6:2]}};fwn_c<={2{upd_x && r_lid(rn_n)==rc_n[6:2]}};
  end
 // G31: assembly enables (G29 / G30 gate the pc1 / it1 hold-while-reset, as v7)
 always @(posedge clk or negedge rcp[31]) if(!rcp[31])aen_c<=0;else aen_c<=aen_x;
 // G9..G28: row-valid bits, 20 groups of 32 (set one edge after the cfg word)
 wire [3:0] envec[0:4];
 assign envec[0]=en_w0;assign envec[1]=en_w1;assign envec[2]=en_w2;assign envec[3]=en_ml;assign envec[4]=en_mh;
 wire [127:0] vbits[0:4];
 for(genvar t=0;t<5;t=t+1)begin:g_vt
  for(genvar g=0;g<4;g=g+1)begin:g_vg
   reg [31:0] v;
   always @(posedge clk or negedge rcp[9+t*4+g])
    if(!rcp[9+t*4+g])v<=32'd0;else v<=v | ({32{envec[t][g]}} & rh_q);
   assign vbits[t][g*32+:32]=v;
  end
 end
 assign rowok=vbits[0] & vbits[1] & vbits[2] & vbits[3] & vbits[4];
 // ---------------- outputs ----------------
 assign busy=busy_r | start_q;assign done=done_r;assign fault=fault_r;assign uop_v=uop_v_r;assign uop_pc=uop_pc_r;
 assign tap_iteration=iteration;
 assign tap_steps={uop[1407+:8],uop[1318+:16],uop[1350+:16],uop[1366+:16],uop[1302+:16],uop[1334+:16]};
 always @(posedge clk)uop_d1<=uop;
endmodule

// 512-b programme bank, v8: two ot_sram_1r1w_128x256_m1_r2c2_p192_mir (bits 255:0 / 511:256), macro read at the fetch
// edge, data registered on the next edge AND-masked by 16 v1 copies (one per 32 bits): data = v1 ? word : 0.
module ot_hgi_coll_program_bank128m(
 input wire clk,read_v,write_v,
 input wire [6:0] read_row,write_row,
 input wire [511:0] write_data,
 input wire [15:0] vm,
 output reg [511:0] data
);
 wire [255:0] rq_lo,rq_hi;
 ot_sram_1r1w_128x256_m1_r2c2_p192_mir u_sram_lo(
  .clk(clk),.r_ce_in(read_v),.r_addr_in(read_row),.rd_out(rq_lo),
  .w_ce_in(write_v),.w_addr_in(write_row),.wd_in(write_data[255:0]),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_1r1w_128x256_m1_r2c2_p192_mir u_sram_hi(
  .clk(clk),.r_ce_in(read_v),.r_addr_in(read_row),.rd_out(rq_hi),
  .w_ce_in(write_v),.w_addr_in(write_row),.wd_in(write_data[511:256]),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 wire [511:0] rq={rq_hi,rq_lo};
 for(genvar j=0;j<16;j=j+1)begin:g_m
  always @(posedge clk)data[j*32+:32]<={32{vm[j]}} & rq[j*32+:32];
 end
endmodule
`default_nettype wire
