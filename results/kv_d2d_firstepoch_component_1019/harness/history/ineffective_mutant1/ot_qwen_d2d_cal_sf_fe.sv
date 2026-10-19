`timescale 1ns/1ps
// Private fixed-image functional guard; original source SHA9b369435 preserved separately.
module ot_qwen_d2d_cal_sf_fe #(parameter integer ENABLE_FIRST_EPOCH_GUARD = 0, parameter integer FIXED_IMAGE = 1, parameter [1023:0] EXPECTED_IMAGE = 0, parameter [4:0] EXPECTED_BOOT_BASE = 0, parameter [4:0] EXPECTED_TOKEN_BASE = 0, parameter integer NE = 32, parameter integer AW = $clog2(NE), parameter integer MUTFO = 0) (
    input wire [15:0] cfg_epoch, start_epoch,
    input wire cfg_valid, start_valid, pair_ready, pair_poison, reload,
    output wire receipt_ready,
    output wire [15:0] receipt_epoch,
    output reg [31:0] seen,
    output reg base_seen, epoch_valid, settled, poisoned, first_consumed,
    input  wire          ck,
    input  wire          rst_n,
    input  wire          cfg_we,
    input  wire [AW:0]   cfg_addr,       // [AW] = 1: segment-1 base register (cfg_data[AW-1:0])
    input  wire [63:0]   cfg_data_c,     // two identical pin copies: [31:0] entries 0..NE/2-1, [63:32] the rest
    input  wire [AW-1:0] cfg_base_c,     // a third pin copy of cfg_data[AW-1:0]: the segment-1 base decode
    input  wire [3:0]    start_c,        // four identical pin copies of the compiled start strobe
    input  wire [3:0]    seg_c,          // four identical pin copies of start_seg
    input  wire [3:0]    halt_c,         // copies of halt: [0] pointer low half, [1] pointer high half, [2] cnt, [3] run state
    output reg           ev_v,
    output reg  [2:0]    ev_port,
    output reg  [3:0]    ev_kind,
    output reg  [4:0]    ev_beat,
    output reg           running,
    output reg           fault
);
    // Fixed image only. Receipt taps mirror the actual accepted-write predicate below.
    initial if (FIXED_IMAGE != 1) $error("FIRST_EPOCH_VARIABLE_IMAGE_UNSUPPORTED");
    reg [15:0] installed_epoch;
    reg reset_first, reset_leaf0, reset_leaf1;
    always @(posedge ck or negedge rst_n)
      if (!rst_n) begin reset_first<=0; reset_leaf0<=0; reset_leaf1<=0; end
      else begin reset_first<=1; reset_leaf0<=reset_first; reset_leaf1<=reset_first; end
    // Receipt and the actual calendar share assertion AND release. Landing
    // readiness cannot erase an actually accepted early configuration write.
    wire guard_rst_n = rst_n;
    wire write_entry = cfg_we && !running && !cfg_addr[AW];
    wire write_base = cfg_we && !running && cfg_addr[AW];
    wire [31:0] consumed_data = cfg_addr[AW-1:0] < NE/2 ? cfg_data_c[31:0] : cfg_data_c[63:32];
    wire [31:0] expected_data = EXPECTED_IMAGE[32*cfg_addr[AW-1:0] +: 32];
    wire metadata_ok = cfg_valid && (!epoch_valid || cfg_epoch == installed_epoch);
    wire boot_data_ok = write_entry ? consumed_data == expected_data :
                        write_base && cfg_addr == 6'd32 && cfg_base_c == EXPECTED_BOOT_BASE;
    wire runtime_data_ok = write_base && cfg_addr == 6'd32 &&
                           (cfg_base_c == EXPECTED_BOOT_BASE || cfg_base_c == EXPECTED_TOKEN_BASE);
    wire bad_write = cfg_we && (running || (metadata_ok !== 1'b1) ||
                            (first_consumed ? (runtime_data_ok !== 1'b1) : (boot_data_ok !== 1'b1)));
    wire copies_ok = start_c == {4{start_c[0]}} && seg_c == {4{seg_c[0]}};
    wire base_copies_ok;
    wire identity_ok = start_valid && epoch_valid && start_epoch == installed_epoch;
    wire start_allowed = guard_rst_n && reset_leaf0 && reset_leaf1 && receipt_ready && pair_ready && !pair_poison &&
                         !reload && !poisoned && !fault && !bad_write && !cfg_we && !cfg_recent &&
                         !running && (copies_ok === 1'b1) && (identity_ok === 1'b1) && !(|halt_c);
    wire any_start = |start_c;
    wire [3:0] authorized_start = (ENABLE_FIRST_EPOCH_GUARD != 0) ?
                          start_c : start_c;
    wire [3:0] effective_halt = halt_c | {4{ENABLE_FIRST_EPOCH_GUARD != 0 &&
               (poisoned || fault || bad_write || pair_poison || reload || (any_start && !start_allowed))}};
    assign receipt_ready = epoch_valid && (&seen) && base_seen && settled &&
                           !poisoned && !reload && !pair_poison && guard_rst_n && (base_copies_ok === 1'b1);
    assign receipt_epoch = installed_epoch;
    always @(posedge ck or negedge guard_rst_n) begin
      if (!guard_rst_n) begin
        seen<=0; base_seen<=0; installed_epoch<=0; epoch_valid<=0;
        settled<=0; poisoned<=0; first_consumed<=0;
      end else if (ENABLE_FIRST_EPOCH_GUARD != 0) begin
        if (reload) begin seen<=0; base_seen<=0; epoch_valid<=0; settled<=0; first_consumed<=0; end
        else begin
          if (cfg_we) settled<=0;
          else if ((&seen) && base_seen && epoch_valid) settled<=1;
          if (cfg_we && !first_consumed && !bad_write) begin
            if (!epoch_valid) begin installed_epoch<=cfg_epoch; epoch_valid<=1; end
            if (write_entry) seen[cfg_addr[AW-1:0]]<=1;
            if (write_base) base_seen<=1;
          end
          if (any_start && start_allowed) first_consumed<=1;
        end
        // Current-edge faults veto before every original start-dependent assignment.
        // Poison survives reload and any later upload; only real local reset clears it.
        if (bad_write || pair_poison || fault || (any_start && !start_allowed)) poisoned<=1;
      end
    end
    generate if (NE != 32) begin : g_ne_unsupported
        OT_QWEN_D2D_CAL_SF_SUPPORTS_NE32_ONLY u_ne ();
    end endgenerate
    localparam integer H = NE / 2;
    // ---- compiler image: one 32-b register per entry, written only while stopped (as built) ----
    wire [32*NE-1:0] tv;
    genvar gi;
    for (gi = 0; gi < NE; gi = gi + 1) begin : g_e
        reg [31:0] e;
        always @(posedge ck)
            if (cfg_we && !running && !cfg_addr[AW] && cfg_addr[AW-1:0] == gi)
                e <= (gi < H) ? cfg_data_c[31:0] : cfg_data_c[63:32];
        assign tv[32*gi +: 32] = e;
    end
    // ---- segment-1 base, one-hot.  Copy 0 is the master; copy 1 takes the SAME D net (sel1_d) ----
    wire seg_we = cfg_we && !running && cfg_addr[AW];
    wire [NE-1:0] sel1_dec = {{(NE-1){1'b0}}, 1'b1} << cfg_base_c;
    (* keep = "true", dont_touch = "true" *) reg [NE-1:0] sel1_c0;
    (* keep = "true", dont_touch = "true" *) reg [NE-1:0] sel1_c1;
    assign base_copies_ok = (sel1_c0 == sel1_c1) &&
        ((sel1_c0 == (32'b1 << EXPECTED_BOOT_BASE)) ||
         (first_consumed && sel1_c0 == (32'b1 << EXPECTED_TOKEN_BASE)));
    wire [NE-1:0] sel1_d = seg_we ? sel1_dec : sel1_c0;
    (* keep = "true", dont_touch = "true" *) always @(posedge ck) begin
        sel1_c0 <= sel1_d;
        sel1_c1 <= (MUTFO == 1) ? (seg_we ? sel1_dec : sel1_c1) : sel1_d;
    end
    // ---- AND-OR selects: bits [H-1:0]... of the selected word from copy 0, the upper word half from copy 1 ----
    reg [31:0] f1_lo, f1_hi, nx_lo, nx_hi;
    (* keep = "true", dont_touch = "true" *) reg [NE-1:0] pc0;   // one-hot ptr[AW-1:0], master (advance, fault, rotate)
    (* keep = "true", dont_touch = "true" *) reg [NE-1:0] pc1;   // copy: same D net, selects the upper word half
    reg ph;                                                     // ptr[AW]
    integer k;
    always @* begin
        f1_lo = 32'd0; f1_hi = 32'd0; nx_lo = 32'd0; nx_hi = 32'd0;
        for (k = 0; k < NE; k = k + 1) begin
            f1_lo = f1_lo | ({32{sel1_c0[k]}} & tv[32*k +: 32]);
            f1_hi = f1_hi | ({32{sel1_c1[k]}} & tv[32*k +: 32]);
            nx_lo = nx_lo | ({32{pc0[k]}} & tv[32*k +: 32]);
            nx_hi = nx_hi | ({32{pc1[k]}} & tv[32*k +: 32]);
        end
    end
    wire [31:0] f1  = {f1_hi[31:16], f1_lo[15:0]};               // = tbl[seg1]
    wire [31:0] nxt = {nx_hi[31:16], nx_lo[15:0]};               // = tbl[ptr[AW-1:0]]
    // Prefetch both first entries while the compiler image is stable (as built: same edges, same cfg_recent rule).
    reg [31:0] first0_q, first1_q;
    reg cfg_recent;
    always @(posedge ck) begin
        first0_q <= tv[31:0]; first1_q <= f1;
        cfg_recent <= cfg_we;
    end
    // first word fields: [17:0] by seg copy 0, [31:18] (dt) by seg copy 1
    wire [31:0] first = {seg_c[1] ? first1_q[31:18] : first0_q[31:18], seg_c[0] ? first1_q[17:0] : first0_q[17:0]};
    reg [31:0] cur;
    reg [13:0] cnt;
    reg [4:0]  rep, bcur;
    // running and a KEPT copy share one D net (run_d); the pointer's upper half advances on the copy
    (* keep = "true", dont_touch = "true" *) reg run_c;
    wire run_d = effective_halt[3] ? 1'b0 : authorized_start[0] ? 1'b1 : (running && cnt == 14'd1 && rep == 5'd0 && cur[17]) ? 1'b0 : running;
    (* keep = "true", dont_touch = "true" *) always @(posedge ck or negedge rst_n)
        if (!rst_n) begin running <= 1'b0; run_c <= 1'b0; end
        else begin running <= run_d; run_c <= run_d; end
    wire adv   = running && cnt == 14'd1 && rep == 5'd0 && !cur[17];
    wire adv_h = run_c && cnt == 14'd1 && rep == 5'd0 && !cur[17];
    // ---- pointer: one-hot + lap bit, ONE D net for master and copy (ptr <= {0,sb}+1 / ptr+1 / hold) ----
    wire [NE-1:0] sel1_h = {sel1_c1[NE-1:H], sel1_c0[H-1:0]};
    wire [NE-1:0] st_s1  = {sel1_h[NE-2:0], sel1_h[NE-1]};       // one-hot (seg1 + 1) mod NE
    wire [NE-1:0] rot    = {pc0[NE-2:0], pc0[NE-1]};
    reg  [NE-1:0] pd;
    reg           phd;
    always @* begin
        for (k = 0; k < NE; k = k + 1) begin
            if ((k < H) ? effective_halt[0] : effective_halt[1]) pd[k] = pc0[k];
            else if ((k < H) ? authorized_start[2] : authorized_start[3]) pd[k] = ((k < H) ? seg_c[2] : seg_c[3]) ? st_s1[k] : (k == 1);
            else if ((k < H) ? adv : adv_h) pd[k] = rot[k];
            else pd[k] = pc0[k];
        end
        if (effective_halt[1]) phd = ph;
        else if (authorized_start[3]) phd = seg_c[3] & sel1_c1[NE-1];
        else if (adv_h) phd = ph ^ pc0[NE-1];
        else phd = ph;
    end
    (* keep = "true", dont_touch = "true" *) always @(posedge ck or negedge rst_n)
        if (!rst_n) begin pc0 <= {{(NE-1){1'b0}}, 1'b1}; pc1 <= {{(NE-1){1'b0}}, 1'b1}; ph <= 1'b0; end
        else begin pc0 <= pd; pc1 <= pd; ph <= phd; end
    // ---- run state (as built; start copy 0) ----
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            ev_v <= 1'b0; ev_port <= 3'd0; ev_kind <= 4'd0; ev_beat <= 5'd0;
            cur <= 32'd0; fault <= 1'b0; rep <= 5'd0; bcur <= 5'd0;
        end else begin
            ev_v <= 1'b0;
            if (ENABLE_FIRST_EPOCH_GUARD != 0 && (poisoned || bad_write || pair_poison || (any_start && !start_allowed))) fault <= 1'b1;
            if (cfg_we && running) fault <= 1'b1;
            if (effective_halt[3]) ;                                                       // running: run_d
            else if (authorized_start[0]) begin
                if (running || cfg_we || cfg_recent) fault <= 1'b1;
                cur <= first; rep <= first[4:0]; bcur <= first[9:5];
                if (first[31:18] == 14'd0 || {1'b0, first[9:5]} + {1'b0, first[4:0]} > 6'd31) fault <= 1'b1;
            end else if (running) begin
                if (cnt == 14'd1) begin
                    ev_v <= (ENABLE_FIRST_EPOCH_GUARD == 0 || (!poisoned && !pair_poison)); ev_port <= cur[16:14]; ev_kind <= cur[13:10]; ev_beat <= bcur;
                    if (rep != 5'd0) begin rep <= rep - 5'd1; bcur <= bcur + 5'd1; end   // burst: next cycle
                    else if (cur[17]) ;                                            // running: run_d
                    else begin
                        if (ph && pc0[0]) fault <= 1'b1;                               // ptr == NE
                        if (nxt[31:18] == 14'd0 || {1'b0, nxt[9:5]} + {1'b0, nxt[4:0]} > 6'd31) fault <= 1'b1;
                        cur <= nxt; rep <= nxt[4:0]; bcur <= nxt[9:5];
                    end
                end
            end
        end
    end
    // ---- interval counter (as built; start copy 1) ----
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) cnt <= 14'd0;
        else if (effective_halt[2]) cnt <= cnt;
        else if (authorized_start[1]) cnt <= first[31:18];
        else if (running) begin
            if (cnt == 14'd1) begin
                if (rep == 5'd0 && !cur[17]) cnt <= nxt[31:18];
            end else cnt <= cnt - 1'b1;
        end
    end
`ifdef OT_FO_CHECK
    reg fo_armed = 1'b0;
    always @(posedge ck) begin
        if (fo_armed && (sel1_c1 !== sel1_c0 || pc1 !== pc0 || run_c !== running))
            $display("FO_COPY_MISMATCH %m t=%0t sel1 %h/%h pc %h/%h", $time, sel1_c0, sel1_c1, pc0, pc1);
        fo_armed <= 1'b1;
    end
`endif
endmodule
