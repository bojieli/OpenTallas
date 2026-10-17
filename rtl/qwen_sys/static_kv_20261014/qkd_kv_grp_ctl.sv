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
