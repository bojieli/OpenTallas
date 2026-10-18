`timescale 1ns/1fs
// KVJ-D 2026-10-17 (kv_static_join_plan item 7, "per-group control tile, x32, hardened once"): every core -> HBM
// control crossing of ONE landing group in one tile beside its landing segment / front calendar:
//   u_phase  qkd_static_kv_phase_launch (ctrl_go / kgo / vgo + ctx_t / epoch / layer to the group's HBM side),
//   u_drain  qkd_static_kv_drain_guard4 (the group's 4 PC ctrl / front / ring idle + fault observations, core owner),
//   u_cdc[0] qkd_static_kv_boot_cdc HAS_SEAL 0 -> the group's front calendar (qkd_kv_front_cal cfg),
//   u_cdc[1..4] qkd_static_kv_boot_cdc HAS_SEAL 1 -> the group's 4 pc_path cal_cfg / cal_seal.
// Wires only around the unchanged ROLES RTL: no logic, no added edge.  Boot CDC buses are packed by index
// (cdc i = bits [i*W +: W]).  Phase-profile parameters (PH0 / SAFE_*_U / META_HOLD_CORE) are compiler-priced
// (plan item 8); the defaults are the component bench's legal profile, not a die measurement.
// GRPCTL-2 2026-10-17 (coordinator review 0co: hrst_n port fanout 387): the hrst_n port drives ONLY u_hrr, an
// ot_rst_relay on hck (2-flop synchroniser + one registered relay flop per region, asynchronous assert, synchronous
// release 3 hck edges after the port).  Region i < 5 resets boot CDC i's HBM side (its ~78 sink / state flops and its
// FIFO read-domain reset), region 5 the phase launch's HBM side, so no port net spans the tile and each relay flop sits
// by its own region.  Reset only: no datapath edge, no cycle on any functional path.
module qkd_kv_grp_ctl #(parameter integer PH0=0, SAFE_LOW_U=200, SAFE_HIGH_U=600, META_HOLD_CORE=8, MUT=0) (
    input  wire          ck, rst_n, hck, hrst_n,
    // phase launch (core in, HBM out)
    input  wire          ctrl_go, kgo, vgo,
    input  wire [13:0]   ctx_t, input wire [15:0] epoch, input wire [5:0] layer,
    output wire          ctrl_go_h, kgo_h, vgo_h,
    output wire [13:0]   ctx_t_h, output wire [15:0] epoch_h, output wire [5:0] layer_h,
    output wire          ph_fault_core, ph_idle_core, ph_fault_hbm, ph_idle_hbm,
    // drain guard (core owner of the group's asynchronous observations)
    input  wire [3:0]    ctrl_idle_core, ring_idle_core,
    input  wire [3:0]    ctrl_idle_hbm, front_idle_hbm, ring_idle_hbm,
    input  wire [3:0]    ctrl_fault_core, ctrl_completion_fault_core, ctrl_intake_fault_core, ring_fault_core,
    input  wire [3:0]    ctrl_fault_hbm, ctrl_output_fault_hbm, ctrl_calendar_fault_hbm, ring_fault_hbm,
    input  wire [3:0]    front_fault_overflow_hbm, front_fault_go_hbm, front_hold_hbm,
    input  wire          upstream_quiet, upstream_fault,
    output wire          drained, drain_fault,
    // 5 boot CDCs (core in, HBM out): 0 = front calendar, 1..4 = pc_path calendars
    input  wire [4:0]    cfg_we, input wire [39:0] cfg_addr, input wire [319:0] cfg_data, input wire [4:0] cfg_last,
    output wire [4:0]    sink_we, output wire [39:0] sink_addr, output wire [319:0] sink_data, output wire [4:0] sink_seal,
    output wire [4:0]    applied_hbm, boot_fault_hbm, boot_fault_core
);
    wire [5:0] hrst_r;
    ot_rst_relay #(.REGIONS(6), .SYNC_STAGES(2), .TREE_STAGES(1)) u_hrr (.clk(hck), .rst_n_in(hrst_n), .rst_n(hrst_r));
    qkd_static_kv_phase_launch #(.PH0(PH0), .SAFE_LOW_U(SAFE_LOW_U), .SAFE_HIGH_U(SAFE_HIGH_U),
                                 .META_HOLD_CORE(META_HOLD_CORE), .MUT((MUT==2)?3:0)) u_phase (
        .ck(ck), .rst_n(rst_n), .hck(hck), .hrst_n(hrst_r[5]), .ctrl_go(ctrl_go), .kgo(kgo), .vgo(vgo),
        .ctx_t(ctx_t), .epoch(epoch), .layer(layer), .ctrl_go_h(ctrl_go_h), .kgo_h(kgo_h), .vgo_h(vgo_h),
        .ctx_t_h(ctx_t_h), .epoch_h(epoch_h), .layer_h(layer_h),
        .fault_core(ph_fault_core), .fault_hbm(ph_fault_hbm), .idle_core(ph_idle_core), .idle_hbm(ph_idle_hbm));
    qkd_static_kv_drain_guard4 #(.MUT(0)) u_drain (
        .ck(ck), .rst_n(rst_n), .ctrl_idle_core(ctrl_idle_core), .ring_idle_core(ring_idle_core),
        .ctrl_idle_hbm(ctrl_idle_hbm), .front_idle_hbm(front_idle_hbm), .ring_idle_hbm(ring_idle_hbm),
        .ctrl_fault_core(ctrl_fault_core), .ctrl_completion_fault_core(ctrl_completion_fault_core),
        .ctrl_intake_fault_core(ctrl_intake_fault_core), .ring_fault_core(ring_fault_core),
        .ctrl_fault_hbm(ctrl_fault_hbm), .ctrl_output_fault_hbm(ctrl_output_fault_hbm),
        .ctrl_calendar_fault_hbm(ctrl_calendar_fault_hbm), .ring_fault_hbm(ring_fault_hbm),
        .front_fault_overflow_hbm(front_fault_overflow_hbm), .front_fault_go_hbm(front_fault_go_hbm),
        .front_hold_hbm(front_hold_hbm), .upstream_quiet(upstream_quiet), .upstream_fault(upstream_fault),
        .drained(drained), .fault(drain_fault));
    genvar i;
    generate for (i = 0; i < 5; i = i + 1) begin : u_cdc
        qkd_static_kv_boot_cdc #(.HAS_SEAL(i == 0 ? 0 : 1), .MUT((MUT==1 && i==2) ? 1 : 0)) u (
            .ck(ck), .rst_n(rst_n), .hck(hck), .hrst_n(hrst_r[i]),
            .cfg_we(cfg_we[i]), .cfg_addr(cfg_addr[8*i +: 8]), .cfg_data(cfg_data[64*i +: 64]), .cfg_last(cfg_last[i]),
            .sink_we(sink_we[i]), .sink_addr(sink_addr[8*i +: 8]), .sink_data(sink_data[64*i +: 64]), .sink_seal(sink_seal[i]),
            .applied_hbm(applied_hbm[i]), .fault_core(boot_fault_core[i]), .fault_hbm(boot_fault_hbm[i]));
    end endgenerate
endmodule

// KV-NATIVE 2026-10-17 successor of qkd_kv_grp_ctl (routed native audit FAIL, claude/native-batch-1017 029f539c5,
// results/arch/native_batch_1017/native_batch_audit.json, view qkd_kv_grp_ctl-g2-95edd890c: capture cfg_we[0..4]
// 335.6-349.4, rst_n 214.9, ctrl_go 192.9 > 190 -- cfg_we went straight from the pin into each boot FIFO's wr_valid gate
// (cfg_we & !sealed & !fault -> write pointer + 64-b data enables), rst_n fanned out raw, ctrl_go fed idle_core logic).
// Every CORE-domain input now lands in one pin flop first (one kept flop per bit; rst_n -> rst_q, a plain flop whose Q
// is the core-side reset of the unchanged qkd_kv_grp_ctl inside).  hck-domain hrst_n is unchanged (already ot_rst_relay).
// Contract: this tile == qkd_kv_grp_ctl with every core-domain input (rst_n included) delayed by exactly ONE ck edge.
// The compiler launches ctrl_go / kgo / vgo / ctx_t / epoch / layer and the boot cfg_* words one core edge earlier, so
// the toggle and every HBM-side event keep their absolute edges; SAFE_* are unchanged.  PH0 keeps its definition (q at
// the first edge with the phase launch's internal rn active); that edge is now one ck edge later relative to the rst_n
// pin, which the die's reset / PLL phase-origin proof must state.  HBM-side and core-side outputs are cycle-identical
// (tb_kv_grp_ctl_p: old fed the same stimulus one ck edge later).  Drain observations are registered too (uniform shift;
// on the *_hbm observations the pin flop is one more synchroniser stage in front of the drain guard's own two).
// MUT (bench only): 1 / 2 as qkd_kv_grp_ctl; 3 cfg_we bypasses its pin flop (data still registered).
module qkd_kv_grp_ctl_p #(parameter integer PH0=0, SAFE_LOW_U=200, SAFE_HIGH_U=600, META_HOLD_CORE=8, MUT=0) (
    input  wire          ck, rst_n, hck, hrst_n,
    input  wire          ctrl_go, kgo, vgo,
    input  wire [13:0]   ctx_t, input wire [15:0] epoch, input wire [5:0] layer,
    output wire          ctrl_go_h, kgo_h, vgo_h,
    output wire [13:0]   ctx_t_h, output wire [15:0] epoch_h, output wire [5:0] layer_h,
    output wire          ph_fault_core, ph_idle_core, ph_fault_hbm, ph_idle_hbm,
    input  wire [3:0]    ctrl_idle_core, ring_idle_core,
    input  wire [3:0]    ctrl_idle_hbm, front_idle_hbm, ring_idle_hbm,
    input  wire [3:0]    ctrl_fault_core, ctrl_completion_fault_core, ctrl_intake_fault_core, ring_fault_core,
    input  wire [3:0]    ctrl_fault_hbm, ctrl_output_fault_hbm, ctrl_calendar_fault_hbm, ring_fault_hbm,
    input  wire [3:0]    front_fault_overflow_hbm, front_fault_go_hbm, front_hold_hbm,
    input  wire          upstream_quiet, upstream_fault,
    output wire          drained, drain_fault,
    input  wire [4:0]    cfg_we, input wire [39:0] cfg_addr, input wire [319:0] cfg_data, input wire [4:0] cfg_last,
    output wire [4:0]    sink_we, output wire [39:0] sink_addr, output wire [319:0] sink_data, output wire [4:0] sink_seal,
    output wire [4:0]    applied_hbm, boot_fault_hbm, boot_fault_core
);
    // ---- core-domain pin flops (no reset: pure one-edge delay of the pin; the reset itself is rst_q) ----
    (* keep = "true", dont_touch = "true" *) reg rst_q;
    (* keep = "true" *) reg go_q, kgo_q, vgo_q;
    (* keep = "true" *) reg [35:0] meta_q;
    (* keep = "true" *) reg [4:0] we_q, last_q;
    reg [39:0] addr_q; reg [319:0] data_q;
    (* keep = "true" *) reg [7:0]  ic_q;                       // ctrl_idle_core, ring_idle_core
    (* keep = "true" *) reg [11:0] ih_q;                       // ctrl / front / ring idle_hbm
    (* keep = "true" *) reg [15:0] fc_q;                       // 4 core fault vectors
    (* keep = "true" *) reg [27:0] fh_q;                       // 7 hbm fault / hold vectors
    (* keep = "true" *) reg [1:0]  up_q;
    always @(posedge ck) begin
        rst_q <= rst_n;
        go_q <= ctrl_go; kgo_q <= kgo; vgo_q <= vgo; meta_q <= {ctx_t, epoch, layer};
        we_q <= cfg_we; last_q <= cfg_last; addr_q <= cfg_addr; data_q <= cfg_data;
        ic_q <= {ring_idle_core, ctrl_idle_core};
        ih_q <= {ring_idle_hbm, front_idle_hbm, ctrl_idle_hbm};
        fc_q <= {ring_fault_core, ctrl_intake_fault_core, ctrl_completion_fault_core, ctrl_fault_core};
        fh_q <= {front_hold_hbm, front_fault_go_hbm, front_fault_overflow_hbm, ring_fault_hbm, ctrl_calendar_fault_hbm,
                 ctrl_output_fault_hbm, ctrl_fault_hbm};
        up_q <= {upstream_fault, upstream_quiet};
    end
    wire [4:0] we_g = (MUT == 3) ? cfg_we : we_q;
    qkd_kv_grp_ctl #(.PH0(PH0), .SAFE_LOW_U(SAFE_LOW_U), .SAFE_HIGH_U(SAFE_HIGH_U), .META_HOLD_CORE(META_HOLD_CORE),
                     .MUT((MUT == 3) ? 0 : MUT)) u_g (
        .ck(ck), .rst_n(rst_q), .hck(hck), .hrst_n(hrst_n),
        .ctrl_go(go_q), .kgo(kgo_q), .vgo(vgo_q), .ctx_t(meta_q[35:22]), .epoch(meta_q[21:6]), .layer(meta_q[5:0]),
        .ctrl_go_h(ctrl_go_h), .kgo_h(kgo_h), .vgo_h(vgo_h), .ctx_t_h(ctx_t_h), .epoch_h(epoch_h), .layer_h(layer_h),
        .ph_fault_core(ph_fault_core), .ph_idle_core(ph_idle_core), .ph_fault_hbm(ph_fault_hbm), .ph_idle_hbm(ph_idle_hbm),
        .ctrl_idle_core(ic_q[3:0]), .ring_idle_core(ic_q[7:4]),
        .ctrl_idle_hbm(ih_q[3:0]), .front_idle_hbm(ih_q[7:4]), .ring_idle_hbm(ih_q[11:8]),
        .ctrl_fault_core(fc_q[3:0]), .ctrl_completion_fault_core(fc_q[7:4]), .ctrl_intake_fault_core(fc_q[11:8]),
        .ring_fault_core(fc_q[15:12]),
        .ctrl_fault_hbm(fh_q[3:0]), .ctrl_output_fault_hbm(fh_q[7:4]), .ctrl_calendar_fault_hbm(fh_q[11:8]),
        .ring_fault_hbm(fh_q[15:12]), .front_fault_overflow_hbm(fh_q[19:16]), .front_fault_go_hbm(fh_q[23:20]),
        .front_hold_hbm(fh_q[27:24]),
        .upstream_quiet(up_q[0]), .upstream_fault(up_q[1]), .drained(drained), .drain_fault(drain_fault),
        .cfg_we(we_g), .cfg_addr(addr_q), .cfg_data(data_q), .cfg_last(last_q),
        .sink_we(sink_we), .sink_addr(sink_addr), .sink_data(sink_data), .sink_seal(sink_seal),
        .applied_hbm(applied_hbm), .boot_fault_hbm(boot_fault_hbm), .boot_fault_core(boot_fault_core));
endmodule
