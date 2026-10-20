`timescale 1ns/1ps
`default_nettype none
// HBM-HCROOT6 2026-10-20 (H.STA.BLK.1, native32): ot_static_program_target_fs -- ot_static_program_target (TGT_PIN 1,
// CAP_CLK 0) with the same ports, the same function and the same edges, rebuilt FANOUT-SAFE (SAFE-DESIGN item 3: no
// driver above 32 loads).  The mapped census of the HC root found the 2^PCW-row installed bitmap behind ~150 of its 282
// drivers above 32: reset_live 2,122 (the two targets' synchronizers merged), program_cfg_we 512/1,024, the write
// address decode 749, the scan_row read mux 486..519, the program_cfg_data enable 496.  Here:
//   * the bitmap is NB = 2^PCW / BW banks of BW = 16 rows; each bank has its own KEPT reset_live copy, its own kept copies of
//     program_cfg_we / install_open, a registered one-hot bank write select and a registered row index (all loaded on
//     the edge that loads program_cfg_we, from G kept copies of the write-accept logic and of the captured address);
//     reset_live is NL kept copies (2 main + one per bank + one per scan counter), each async-cleared by and loaded
//     from one of NM kept metas (<= 16 copies a meta), so assert stays immediate and release is the same edge;
//   * the scan read installed[scan_row] is an AND-OR over registered one-hot bank selects and per-bank registered row
//     indices, held by G kept scan counters that step exactly as scan_row (same next state, own state);
//   * program_cfg_data is loaded every edge from the capture register (its only consumers -- the programme SRAM write
//     stage and the table SRAM -- read it only with program_cfg_we; the value on a write edge is unchanged).
// Every copy is a separate keep_hierarchy instance (Yosys cannot merge equal-D flops across instances).  No edge moves:
// configured, fault, start, programme writes and scans are cycle-identical to ot_static_program_target (bench: the HC
// root SAFE 1 bench uses this module for both targets).
(* keep_hierarchy = 1 *) module ot_spt_kr #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d,
                                                                     output reg [W-1:0] q);
    always @(posedge clk) q <= d;
endmodule
// kept async-clear register (reset copies)
(* keep_hierarchy = 1 *) module ot_spt_kra #(parameter integer W = 1) (input wire clk, rst_n, input wire [W-1:0] d,
                                                                      output reg [W-1:0] q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= {W{1'b0}}; else q <= d;
endmodule
// kept write-accept logic copy: the cv branch's accept condition of ot_static_program_target
(* keep_hierarchy = 1 *) module ot_spt_wacc #(parameter integer PCW = 10) (
    input wire cv, input wire [7:0] target, tid, input wire program_active, scanning, lv,
    input wire [11:0] address, input wire [31:0] hdr, output wire acc
);
    assign acc = cv && target == tid && !(program_active || scanning || lv || {1'b0, address} >= (13'd1 << PCW) ||
                 hdr[31:16] != 16'hc7a1 || hdr[15:0] != {4'b0, address});
endmodule
// kept descriptor-match copy
(* keep_hierarchy = 1 *) module ot_spt_dm (input wire dv, input wire [7:0] target, tid, output wire m);
    assign m = dv && target == tid;
endmodule
// kept copy of the descriptor-accept-starts-a-scan condition (scan_row <= base) of ot_static_program_target
(* keep_hierarchy = 1 *) module ot_spt_sld #(parameter integer PCW = 10) (
    input wire dv, cv, lv, program_active, scanning, validated, input wire [7:0] target, tid,
    input wire [15:0] loops, input wire [12:0] limit, input wire [11:0] base,
    input wire [PCW-1:0] stored_base, input wire [PCW:0] stored_limit, output wire ld
);
    wire bad = program_active || scanning || lv || cv || loops == 0 || limit <= {1'b0, base} || limit > (13'd1 << PCW);
    wire reuse = validated && base == stored_base && limit == stored_limit;
    assign ld = dv && target == tid && !bad && !reuse;
endmodule
// one bitmap bank: BW rows, own reset copy, own program_cfg_we / install_open copies, registered one-hot select + row
(* keep_hierarchy = 1 *) module ot_spt_bank #(parameter integer BW = 16, parameter integer LW = 4) (
    input wire clk, rst_n,              // rst_n = this bank's kept reset_live copy
    input wire pw,                      // == program_cfg_we (kept copy, same edge)
    input wire wsel,                    // == program_cfg_we && program_cfg_addr selects this bank
    input wire [LW-1:0] wrow,           // == program_cfg_addr row within the bank (kept copy)
    input wire dvm,                     // dv && target == tid (kept copy, current edge)
    input wire ssel,                    // == scan_row selects this bank (kept counter copy)
    input wire [LW-1:0] srow,           // == scan_row row within the bank (kept counter copy)
    output wire rd                      // ssel && installed[scan_row]
);
    reg [BW-1:0] inst; reg io;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin inst <= {BW{1'b0}}; io <= 1'b0; end
        else begin
            // ot_static_program_target order: write (if program_cfg_we) then the descriptor branch clears install_open
            if (pw) begin
                if (!io) inst <= wsel ? ({{(BW-1){1'b0}}, 1'b1} << wrow) : {BW{1'b0}};
                else if (wsel) inst[wrow] <= 1'b1;
                io <= 1'b1;
            end
            if (dvm) io <= 1'b0;
        end
    assign rd = ssel && inst[srow];
endmodule
// kept scan counter copy: own scan_row state (same next state as the master), registered selects for NK banks
(* keep_hierarchy = 1 *) module ot_spt_scnt #(parameter integer PCW = 10, parameter integer LW = 4,
                                              parameter integer NK = 8, parameter integer B0 = 0) (
    input wire clk, rst_n,
    input wire ld, input wire [PCW-1:0] base,    // the descriptor accept that starts a scan (scan_row <= base)
    input wire scanning, input wire [PCW:0] scan_limit,   // step = scanning && not the last row (own state)
    output wire [NK-1:0] ssel, output wire [NK*LW-1:0] srow
);
    reg [PCW-1:0] sr;
    wire step = scanning && !({1'b0, sr} + 1'b1 == scan_limit);
    wire [PCW-1:0] nx = ld ? base : step ? sr + 1'b1 : sr;
    always @(posedge clk or negedge rst_n) if (!rst_n) sr <= {PCW{1'b0}}; else sr <= nx;
    genvar k;
    for (k = 0; k < NK; k = k + 1) begin : g_k
        (* keep = 1 *) ot_spt_kra #(.W(1 + LW)) u_c (.clk(clk), .rst_n(rst_n),
            .d({nx[PCW-1:LW] == (PCW - LW)'(B0 + k), nx[LW-1:0]}), .q({ssel[k], srow[k*LW +: LW]}));
    end
endmodule

module ot_static_program_target_fs #(parameter [7:0] TARGET=8'd48,parameter integer PCW=10,parameter integer TGT_PIN=0,
                                     parameter integer CAP_CLK=0)(
    input wire clk,rst_n,
    input wire clk_cap,   // unused (CAP_CLK 0 only)
    input wire [7:0] tgt,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    input wire program_active,
    output reg program_cfg_we,
    output reg [PCW-1:0] program_cfg_addr,
    output reg [255:0] program_cfg_data,
    output reg program_start_v,
    output reg [PCW-1:0] program_start_base,
    output reg [PCW:0] program_start_limit,
    output reg [15:0] program_start_loops,
    output reg configured,fault
);
    localparam integer ROWS=1<<PCW, BW=16, LW=4, NB=ROWS/BW, G=8, NK=NB/G;
    initial if(PCW<8 || PCW>12)$fatal(1,"programme target PCW must be8..12");
    initial if(CAP_CLK!=0)$fatal(1,"ot_static_program_target_fs: CAP_CLK 0 only");
    // ---- reset synchronizer: NM kept metas (async clear from rst_n), kept lives (each async-cleared by AND loaded from
    // its meta: assert is immediate, release one edge after the meta, exactly reset_live); <= 16 lives per meta
    localparam integer NL = 2 + NB + G, NM = (NL + 15) / 16;
    wire [NM-1:0] rmeta; wire [NL-1:0] rl;
    genvar gi;
    for (gi = 0; gi < NM; gi = gi + 1) begin : g_meta
        (* keep = 1, async_reg = "true" *) ot_spt_kra #(.W(1)) u_m (.clk(clk), .rst_n(rst_n), .d(1'b1), .q(rmeta[gi]));
    end
    for (gi = 0; gi < NL; gi = gi + 1) begin : g_live
        (* keep = 1, async_reg = "true" *) ot_spt_kra #(.W(1)) u_l (.clk(clk), .rst_n(rmeta[gi / 16]), .d(rmeta[gi / 16]),
            .q(rl[gi]));
    end
    wire reset_live = rl[0], reset_live2 = rl[1];
    wire [NB-1:0] rlb = rl[2 +: NB]; wire [G-1:0] rlg = rl[2 + NB +: G];
    // ---- capture rung (as ot_static_program_target, CAP_CLK 0)
    reg cv,dv,lv;
    reg [7:0] target;
    reg [7:0] tgt_q; always @(posedge clk) tgt_q<=tgt;
    wire [7:0] tid=(TGT_PIN!=0)?tgt_q:TARGET;
    reg [11:0] address,base;
    reg [PCW-1:0] stored_base;
    reg [255:0] data_q;
    reg [12:0] limit;
    reg [PCW:0] stored_limit;
    reg [15:0] loops,stored_loops;
    reg armed,scanning,validated,missing;
    reg [PCW-1:0] scan_row;
    reg [PCW:0] scan_limit;
    reg [1:0] commit;
    wire launch_ready=armed&&validated&&!scanning&&commit==0&&!program_active&&!fault;
    always @(posedge clk)begin
        target<=cfg_target;address<=cfg_addr;data_q<=cfg_data;
        base<=desc_base;limit<=desc_limit;loops<=desc_loops;
    end
    // kept copies of the captured address (one per bank group): same D (the cfg_addr pins), same edge
    wire [11:0] addr_g [0:G-1];
    for (gi = 0; gi < G; gi = gi + 1) begin : g_addr
        (* keep = 1 *) ot_spt_kr #(.W(12)) u_a (.clk(clk), .d(cfg_addr), .q(addr_g[gi]));
    end
    always @(posedge clk or negedge reset_live2)
        if(!reset_live2)begin cv<=0;dv<=0;lv<=0;end
        else begin cv<=cfg_v;dv<=desc_v;lv<=launch_v;end
    // ---- write accept (G kept copies) and descriptor match (G kept copies)
    wire [G-1:0] wacc, dvm_g;
    for (gi = 0; gi < G; gi = gi + 1) begin : g_wacc
        (* keep = 1 *) ot_spt_wacc #(.PCW(PCW)) u_w (.cv(cv), .target(target), .tid(tid), .program_active(program_active),
            .scanning(scanning), .lv(lv), .address(addr_g[gi]), .hdr(data_q[255:224]), .acc(wacc[gi]));
        (* keep = 1 *) ot_spt_dm u_d (.dv(dv), .target(target), .tid(tid), .m(dvm_g[gi]));
    end
    wire wacc0 = wacc[0];
    wire dvm = dv && target == tid;
    // ---- bitmap banks: program_cfg_we / bank select / row copies loaded on the edge that loads program_cfg_we
    wire [NB-1:0] b_pw, b_ws, b_rd, b_ss; wire [NB*LW-1:0] b_wr, b_sr;
    for (gi = 0; gi < NB; gi = gi + 1) begin : g_bank
        localparam integer GG = gi / NK;
        (* keep = 1 *) ot_spt_kra #(.W(2 + LW)) u_wc (.clk(clk), .rst_n(rlb[gi]),
            .d({wacc[GG], wacc[GG] && addr_g[GG][PCW-1:LW] == (PCW - LW)'(gi), addr_g[GG][LW-1:0]}),
            .q({b_pw[gi], b_ws[gi], b_wr[gi*LW +: LW]}));
        ot_spt_bank #(.BW(BW), .LW(LW)) u_b (.clk(clk), .rst_n(rlb[gi]), .pw(b_pw[gi]), .wsel(b_ws[gi]),
            .wrow(b_wr[gi*LW +: LW]), .dvm(dvm_g[GG]), .ssel(b_ss[gi]), .srow(b_sr[gi*LW +: LW]), .rd(b_rd[gi]));
    end
    wire inst_rd = |b_rd;                                   // == installed[scan_row]
    // ---- descriptor accept / scan step (the master's next-state terms), scan counters (G kept copies)
    wire dv_bad = program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW);
    wire reuse = validated && base==stored_base && limit==stored_limit;
    wire scan_last = {1'b0,scan_row}+1'b1==scan_limit;
    for (gi = 0; gi < G; gi = gi + 1) begin : g_scnt
        wire ld;
        (* keep = 1 *) ot_spt_sld #(.PCW(PCW)) u_ld (.dv(dv), .cv(cv), .lv(lv), .program_active(program_active),
            .scanning(scanning), .validated(validated), .target(target), .tid(tid), .loops(loops), .limit(limit),
            .base(base), .stored_base(stored_base), .stored_limit(stored_limit), .ld(ld));
        (* keep = 1 *) ot_spt_scnt #(.PCW(PCW), .LW(LW), .NK(NK), .B0(gi * NK)) u_s (.clk(clk), .rst_n(rlg[gi]),
            .ld(ld), .base(base[PCW-1:0]), .scanning(scanning), .scan_limit(scan_limit), .ssel(b_ss[gi*NK +: NK]),
            .srow(b_sr[gi*NK*LW +: NK*LW]));
    end
    always @(posedge clk) program_cfg_data<=data_q;         // read only with program_cfg_we (see header)
    always @(posedge clk or negedge reset_live)
        if(!reset_live)begin
            program_cfg_we<=0;program_start_v<=0;configured<=0;fault<=0;
            armed<=0;scanning<=0;validated<=0;missing<=0;
            scan_row<=0;scan_limit<=0;commit<=0;
        end else begin
            program_cfg_we<=0;program_start_v<=0;
            configured<=launch_ready&&!lv&&!((cv||dv)&&target==tid);
            commit<={commit[0],program_cfg_we};
            if(cv && target==tid)begin
                armed<=0;validated<=0;configured<=0;
                if(!wacc0)fault<=1;
                else begin program_cfg_we<=1;program_cfg_addr<=address[PCW-1:0];end
            end
            if(dvm)begin
                armed<=0;validated<=0;configured<=0;
                if(dv_bad)fault<=1;
                else begin
                    stored_base<=base[PCW-1:0];stored_limit<=limit[PCW:0];stored_loops<=loops;
                    armed<=1;missing<=0;
                    if(reuse)begin
                        validated<=1;scanning<=0;
                    end else begin
                        scanning<=1;scan_row<=base[PCW-1:0];scan_limit<=limit[PCW:0];
                    end
                end
            end
            if(scanning)begin
                if(!inst_rd)missing<=1;
                if(scan_last)begin
                    scanning<=0;
                    if(missing || !inst_rd)fault<=1;
                    else validated<=1;
                end else scan_row<=scan_row+1'b1;
            end
            if(lv && armed)begin
                armed<=0;configured<=0;
                if(!launch_ready || cv || dv)fault<=1;
                else begin
                    program_start_v<=1;program_start_base<=stored_base;
                    program_start_limit<=stored_limit;program_start_loops<=stored_loops;
                end
            end
        end
endmodule
`default_nettype wire
