// Bench of the default-off ROM-field system successors (rtl/dsrom_sys): ot_v41_spine_w17w10_sys +
// ot_v41_field_w17w10_sys beside the pinned originals ot_v41_spine_w17w10 + ot_v41_field_w17w10 (REF).  Every
// system has its own vector-memory model (exactly ot_v41_fieldtop_w17w10's: VRD-wide registered read, R write
// ports, increasing port order on a collision) and its own op sequencer over the same op list.  One Verilator
// build holds REF and four DUT variants:
//
//   D0  FAULT_TIE 0, RET_CREDIT 0   (the default: must equal REF on every port, every cycle)        never stalled
//   D1  FAULT_TIE 1, RET_CREDIT 0   (fault tie-off alone; under stall: the documented no-ACK hazard)   stalled
//   D2  FAULT_TIE 1, RET_CREDIT 1, RET_OD = OD2, RET_H = H2  (H2 from the rows/region/phase bound)     stalled
//   D3  FAULT_TIE 1, RET_CREDIT 1, RET_OD = OD3, RET_H = H3  (stress: headroom below the proven bound)  stalled
//
// +STALL=<percent> stalls each VM write port of D1..D3 independently (same seeded pattern for all three);
// REF and D0 are never stalled.  With +STALL=0 every DUT's original ports are compared with REF's every cycle
// (2-state simulation: the field fault of D1..D3 is compared separately, because REF's undriven n_fault bits
// take whatever initial value the simulator gives them: +verilator+rand+reset+2 makes that visible).
//
// Plusargs: +OT_ROM_DIR=<img> +OPS=<ops.txt> +LOG=<prefix> [+STALL=p] [+SEED=s].  Logs <prefix>.<sys>.log:
//   W <cycle> <port> <addr hex> <data hex>    write accepted (w_we & vm_w_ready)
//   L <cycle> <port> <addr hex> <data hex>    write presented while not ready: lost (RET_CREDIT = 0)
//   O <op> <phase_cycles> <wall> <rows r0> <rows r1> ...   per op: rows each region's root produced
//   S key=value ...                           final summary
`timescale 1ns/1ps

module fs_sys #(
    parameter integer ORIG = 0,          // 1: the pinned originals
    parameter integer NP = 16,
    parameter integer R = 4,
    parameter integer NBF = 8,
    parameter integer PHW = 4,
    parameter integer VAW = 16,
    parameter integer SAW = 14,
    parameter integer VRD = 64,
    parameter integer KMAX = 6144,
    parameter integer FAULT_TIE = 0,
    parameter integer RET_CREDIT = 0,
    parameter integer RET_OD = 16,
    parameter integer RET_H = 16,
    parameter integer STALLED = 0,
    parameter NAME = "x",
    parameter integer BW = 1 + PHW + 3 + 1 + 1 + 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10 + 3 + 3 + 1 + 3 + 4 + 32 + 1024
) (
    input  wire clk,
    input  wire rst_n,
    input  wire fin,
    output reg  done,
    // observation (original ports)
    output wire ready, idle, x_re, sfault, ffault, busy,
    output wire [VAW-1:0]   x_addr,
    output wire [R-1:0]     w_we, r_v, r_e,
    output wire [R*VAW-1:0] w_addr,
    output wire [R*32-1:0]  w_data, r_fp32,
    output wire [16*R-1:0]  r_row, r_bf16,
    output wire [3*R-1:0]   r_pos,
    output wire [31:0]      pcyc,
    output wire [BW-1:0]    bus
);
    integer nops, fd, rc;
    integer o_ph [0:63], o_np [0:63], o_xb [0:63], o_xs [0:63], o_ob [0:63], o_os [0:63];
    reg [8*1024-1:0] ops_path, log_path, rom_dir;
    integer lg, stall, seed;
    reg [31:0] vm [0:(1 << VAW)-1];
    integer ii;
    initial begin
        nops = 0;
        if (!$value$plusargs("OPS=%s", ops_path)) $fatal(1, "+OPS");
        if (!$value$plusargs("LOG=%s", log_path)) $fatal(1, "+LOG");
        if (!$value$plusargs("OT_ROM_DIR=%s", rom_dir)) $fatal(1, "+OT_ROM_DIR");
        if (!$value$plusargs("STALL=%d", stall)) stall = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (STALLED == 0) stall = 0;
        fd = $fopen(ops_path, "r");
        rc = 6;
        while (rc == 6) begin
            rc = $fscanf(fd, "%d %d %d %d %d %d\n", o_ph[nops], o_np[nops], o_xb[nops], o_xs[nops], o_ob[nops], o_os[nops]);
            if (rc == 6) nops = nops + 1;
        end
        $fclose(fd);
        lg = $fopen({log_path, ".", NAME, ".log"}, "w");
        for (ii = 0; ii < (1 << VAW); ii = ii + 1) vm[ii] = 32'd0;
        $readmemh({rom_dir, "/vm.hex"}, vm);
    end

    reg  [VRD*32-1:0] x_q;
    reg  [R-1:0]      vm_w_ready;
    wire [R-1:0]      r_ready, near, push, w_ack;
    wire [8*R-1:0]    occ;
    wire [31:0]       retired, gcyc;
    wire              gated, wovf, rovf;
    reg               go;
    reg  [PHW-1:0]    ph; reg [2:0] np; reg [VAW-1:0] xb, xs, ob, os;
    wire              c_go, c_gobf, c_cfg, c_xs_v, c_xb_v;
    wire [PHW-1:0]    c_ph;
    wire [2:0]        c_np, c_xs_b, c_xs_pos, c_xb_pos, c_xb_b;
    wire [7:0]        c_xs_p;
    wire [1:0]        c_xs_sv;
    wire [255:0]      c_xs_q0, c_xs_q1;
    wire [9:0]        c_xs_e0, c_xs_e1;
    wire [3:0]        c_xb_sv;
    wire [31:0]       c_xb_u;
    wire [1023:0]     c_xb_d;
    generate if (ORIG != 0) begin : g_o
        ot_v41_spine_w17w10 #(.PHW(PHW), .SAW(SAW), .R(R), .VAW(VAW), .VRD(VRD), .KMAX(KMAX), .BST(2)) u_sp (
            .clk(clk), .rst_n(rst_n), .go(go), .i_ph(ph), .i_np(np), .i_xbase(xb), .i_xps(xs),
            .i_obase(ob), .i_ops(os), .i_fmt(2'd0), .ready(ready), .idle(idle), .x_re(x_re), .x_addr(x_addr),
            .x_q(x_q), .w_we(w_we), .w_addr(w_addr), .w_data(w_data),
            .f_cfg_go(c_cfg), .f_cfg_ph(c_ph), .f_cfg_np(c_np), .f_go(c_go), .f_go_bf(c_gobf), .f_xs_v(c_xs_v),
            .f_xs_p(c_xs_p), .f_xs_b(c_xs_b), .f_xs_sv(c_xs_sv), .f_xs_q0(c_xs_q0), .f_xs_e0(c_xs_e0),
            .f_xs_q1(c_xs_q1), .f_xs_e1(c_xs_e1), .f_xs_pos(c_xs_pos), .f_xb_pos(c_xb_pos), .f_xb_v(c_xb_v),
            .f_xb_b(c_xb_b), .f_xb_sv(c_xb_sv), .f_xb_u(c_xb_u), .f_xb_d(c_xb_d), .f_bus(bus),
            .r_v(r_v), .r_row(r_row), .r_pos(r_pos), .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e),
            .f_fault(ffault), .fault(sfault), .phase_cycles(pcyc));
        ot_v41_field_w17w10 #(.NP(NP), .R(R), .NBF(NBF), .PHW(PHW), .RST(1)) u_fl (
            .clk(clk), .rst_n(rst_n), .cfg_go(c_cfg), .cfg_ph(c_ph), .cfg_np(c_np), .go(c_go), .go_bf(c_gobf),
            .xs_v(c_xs_v), .xs_p(c_xs_p), .xs_b(c_xs_b), .xs_sv(c_xs_sv), .xs_q0(c_xs_q0), .xs_e0(c_xs_e0),
            .xs_q1(c_xs_q1), .xs_e1(c_xs_e1), .xs_pos(c_xs_pos), .xb_pos(c_xb_pos), .xb_v(c_xb_v), .xb_b(c_xb_b),
            .xb_sv(c_xb_sv), .xb_u(c_xb_u), .xb_d(c_xb_d), .r_v(r_v), .r_row(r_row), .r_pos(r_pos),
            .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e), .busy(busy), .fault(ffault));
        assign r_ready = {R{1'b1}}; assign near = '0; assign push = r_v; assign w_ack = w_we; assign occ = '0;
        assign retired = 32'd0; assign gcyc = 32'd0; assign gated = 1'b0; assign wovf = 1'b0; assign rovf = 1'b0;
    end else begin : g_s
        wire [16*R-1:0] ack_row;
        wire [3*R-1:0]  ack_pos;
        ot_v41_spine_w17w10_sys #(.PHW(PHW), .SAW(SAW), .R(R), .VAW(VAW), .VRD(VRD), .KMAX(KMAX), .BST(2),
                                 .RET_CREDIT(RET_CREDIT)) u_sp (
            .clk(clk), .rst_n(rst_n), .go(go), .i_ph(ph), .i_np(np), .i_xbase(xb), .i_xps(xs),
            .i_obase(ob), .i_ops(os), .i_fmt(2'd0), .ready(ready), .idle(idle), .x_re(x_re), .x_addr(x_addr),
            .x_q(x_q), .w_we(w_we), .w_addr(w_addr), .w_data(w_data),
            .f_cfg_go(c_cfg), .f_cfg_ph(c_ph), .f_cfg_np(c_np), .f_go(c_go), .f_go_bf(c_gobf), .f_xs_v(c_xs_v),
            .f_xs_p(c_xs_p), .f_xs_b(c_xs_b), .f_xs_sv(c_xs_sv), .f_xs_q0(c_xs_q0), .f_xs_e0(c_xs_e0),
            .f_xs_q1(c_xs_q1), .f_xs_e1(c_xs_e1), .f_xs_pos(c_xs_pos), .f_xb_pos(c_xb_pos), .f_xb_v(c_xb_v),
            .f_xb_b(c_xb_b), .f_xb_sv(c_xb_sv), .f_xb_u(c_xb_u), .f_xb_d(c_xb_d), .f_bus(bus),
            .r_v(r_v), .r_row(r_row), .r_pos(r_pos), .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e),
            .f_fault(ffault), .fault(sfault), .phase_cycles(pcyc),
            .vm_w_ready(vm_w_ready), .r_ready(r_ready), .r_near_full(near), .w_ack(w_ack), .ack_row(ack_row),
            .ack_pos(ack_pos), .rows_retired(retired), .issue_gated(gated), .gate_cycles(gcyc), .w_ovf(wovf));
        ot_v41_field_w17w10_sys #(.NP(NP), .R(R), .NBF(NBF), .PHW(PHW), .RST(1), .FAULT_TIE(FAULT_TIE),
                                  .RET_CREDIT(RET_CREDIT), .RET_OD(RET_OD), .RET_H(RET_H)) u_fl (
            .clk(clk), .rst_n(rst_n), .cfg_go(c_cfg), .cfg_ph(c_ph), .cfg_np(c_np), .go(c_go), .go_bf(c_gobf),
            .xs_v(c_xs_v), .xs_p(c_xs_p), .xs_b(c_xs_b), .xs_sv(c_xs_sv), .xs_q0(c_xs_q0), .xs_e0(c_xs_e0),
            .xs_q1(c_xs_q1), .xs_e1(c_xs_e1), .xs_pos(c_xs_pos), .xb_pos(c_xb_pos), .xb_v(c_xb_v), .xb_b(c_xb_b),
            .xb_sv(c_xb_sv), .xb_u(c_xb_u), .xb_d(c_xb_d), .r_v(r_v), .r_row(r_row), .r_pos(r_pos),
            .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e), .busy(busy), .fault(ffault),
            .r_ready(r_ready), .r_near_full(near), .r_push(push), .r_occ(occ), .ret_ovf(rovf));
    end endgenerate

    // vector memory (ot_v41_fieldtop_w17w10's model; a write lands only when accepted)
    integer kv;
    always @(posedge clk) begin
        if (x_re) for (kv = 0; kv < VRD; kv = kv + 1) x_q[32*kv +: 32] <= vm[x_addr + VAW'(kv)];
        for (kv = 0; kv < R; kv = kv + 1) if (w_we[kv] && vm_w_ready[kv]) vm[w_addr[VAW*kv +: VAW]] <= w_data[32*kv +: 32];
    end
    // write-port stall pattern: drawn every cycle for every port whatever the system (identical pattern per seed)
    integer ks, sd, rnd;
    initial sd = 0;
    always @(posedge clk) begin
        if (sd == 0) sd = seed;
        for (ks = 0; ks < R; ks = ks + 1) begin
            rnd = $random(sd);
            vm_w_ready[ks] <= (stall == 0) ? 1'b1 : ((((rnd % 100) + 100) % 100) >= stall);
        end
    end
    initial vm_w_ready = {R{1'b1}};

    // sequencer
    integer cyc, k, st, t0, kp;
    integer pushc [0:R-1];
    initial begin cyc = 0; k = 0; st = 0; t0 = 0; done = 1'b0; go = 1'b0; end
    always @(posedge clk) if (rst_n) begin
        go <= 1'b0;
        case (st)
            0: if (k == nops) done <= 1'b1;
               else if (ready) begin
                   go <= 1'b1; ph <= PHW'(o_ph[k]); np <= 3'(o_np[k]); xb <= VAW'(o_xb[k]); xs <= VAW'(o_xs[k]);
                   ob <= VAW'(o_ob[k]); os <= VAW'(o_os[k]); st <= 1; t0 <= cyc;
                   for (kp = 0; kp < R; kp = kp + 1) pushc[kp] = 0;
               end
            1: st <= 2;
            2: if (idle) begin
                   $fwrite(lg, "O %0d %0d %0d", k, pcyc, cyc - t0);
                   for (kp = 0; kp < R; kp = kp + 1) $fwrite(lg, " %0d", pushc[kp]);
                   $fwrite(lg, "\n");
                   k <= k + 1; st <= 0;
               end
            default: st <= 0;
        endcase
    end
    // logging and counters (sampled before the edge)
    integer accepted, lost, stalled_cycles, fault_cycles, kc;
    integer occ_max [0:R-1];
    initial begin accepted = 0; lost = 0; stalled_cycles = 0; fault_cycles = 0; for (kc = 0; kc < R; kc = kc + 1) occ_max[kc] = 0; end
    always @(posedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (ffault) fault_cycles = fault_cycles + 1;
        for (kc = 0; kc < R; kc = kc + 1) begin
            if (push[kc]) pushc[kc] = pushc[kc] + 1;
            if (32'(occ[8*kc +: 8]) > occ_max[kc]) occ_max[kc] = 32'(occ[8*kc +: 8]);
            if (!vm_w_ready[kc]) stalled_cycles = stalled_cycles + 1;
            if (w_we[kc]) begin
                if (vm_w_ready[kc]) begin
                    $fwrite(lg, "W %0d %0d %h %h\n", cyc, kc, w_addr[VAW*kc +: VAW], w_data[32*kc +: 32]);
                    accepted = accepted + 1;
                end else if (RET_CREDIT == 0) begin
                    $fwrite(lg, "L %0d %0d %h %h\n", cyc, kc, w_addr[VAW*kc +: VAW], w_data[32*kc +: 32]);
                    lost = lost + 1;
                end
            end
        end
    end
    integer kf;
    always @(posedge fin) begin
        $fwrite(lg, "S done=%0d cycles=%0d ops=%0d ops_done=%0d field_fault=%0d spine_fault=%0d field_fault_cycles=%0d", done, cyc,
                nops, k, ffault, sfault, fault_cycles);
        $fwrite(lg, " ret_ovf=%0d w_ovf=%0d rows_retired=%0d gate_cycles=%0d accepted=%0d lost=%0d stall_port_cycles=%0d",
                rovf, wovf, retired, gcyc, accepted, lost, stalled_cycles);
        $fwrite(lg, " stall=%0d seed=%0d fault_tie=%0d ret_credit=%0d ret_od=%0d ret_h=%0d occ_max=", stall, seed, FAULT_TIE,
                RET_CREDIT, RET_OD, RET_H);
        for (kf = 0; kf < R; kf = kf + 1) $fwrite(lg, "%0d%s", occ_max[kf], kf == R - 1 ? "" : ",");
        $fwrite(lg, "\n");
        $fclose(lg);
    end
endmodule

module tb_field_sys #(
    parameter integer NP = 16,
    parameter integer R = 4,
    parameter integer NBF = 8,
    parameter integer PHW = 4,
    parameter integer VAW = 16,
    parameter integer OD2 = 16,
    parameter integer H2 = 16,
    parameter integer OD3 = 4,
    parameter integer H3 = 4,
    parameter integer LIMIT = 60000,
    parameter integer GRACE = 20000      // cycles D3 (stress) may run after the others finish
) (
    input wire clk
);
    localparam integer BW = 1 + PHW + 3 + 1 + 1 + 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10 + 3 + 3 + 1 + 3 + 4 + 32 + 1024;
    localparam integer NS = 5;
    reg rst_n = 1'b0;
    reg fin = 1'b0;
    wire [NS-1:0] done;
    wire              ready [0:NS-1], idle [0:NS-1], x_re [0:NS-1], sfault [0:NS-1], ffault [0:NS-1], busy [0:NS-1];
    wire [VAW-1:0]    x_addr [0:NS-1];
    wire [R-1:0]      w_we [0:NS-1], r_v [0:NS-1], r_e [0:NS-1];
    wire [R*VAW-1:0]  w_addr [0:NS-1];
    wire [R*32-1:0]   w_data [0:NS-1], r_fp32 [0:NS-1];
    wire [16*R-1:0]   r_row [0:NS-1], r_bf16 [0:NS-1];
    wire [3*R-1:0]    r_pos [0:NS-1];
    wire [31:0]       pcyc [0:NS-1];
    wire [BW-1:0]     bus [0:NS-1];
`define FS_PORTS(i) .clk(clk), .rst_n(rst_n), .fin(fin), .done(done[i]), .ready(ready[i]), .idle(idle[i]), .x_re(x_re[i]), \
        .sfault(sfault[i]), .ffault(ffault[i]), .busy(busy[i]), .x_addr(x_addr[i]), .w_we(w_we[i]), .r_v(r_v[i]), .r_e(r_e[i]), \
        .w_addr(w_addr[i]), .w_data(w_data[i]), .r_fp32(r_fp32[i]), .r_row(r_row[i]), .r_bf16(r_bf16[i]), .r_pos(r_pos[i]), \
        .pcyc(pcyc[i]), .bus(bus[i])
    fs_sys #(.ORIG(1), .NP(NP), .R(R), .NBF(NBF), .PHW(PHW), .VAW(VAW), .STALLED(0), .NAME("ref")) u_ref (`FS_PORTS(0));
    fs_sys #(.NP(NP), .R(R), .NBF(NBF), .PHW(PHW), .VAW(VAW), .FAULT_TIE(0), .RET_CREDIT(0), .STALLED(0), .NAME("d0")) u_d0 (`FS_PORTS(1));
    fs_sys #(.NP(NP), .R(R), .NBF(NBF), .PHW(PHW), .VAW(VAW), .FAULT_TIE(1), .RET_CREDIT(0), .STALLED(1), .NAME("d1")) u_d1 (`FS_PORTS(2));
    fs_sys #(.NP(NP), .R(R), .NBF(NBF), .PHW(PHW), .VAW(VAW), .FAULT_TIE(1), .RET_CREDIT(1), .RET_OD(OD2), .RET_H(H2),
             .STALLED(1), .NAME("d2")) u_d2 (`FS_PORTS(3));
    fs_sys #(.NP(NP), .R(R), .NBF(NBF), .PHW(PHW), .VAW(VAW), .FAULT_TIE(1), .RET_CREDIT(1), .RET_OD(OD3), .RET_H(H3),
             .STALLED(1), .NAME("d3")) u_d3 (`FS_PORTS(4));

    integer cyc = 0, stall, t_main = -1;
    integer checks [1:NS-1], mism [1:NS-1], ffd [1:NS-1], ref_ff1 = 0;
    reg [8*16-1:0] first [1:NS-1];
    integer firstc [1:NS-1];
    integer i, bad;
    reg [8*16-1:0] what;
    reg [8*1024-1:0] log_path;
    integer lg;
    initial begin
        if (!$value$plusargs("STALL=%d", stall)) stall = 0;
        for (i = 1; i < NS; i = i + 1) begin checks[i] = 0; mism[i] = 0; ffd[i] = 0; first[i] = "-"; firstc[i] = -1; end
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 6) rst_n <= 1'b1;
        if (rst_n) begin
            if (ffault[0]) ref_ff1 = ref_ff1 + 1;
            for (i = 1; i < NS; i = i + 1) if (stall == 0 || i == 1) begin
                // REF and D0 are never stalled: D0 is compared on every run, D1..D3 only on no-stall runs
                checks[i] = checks[i] + 1;
                bad = 1;
                if (ready[i] != ready[0]) what = "ready";
                else if (idle[i] != idle[0]) what = "idle";
                else if (x_re[i] != x_re[0]) what = "x_re";
                else if (x_addr[i] != x_addr[0]) what = "x_addr";
                else if (w_we[i] != w_we[0]) what = "w_we";
                else if (w_addr[i] != w_addr[0]) what = "w_addr";
                else if (w_data[i] != w_data[0]) what = "w_data";
                else if (sfault[i] != sfault[0]) what = "spine_fault";
                else if (pcyc[i] != pcyc[0]) what = "phase_cycles";
                else if (bus[i] != bus[0]) what = "f_bus";
                else if (r_v[i] != r_v[0]) what = "r_v";
                else if (r_row[i] != r_row[0]) what = "r_row";
                else if (r_pos[i] != r_pos[0]) what = "r_pos";
                else if (r_fp32[i] != r_fp32[0]) what = "r_fp32";
                else if (r_bf16[i] != r_bf16[0]) what = "r_bf16";
                else if (r_e[i] != r_e[0]) what = "r_e";
                else if (busy[i] != busy[0]) what = "busy";
                else if (i == 1 && ffault[i] != ffault[0]) what = "field_fault";
                else bad = 0;
                if (bad != 0) begin
                    if (mism[i] == 0) begin first[i] = what; firstc[i] = cyc; end
                    mism[i] = mism[i] + 1;
                end
                if (ffault[i] != ffault[0]) ffd[i] = ffd[i] + 1;
            end
        end
        if (t_main < 0 && &done[3:0]) t_main = cyc;
        if (cyc > 10 && (&done || cyc > LIMIT || (t_main >= 0 && cyc > t_main + GRACE)) && !fin) begin
            fin <= 1'b1;
            if (!$value$plusargs("LOG=%s", log_path)) log_path = "x";
            lg = $fopen({log_path, ".tb.log"}, "w");
            $fwrite(lg, "S all_done=%0d main_done=%0d main_cycles=%0d cycles=%0d stall=%0d ref_field_fault_cycles=%0d\n", &done,
                    &done[3:0], t_main, cyc, stall, ref_ff1);
            for (i = 1; i < NS; i = i + 1)
                $fwrite(lg, "C d%0d checks=%0d mismatches=%0d first=%0s first_cycle=%0d field_fault_differs_cycles=%0d\n", i - 1,
                        checks[i], mism[i], first[i], firstc[i], ffd[i]);
            $fclose(lg);
        end
        if (fin) $finish;
    end
endmodule
