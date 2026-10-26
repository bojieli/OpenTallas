// Physical regrouping (Q-COMPUTE-ELEM r13 2026-10-15): the static controller head side = the exact
// ot_qfd_tt_ctlm_static_parent body minus the ROM tree (u_head + native route + resident relocation +
// loaded stage), one hardened leaf with roots ck_head / ck_me_sched. No logic or edge change; the tree
// return enters as rom_ret_i. Equivalence vs the original parent: physical/qwen_tt_static_cluster_1015.
// r14 (2026-10-15): the two program SRAMs take explicit raw clock entries ck_pm0/ck_pm1 (qfd_tt_ctlm_head_static_rk).
// h7 (Q-ELEM-TTH 2026-10-16): ONE standard-cell root ck_head (the former ck_me_sched entry is merged into it; the die
// already delivers both from one tap). Separate entries carry the die-skew reserve (setup 150/210, hold 100) on every
// sched<->core hop: h6 gate sched->core -429 ps incl. 210 ps reserve. Raw SRAM entries ck_pm0/ck_pm1 stay separate.
// Static successor parent: actual WSRC classification and real native status.
// No native command reaches the ROM tree; native completion comes from endpoint.
// r2 (Q-COMPUTE-ELEM, 2026-10-15, coordinator 12:50 accepted +1 cycle): rom_cmd leaves the head from a register
// (CMDREG=1): h3 gate reg->out -633.9 ps = u_sd_me_i_wcs -> native route + resident relocation (16 levels) -> pin.
// The tree command is one edge later (compiler-visible +1 on every ROM-tree command; ledger row TT.ROMCMD).
// h6 (Q-ELEM-TTH 2026-10-16, RSTN=1): rst_n drove ~481 async-clear flops directly (reset pins are excluded from the
// pin registers; scale-leaf tc1 class: native rst_n capture 357 ps). Now rst_n -> one ot_qfd_rst_stn flop at the pin
// -> the leaf-internal reset rsl (assert asynchronous, release one ck_head edge later; no data/command edge changes).
// h10 (Q-IO-1815 TTH 2026-10-16, RSTREP=1): the h9b gate's single reset station flop drove 481 async clears (380 of
// them the rom_cmd_q datapath register, W face; textbook high_fanout + recovery -154..-197 ps). Three kept station
// copies, each the identical ot_qfd_rst_stn function of the rst_n port (async assert, release RSTN ck_head edges later):
// rsl -> u_head / native route / stage regs (~120 loads), rsl_c0 / rsl_c1 -> the two halves of rom_cmd_q (190 each).
// Release timing identical to the single station (exact, 0 edges).
// h14 (Q-TTH14 2026-10-17, DSEL=1): the decode adds' DYN operand is a register per FIFO head word, written with the
// word (dyn is fixed in S_RUN); removes the dyn select + its wire from the h13 worst path (dyn -> obase add). Exact, 0 edges.
// h15 (Q-TTH15 2026-10-17, H15=1, coordinator-approved): PWCP program-SRAM write-pin copies per macro x pin edge, FQWE
// registered one-hot FIFO write enables + prog_q capture-enable slice copies, OINC o_cnt <= o_cnt1 with a KS incrementer,
// DTIL me_tiles DPRE/DSEL, SLATE fixed-issue sched_q late start select, AMWC am_wins kept copies, RRH 4 more reset copies
// for the head-fill slices.  All exact, 0 edges (+~560 flops).  Kit qfd_tt_head_static_h15: mirrored (MY) macros, E home band.
// h17 (Q-H16C 2026-10-18, STAGE_ME, default 0 = as built): QLB-PROG G-C3 one-image-per-epoch.  STAGE_ME = 1: the ROM
// relocation stage (loaded_stage / command_stage) is the RUNNING stage, latched from the new stage_start / stage ports
// (the parent's registered dh stage start + stage, qfd_tt_ctlm_dv s_start / s_stage) instead of the image CALS word
// (PW1017 [17:12]; as built every one of the 36 layers would read the weights of the one layer the image names).
// Edges: stage_start / stage and h_start enter through the same pin registers, so loaded_stage is valid on the edge
// h_start reaches u_head, exactly as the soft parent (HARD_HR 0) latch.  STAGE_ME = 0: the stage ports are ignored.
module ot_qfd_tt_ctlm_static_hr #(parameter integer CMDREG = 1, parameter integer RSTN = 1, parameter integer SREG = 1, parameter integer DPRE = 1,
    parameter integer RSTREP = 1, parameter integer DSEL = 1,
    // h15 (Q-TTH15 10-17): PWCP / FQWE / OINC / DTIL / SLATE / AMWC / RRH, see qfd_tt_ctlm_head_static_rk (all exact, 0 edges)
    parameter integer H15 = 1,
    parameter integer STAGE_ME = 0) (
    input wire [94:0] rom_ret_i,
    input wire cp_active,output wire [55:0] cp,
    output wire me_image_ready,output wire [75:0] program_obs,
    output wire layer_context_v,output wire [17:0] native_tok,native_pos,
    output wire [379:0] rom_cmd,
    output wire [5:0] command_stage,
    output wire [379:0] native_cmd,
    output wire [15:0] me_observe,
    input wire [94:0] native_ret,
    input wire ck_head,
    input wire ck_pm0, ck_pm1,   // r14: raw program-SRAM clock entries (same PLL phase as ck_head)
    input wire  rst_n,
    input wire  h_start,
    input wire  stage_start,      // h17 STAGE_ME: running-stage start (unused when STAGE_ME = 0)
    input wire [5:0] stage,       // h17 STAGE_ME: running stage
    input wire [18-1:0] token,
    input wire [18-1:0] pos,
    input wire [11:0] prog_base,
    input wire  pw_v,
    input wire [9:0] pw_addr,
    input wire [63:0] pw_data,
    input wire [24-1:0] x_oacc,
    input wire  x_oidle,
    input wire [15:0] x_oprog,
    input wire [15:0] x_orows,
    input wire  kv_ok,
    input wire  kv_write_drained,
    input wire  me_mem_ok,
    output wire  m_fin_o,
    output wire [18-1:0] m_fidx_o,
    output wire [31:0] m_fval_o,
    output wire  kvd_v,
    output wire [24-1:0] kvd_wbase,
    output wire [24-1:0] kvd_ts,
    output wire [24-1:0] kvd_ks,
    output wire [24-1:0] kvd_js,
    output wire [24-1:0] kvd_wcs,
    output wire [3:0] kvd_split,
    output wire [2:0] kvd_jsh,
    output wire [18-1:0] kvd_tiles,
    output wire [18-1:0] kvd_k,
    output wire [18-1:0] kvd_nout,
    output wire  kvd_kindk,
    output wire [18-1:0] kvd_pos,
    output wire  me_clk_en,
    output wire  c_fault
);
    wire rsl, rsl_c0, rsl_c1;
    generate if (RSTREP != 0 && RSTN != 0) begin : g_rrep
      (* keep = "true", dont_touch = "true" *) reg [RSTN-1:0] r0;
      (* keep = "true", dont_touch = "true" *) reg [RSTN-1:0] r1;
      (* keep = "true", dont_touch = "true" *) reg [RSTN-1:0] r2;
      always @(posedge ck_head or negedge rst_n) if (!rst_n) r0 <= {RSTN{1'b0}}; else r0 <= {r0, 1'b1};
      always @(posedge ck_head or negedge rst_n) if (!rst_n) r1 <= {RSTN{1'b0}}; else r1 <= {r1, 1'b1};
      always @(posedge ck_head or negedge rst_n) if (!rst_n) r2 <= {RSTN{1'b0}}; else r2 <= {r2, 1'b1};
      assign rsl = r0[RSTN-1]; assign rsl_c0 = r1[RSTN-1]; assign rsl_c1 = r2[RSTN-1];
    end else begin : g_rone
      ot_qfd_rst_stn #(.D(RSTN)) u_rst_stn (.clk(ck_head), .rst_n(rst_n), .rst_q(rsl));
      assign rsl_c0 = rsl; assign rsl_c1 = rsl;
    end endgenerate
    wire [379:0] cmd;
    wire [94:0] ret,rom_ret;
    assign rom_ret=rom_ret_i;
    wire [379:0] local_rom_cmd;
    wire head_fault,relocation_fault;
    reg [5:0] loaded_stage;
    reg relocation_sticky;
    always @(posedge ck_head or negedge rsl)
      if(!rsl)begin loaded_stage<=0;relocation_sticky<=0;end
      else begin
        if (STAGE_ME != 0) begin if (stage_start) loaded_stage<=stage; end
        else if(pw_v && pw_addr==1017 && pw_data[63:32]==32'h43414c53)
          loaded_stage<=pw_data[17:12];
        if(relocation_fault)relocation_sticky<=1;
      end
    assign command_stage=loaded_stage;
    wire [379:0] rom_cmd_c;
    ot_qwen_tp8_rom_relocate u_resident_relocation(
      .in_cmd(local_rom_cmd),.in_stage(loaded_stage),.out_cmd(rom_cmd_c),.fault(relocation_fault));
    generate if (CMDREG != 0) begin : g_cmdreg
      reg [379:0] rom_cmd_q;
      always @(posedge ck_head or negedge rsl_c0)
        if (!rsl_c0) rom_cmd_q[189:0] <= 190'd0; else rom_cmd_q[189:0] <= rom_cmd_c[189:0];
      always @(posedge ck_head or negedge rsl_c1)
        if (!rsl_c1) rom_cmd_q[379:190] <= 190'd0; else rom_cmd_q[379:190] <= rom_cmd_c[379:190];
      if (CMDREG >= 2) begin : g_cmdreg2
        // h12 (Q-IO-1815 TTH 2026-10-17, CMDREG=2): a second command register. h11c gate: the relocation adder
        // (kvd field -> code_sum) plus the E->W crossing to rom_cmd_q (237 ps of wire repeaters) is the worst path
        // (-208.7 @770). rom_cmd_q now sits by the adder; rom_cmd_q2 is the W-face launch register. Exact function,
        // +1 edge on every ROM-tree command (ledger TT.ROMCMD2, compiler-visible).
        reg [379:0] rom_cmd_q2;
        always @(posedge ck_head or negedge rsl_c0)
          if (!rsl_c0) rom_cmd_q2[189:0] <= 190'd0; else rom_cmd_q2[189:0] <= rom_cmd_q[189:0];
        always @(posedge ck_head or negedge rsl_c1)
          if (!rsl_c1) rom_cmd_q2[379:190] <= 190'd0; else rom_cmd_q2[379:190] <= rom_cmd_q[379:190];
        assign rom_cmd = rom_cmd_q2;
      end else begin : g_cmdreg1
        assign rom_cmd = rom_cmd_q;
      end
    end else begin : g_cmdwire
      assign rom_cmd = rom_cmd_c;
    end endgenerate
    assign c_fault=head_fault|relocation_sticky;
    ot_qfd_native_cmd_route u_native_route (
      .clk(ck_head),.rst_n(rsl),.cmd(cmd),.rom_ret(rom_ret),.native_ret(native_ret),
      .rom_cmd(local_rom_cmd),.native_cmd(native_cmd),.ret(ret));
    qfd_tt_ctlm_head_static_rk #(.SREG(SREG),.DPRE(DPRE),.DSEL(DSEL),.PWCP(H15),.FQWE(H15),.OINC(H15),.DTIL(H15),.SLATE(H15),
        .AMWC(H15),.RRH(H15)) u_head (
        .me_observe(me_observe),.cp_active(cp_active),.cp(cp),
        .me_image_ready(me_image_ready),.program_obs(program_obs),
        .layer_context_v(layer_context_v),.native_tok(native_tok),.native_pos(native_pos),

        .clk(ck_head),
        .ck_pm({ck_pm1,ck_pm0}),
        .ck_sched(ck_head),   // h7: the static schedule store shares the ck_head root (die ties them)
        .rst_n(rsl),
        .h_start(h_start),
        .token(token),
        .pos(pos),
        .prog_base(prog_base),
        .pw_v(pw_v),
        .pw_addr(pw_addr),
        .pw_data(pw_data),
        .x_oacc(x_oacc),
        .x_oidle(x_oidle),
        .x_oprog(x_oprog),
        .x_orows(x_orows),
        .kv_ok(kv_ok),
        .kv_write_drained(kv_write_drained),
        .me_mem_ok(me_mem_ok),
        .m_fin_o(m_fin_o),
        .m_fidx_o(m_fidx_o),
        .m_fval_o(m_fval_o),
        .me_clk_en(me_clk_en),
        .c_fault(head_fault),
        .kvd_v(kvd_v),
        .kvd_wbase(kvd_wbase),
        .kvd_ts(kvd_ts),
        .kvd_ks(kvd_ks),
        .kvd_js(kvd_js),
        .kvd_wcs(kvd_wcs),
        .kvd_split(kvd_split),
        .kvd_jsh(kvd_jsh),
        .kvd_tiles(kvd_tiles),
        .kvd_k(kvd_k),
        .kvd_nout(kvd_nout),
        .kvd_kindk(kvd_kindk),
        .kvd_pos(kvd_pos),
        .cmd(cmd),.ret(ret));
endmodule
