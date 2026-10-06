`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_capture -- S81 die return capture core (CLAUDE S81-PH, 2026-10-06).  Contract:
// results/rtl/s81_ph_20261006/capture/contract.json.
//
// Stream side (clk): the UNCHANGED ot_dsrom_rd64_vm_capture (ENABLE, ROOTS 128, CAPACITY 1, VM_AW 19,
// VM_ALWAYS_ACCEPT 1) with the canonical S81 per-root quota (ot_dsrom_s81_phase_capture_profile), exactly as the
// spine instantiates it (rtl/dsrom_sys/s81_capture_parent/ot_v41_spine_w17w10.sv).  Its VM is the serial-domain
// vector memory behind one ot_ratio_cdc_fifo per root (DEPTH LD): vm_accept[r] = vm_valid[r] & w_rdy[r]; with
// ALWAYS_ACCEPT a full crossing is a capture fault (fail closed, never a dropped write).  The root bf16 is the
// ot_v41_ret_root RNE of the fp32 ({1'b0, fp32} + 0x7FFF + fp32[16], bits [31:16]), recomputed here bit for bit.
// Phase words come from the VM through the gather (in order with the rows); a phase word that the capture cannot
// accept (phase_ready low) is a protocol fault: the VM issues the next phase only after it saw `drained`.
// Serial side (ckv): per root up to two rows {v, addr19, data32} a serial cycle; status lane {live, idle, drained, fault, phase10, identity47}.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_capture #(
    parameter integer NR = 128,
    parameter integer LD = 4                 // per-root crossing depth (power of two)
) (
    input  wire             clk,
    input  wire             rst_n,           // stream, synchronised
    input  wire             ckv,
    input  wire             rsv_n,           // serial, synchronised
    // from the gather (registered by the caller)
    input  wire [NR-1:0]    row_v,
    input  wire [NR*52-1:0] row_d,           // {e, pos3, row16, fp32}
    input  wire             ctl_v,
    input  wire [158:0]     ctl_d,           // f_vm[159:1]
    input  wire             g_fault, g_busy, g_live,
    // serial side, registered here
    output reg  [2*NR-1:0]  w_v,             // per root: {second row valid, first row valid}
    output reg  [NR*102-1:0] w_d,            // per root: {row1 {data32, addr19}, row0 {data32, addr19}}
    output reg  [63:0]      st                // {busy, live, ..., identity47, phase10, fault, drained, idle, live}
);
    // ---------------- phase / reset words
    wire [1:0]  kind     = ctl_d[1:0];
    wire [46:0] identity = ctl_d[48:2];
    wire [9:0]  phase_id = ctl_d[58:49];
    wire [29:0] obase    = ctl_d[88:59];
    wire [29:0] ops      = ctl_d[118:89];
    wire [2:0]  np       = ctl_d[121:119];
    wire [1:0]  fmt      = ctl_d[123:122];
    wire [15:0] rsplit   = ctl_d[139:124];
    wire        fp32_lo  = ctl_d[140];
    wire        fp32_hi  = ctl_d[141];
    wire [15:0] prows    = ctl_d[157:142];
    wire        rreq_lvl = ctl_d[158];
    reg reset_request, proto_fault;
    wire phase_v = ctl_v && kind == 2'd0;
    wire phase_ready, phase_live, phase_idle, phase_drained, cfault;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin reset_request <= 1'b0; proto_fault <= 1'b0; end
        else begin
            if (ctl_v && kind == 2'd1) reset_request <= rreq_lvl;
            if (phase_v && !phase_ready) proto_fault <= 1'b1;
        end
    wire [128*19-1:0] quota;
    ot_dsrom_s81_phase_capture_profile #(.ENABLE(1)) u_prof (.phase_rows(prows), .phase_np(np), .root_returns(quota));
    // ---------------- rows
    wire [NR-1:0] r_e;
    wire [NR*16-1:0] r_row, r_bf;
    wire [NR*3-1:0] r_pos;
    wire [NR*32-1:0] r_fp;
    wire [NR-1:0] vm_valid, vm_accept, crdy;
    wire [NR*30-1:0] vm_addr;
    wire [NR*32-1:0] vm_data;
    genvar g;
    generate for (g = 0; g < NR; g = g + 1) begin : g_in
        wire [51:0] d = row_d[52*g +: 52];
        wire [32:0] rb = {1'b0, d[31:0]} + 33'h7FFF + {32'd0, d[16]};
        assign r_fp[32*g +: 32] = d[31:0];
        assign r_row[16*g +: 16] = d[47:32];
        assign r_pos[3*g +: 3] = d[50:48];
        assign r_e[g] = d[51];
`ifdef S81PH_MUTANT_BF16_TRUNC
        assign r_bf[16*g +: 16] = d[31:16];
`else
        assign r_bf[16*g +: 16] = rb[31:16];
`endif
        assign vm_accept[g] = vm_valid[g] & crdy[g];
    end endgenerate
    ot_dsrom_rd64_vm_capture #(.ENABLE(1), .ROOTS(NR), .CAPACITY(1), .VM_AW(19), .VM_ALWAYS_ACCEPT(1)) u_cap (
        .clk(clk), .rst_n(rst_n), .reset_request(reset_request),
        .phase_valid(phase_v), .phase_ready(phase_ready), .phase_identity(identity), .phase_id(phase_id),
        .phase_root_rows(quota), .phase_obase(obase), .phase_ops(ops), .phase_np(np), .phase_fmt(fmt),
        .phase_rsplit(rsplit), .phase_fp32_low(fp32_lo), .phase_fp32_high(fp32_hi),
        .r_valid(row_v), .r_error(r_e), .r_row(r_row), .r_bf16(r_bf), .r_pos(r_pos), .r_fp32(r_fp),
        .vm_valid(vm_valid), .vm_accept(vm_accept), .vm_addr(vm_addr), .vm_data(vm_data), .vm_row(), .vm_pos(),
        .held_identity(), .held_phase(), .phase_live(phase_live), .phase_idle(phase_idle),
        .phase_drained(phase_drained), .fault(cfault));
    reg [46:0] h_id; reg [9:0] h_ph;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin h_id <= 47'd0; h_ph <= 10'd0; end
        else if (phase_v && phase_ready) begin h_id <= identity; h_ph <= phase_id; end
    // ---------------- per-root pair packer + crossing (stream -> serial)
    // A root can return one row every stream cycle for a whole phase (the field finishes rows in bursts: the
    // retained I66 trace writes 576 rows in 6 edges, 128 roots at once).  The serial VM takes one crossing word a
    // serial cycle per root (0.75 a stream cycle), so each word carries up to TWO rows (1.5 rows a stream cycle >= 1):
    // a 4-row hold per root packs whatever is waiting when the crossing has room.  Hold overflow is a capture
    // fault (fail closed); the bench shows it never fills under back-to-back bursts.
    wire [NR-1:0] cv;
    wire [NR*103-1:0] cd;
    (* keep *) reg [7:0] rsv_c;
    (* keep *) reg [7:0] rst_cs;
    reg [NR-1:0] hovf;
    always @(posedge ckv or negedge rsv_n) if (!rsv_n) rsv_c <= 8'd0; else rsv_c <= 8'hFF;
    always @(posedge clk or negedge rst_n) if (!rst_n) rst_cs <= 8'd0; else rst_cs <= 8'hFF;
    generate for (g = 0; g < NR; g = g + 1) begin : g_x
        reg [50:0] h [0:3];
        reg [1:0] hr, hw;
        reg [2:0] hc;
        wire wr;
        wire [50:0] din = {vm_data[32*g +: 32], vm_addr[30*g +: 19]};
        wire [2:0] npop = (!wr || hc == 3'd0) ? 3'd0 : (hc == 3'd1) ? 3'd1 : 3'd2;
        assign crdy[g] = (hc - npop) < 3'd4;          // room for this cycle's row after this cycle's pops
        always @(posedge clk or negedge rst_cs[g/16])
            if (!rst_cs[g/16]) begin hr <= 2'd0; hw <= 2'd0; hc <= 3'd0; hovf[g] <= 1'b0; end
            else begin
                hr <= hr + npop[1:0];
                if (vm_valid[g] && crdy[g]) begin hw <= hw + 2'd1; h[hw] <= din; end
                hc <= hc - npop + ((vm_valid[g] && crdy[g]) ? 3'd1 : 3'd0);
                if (vm_valid[g] && !crdy[g]) hovf[g] <= 1'b1;
            end
        ot_ratio_cdc_fifo #(.W(103), .DEPTH(LD)) u_x (.wclk(clk), .wrst_n(rst_cs[g/16]), .w_v(hc != 3'd0), .w_rdy(wr),
            .w_d({h[hr + 2'd1], hc >= 3'd2, h[hr]}), .rclk(ckv), .rrst_n(rsv_c[g/16]), .r_v(cv[g]), .r_rdy(1'b1),
            .r_d(cd[103*g +: 103]), .w_live(), .r_live());
        always @(posedge ckv or negedge rsv_c[g/16])
            if (!rsv_c[g/16]) w_v[2*g +: 2] <= 2'b00; else w_v[2*g +: 2] <= {cv[g] & cd[103*g + 51], cv[g]};
        always @(posedge ckv) begin w_d[102*g +: 51] <= cd[103*g +: 51]; w_d[102*g + 51 +: 51] <= cd[103*g + 52 +: 51]; end
    end endgenerate
    // status lane: the latest stream-side status, written whenever the crossing has room
    wire [63:0] s_now = {g_busy, g_live, 1'b0, h_id, h_ph, cfault | proto_fault | g_fault | (|hovf),
                         phase_drained, phase_idle, phase_live};
    wire s_rdy, s_v; wire [63:0] s_d;
    ot_ratio_cdc_fifo #(.W(64), .DEPTH(2)) u_s (.wclk(clk), .wrst_n(rst_n), .w_v(1'b1), .w_rdy(s_rdy), .w_d(s_now),
        .rclk(ckv), .rrst_n(rsv_n), .r_v(s_v), .r_rdy(1'b1), .r_d(s_d), .w_live(), .r_live());
    always @(posedge ckv or negedge rsv_n) if (!rsv_n) st <= 64'd0; else if (s_v) st <= s_d;
endmodule
