`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_seq_static (claude S81 VM owner r7, 2026-10-14): the S81 VM SEQUENCER ENGINE, engine 12 of the fixed-cycle
// issuer dsfd_stage_seq_static_c (rtl/dsrom_sys/s81_static_control).  Successor of the diagnostic credit prototype
// dsfd_vm_seq (pulse credits / slot pool / stalls: VOID under the owner rule 2026-10-14T18:59 "static cycle schedule,
// no credits / backpressure").
//
// STATIC CONTRACT.  The compiler assigns every command cycle and every counter slot.  Nothing here waits, stalls,
// queues, arbitrates or returns a credit: every command is taken the cycle it reaches the pin, and its done leaves
// c_done exactly DLAT = 6 stream cycles after the command pin cycle (the issuer's calendar row carries done = issue +
// DLAT + its own pin stages).  Completion of operand rows is NOT a scheduling event: it is VERIFIED at a compiled
// CHECK cycle against the actual write-commit observations of the native static VM (dsfd_vm_static512_rel2
// commit_v / commit_addr / commit_mask, 4 slices x 32 banks), and any discrepancy is a sticky fault (c_st[0]); the
// calendar continues and the job result is discarded outside this block (issuer rule).
//
// Command (issuer native ABI) c_cmd = {v, ctx 1, user 10, pos 21, tok 21, arg 24, row 7}; done tag = {ctx, row}.
//   COMPACT v2 sparse SU operands: codes5/7 select slots0..3/4..7;
//   arg[20:19] slotlow2, [18:9] base/16, [8:7] color, [6:0] nrows-1.
//   Rows are 16*base16+color+4*k, k=0..nrows-1; count exactly16*nrows.
//   Same code/slot with arg[18:0]=19'h7ffff is SPARSECHECK.
//   Sparse ops are consumed here, never forwarded. Dense codes0..3 unchanged.
//   arg[23:21] = code.  Codes 0..3 address COUNTER SLOT s = code (NSLOT 4, compiler-allocated, lifetime checked):
//     ARM   s  {[20] client (0 SU, 1 HC), [19:10] base row / 16, [9:0] nrows - 1}     (same 21-bit compact form as
//           tools/s81_ctrl/vm_arms.py compact_arg; that compiler's single-slot output = code 0)
//           counts every element committed in rows [base, base + nrows) at commit-pin cycles >= ARM pin + 1;
//           expected nelems = 16 * nrows (full-row operand contract).
//     CHECK s  {[20] client, [19:10] = 10'h3FF, [9:0] = 10'h3FF} (that range is impossible for an ARM: base 16368 +
//           1024 rows > 16384).  Verifies, for commits observed at pin cycles <= CHECK pin, count == nelems of slot s
//           and client == the armed client.  Pass: slot s becomes VERIFIED (t_inp of its client, an assertion feed for
//           the consumer's own fixed-start check; it never starts or delays anything).
//   Codes 4/6: NATIVE VM ops (P2ID / P2RD / LARM / XMAP-XGO of dsfd_sp_vm_m) forwarded unchanged on v_cv / v_cd at a
//           fixed stage (pin + 2); the sequencer done is the fixed DLAT done.  The legacy VM channel's own dones only
//           retire the outstanding count (<= VQD, assertion; unknown tag = fault).
// GIVE (vm_arms base16 = count = 1023 on code 0) is a CHECK in this ABI: a static program has no GIVE (a job without
// a VM-produced operand simply has no ARM / CHECK).
//
// Faults (sticky; flt[] for the bench / status, OR on c_st[0]):
//   0 CHECK count != nelems        1 count exceeded nelems (stray / duplicate commit in an armed range)
//   2 CHECK of a slot not armed    3 CHECK client != armed client
//   4 ARM of a slot armed and not yet CHECKed (lifetime)               5 ARM range overlaps another armed slot
//   6 ARM range outside 16384 rows                                   7 EARLY READ: a read request (o_rv / o_rr) at a
//     pin cycle <= the CHECK pin into an armed, not yet verified range  8 legacy channel: unknown / surplus done
//   9 legacy channel: more than VQD native ops outstanding            10 legacy VM fault (v_flt)
//
// Pipeline (stream clock ck; ideal-coincident with the native VM bank clocks, as dsfd_vm_static512_rel2's benches):
//   P0 pin registers: command, 128 commit observations, 32 read requests
//   P1 decode; slot state (base / end / client / open) written for ARM / CHECK of pin t at the end of cycle t+1;
//      per port x slot range compare + masked popcount; read early-check
//   P2 per slot x slice partial sums (32 ports)        P3 per slot total -> count (count of pin-t commits from t+4)
//   P4 CHECK compare (count includes every commit pinned <= CHECK pin)   P5 output retime, P6 done register (c_done at pin + DLAT)
//
// Mutants (negative controls, tb_dsfd_vm_seq_static):
//   OT_VMSS_MUT_SLICE   slice 3 commits are not counted (a late / dropped physical slice hidden): must FAIL
//   OT_VMSS_MUT_RANGE   the armed range includes row base + nrows (off-by-one end): must FAIL
//   OT_VMSS_MUT_DLAT    the done leaves one cycle early (DLAT 5): must FAIL
//   OT_VMSS_MUT_HASH    the logical row ignores the bank hash (bank = row[4:0]): must FAIL
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_seq_static #(
    parameter integer NSLOT = 8,
    parameter integer VQD = 8
) (
    input  wire [0:0]    ck,
    input  wire [0:0]    rst,            // async die reset, active low (released synchronously, 2 flops)
    input  wire [84:0]   c_cmd,
    output reg  [8:0]    c_done,
    output reg  [1:0]    c_st,
    // native static VM commit observations (dsfd_vm_static512_rel2: slice s bank b at index 32 s + b)
    input  wire [127:0]  o_cv,
    input  wire [1151:0] o_ca,           // 9-bit bank-local address per bank
    input  wire [511:0]  o_cm,           // 4-word mask per bank (slice s = words 4 s .. 4 s + 3)
    // native static VM logical read requests (dsfd_vm_static512_rel2 rq_v / rq_row)
    input  wire [31:0]   o_rv,
    input  wire [447:0]  o_rr,
    // legacy VM engine channel (dsfd_sp_vm_m cv / cd / dv / dt) for the native codes 4..7
    output reg           v_cv,
    output reg  [83:0]   v_cd,
    input  wire          v_dv,
    input  wire [7:0]    v_dt,
    input  wire          v_flt,
    // VERIFIED levels (assertion feeds for the consumers' fixed-start checks)
    output reg           t_inp_su,
    output reg           t_inp_hc
);
    localparam integer DLAT = 6;
    wire clk = ck[0];
    reg [1:0] rq;
    always @(posedge clk or negedge rst[0]) if (!rst[0]) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    wire rn = rq[1];

    // ------------------------------------------------------------------ P0 pin registers
    reg p0_v; reg [83:0] p0_d;
    reg [127:0] q_cv; reg [1151:0] q_ca; reg [511:0] q_cm;
    reg [31:0] q_rv; reg [447:0] q_rr;
    always @(posedge clk) begin
        if (!rn) begin p0_v <= 1'b0; q_cv <= 128'd0; q_rv <= 32'd0; end
        else begin p0_v <= c_cmd[84]; q_cv <= o_cv; q_rv <= o_rv; end
        p0_d <= c_cmd[83:0]; q_ca <= o_ca; q_cm <= o_cm; q_rr <= o_rr;
    end

    // ------------------------------------------------------------------ P1 decode
    wire [2:0]  d_code = p0_d[30:28];
    wire        d_sparse = d_code == 3'd5 || d_code == 3'd7;
    wire        d_cli = !d_sparse && p0_d[27];
    wire [9:0]  d_b16 = d_sparse ? p0_d[25:16] : p0_d[26:17];
    wire [9:0]  d_nr1 = d_sparse ? {3'd0, p0_d[13:7]} : p0_d[16:7];
    wire [1:0]  d_color = p0_d[15:14];
    wire [2:0]  d_s = d_sparse ? {d_code[1], p0_d[27:26]} : {1'b0, d_code[1:0]};
    wire        d_slot = p0_v && (!d_code[2] || d_sparse);
    wire        d_chk = d_slot && (d_sparse ? p0_d[25:7] == 19'h7ffff : (d_b16 == 10'h3ff && d_nr1 == 10'h3ff));
    wire        d_arm = d_slot && !d_chk;
    wire        d_nat = p0_v && d_code[2] && !d_sparse;
    wire [14:0] d_base = {1'b0, d_b16, 4'd0} + (d_sparse ? {13'd0, d_color} : 15'd0);
`ifdef OT_VMSS_MUT_RANGE
    wire [14:0] d_end = d_base + (d_sparse ? {3'd0, d_nr1, 2'd0} : {5'd0, d_nr1}) + 15'd2;
`else
    wire [14:0] d_end = d_base + (d_sparse ? {3'd0, d_nr1, 2'd0} : {5'd0, d_nr1}) + 15'd1;
`endif
    wire [18:0] d_need = {5'd0, d_nr1, 4'd0} + 19'd16;
    // A sparse operand owns only its color within the bounding interval. Holes
    // never contribute commits, early-read matches, or overlap claims.
    function automatic member(input [13:0] row, input [13:0] lo, input [14:0] hi, input sparse);
        `ifdef OT_VMSS_MUT_DENSECOUNT
        member = row >= lo && {1'b0,row} < hi;
`else
        member = row >= lo && {1'b0,row} < hi && (!sparse || row[1:0] == lo[1:0]);
`endif
    endfunction
    function automatic intersects(input [13:0] al, input [14:0] ah, input asp,
                                  input [13:0] bl, input [14:0] bh, input bsp);
        reg [14:0] first; reg [1:0] color;
        begin
            first = al > bl ? {1'b0,al} : {1'b0,bl};
            color = asp ? al[1:0] : bl[1:0];
            if (asp || bsp) first = first + {13'd0,(color-first[1:0])};
            intersects = !(asp && bsp && al[1:0] != bl[1:0]) && first < ah && first < bh;
        end
    endfunction

    // slot state (pin-t ARM / CHECK visible to compares of pin >= t+1)
    reg [NSLOT-1:0] s_open;               // armed, not yet CHECKed
    reg [NSLOT-1:0] s_sparse;
    reg [NSLOT-1:0] s_cl;                 // client
    reg [NSLOT-1:0] s_ok;                 // verified (CHECK passed), until re-armed
    reg [13:0]      s_lo [0:NSLOT-1];
    reg [14:0]      s_hi [0:NSLOT-1];
    reg [18:0]      s_need [0:NSLOT-1];
    reg [NSLOT-1:0] ovl;
    always @* begin : p_ovl integer k;
        for (k = 0; k < NSLOT; k = k + 1)
            ovl[k] = s_open[k] && k != d_s && intersects(s_lo[k], s_hi[k], s_sparse[k], d_base[13:0], d_end, d_sparse);
    end

    // ------------------------------------------------------------------ P1 per-port compares
    // logical row of slice s bank b: row[13:5] = addr, row[4:0] = b ^ {addr[2:0], 2'b00}
    reg [NSLOT*384-1:0] pc;     // registered per slot x port masked counts (0..4)
    reg [NSLOT-1:0] early;
    always @(posedge clk) begin : p_pc integer s, p; reg [13:0] row; reg [8:0] a;
        for (p = 0; p < 128; p = p + 1) begin
            a = q_ca[9*p +: 9];
`ifdef OT_VMSS_MUT_HASH
            row = {a, p[4:0]};
`else
            row = {a, p[4:0] ^ {a[2:0], 2'b00}};
`endif
            for (s = 0; s < NSLOT; s = s + 1)
                pc[384*s + 3*p +: 3] <= (q_cv[p] && s_open[s] && member(row, s_lo[s], s_hi[s], s_sparse[s]))
                            ? ({2'b0, q_cm[4*p]} + {2'b0, q_cm[4*p+1]} + {2'b0, q_cm[4*p+2]} + {2'b0, q_cm[4*p+3]}) : 3'd0;
        end
    end
    always @* begin : p_early integer s, r;
        early = {NSLOT{1'b0}};
        for (s = 0; s < NSLOT; s = s + 1)
            for (r = 0; r < 32; r = r + 1)
                if (q_rv[r] && s_open[s] && member(q_rr[14*r +: 14], s_lo[s], s_hi[s], s_sparse[s])) early[s] = 1'b1;
    end

    // ------------------------------------------------------------------ P2 per slot x slice partial sums
    reg [NSLOT*32-1:0] ps;
    always @(posedge clk) begin : p_p2 reg [7:0] t; integer s, g, b;
        for (s = 0; s < NSLOT; s = s + 1)
            for (g = 0; g < 4; g = g + 1) begin
                t = 8'd0;
                for (b = 0; b < 32; b = b + 1) t = t + {5'd0, pc[384*s + 3*(32*g + b) +: 3]};
`ifdef OT_VMSS_MUT_SLICE
                if (g == 3) t = 8'd0;                                    // MUTANT: slice 3 never counted
`endif
                ps[32*s + 8*g +: 8] <= t;
            end
    end

    // command pipeline P1 -> P6 (fixed: every command takes the same stages)
    reg        c1_v, c2_v, c3_v, c4_v, c5_v;
    reg        c1_chk, c2_chk, c3_chk;
    reg        c1_arm, c2_arm;
    reg [2:0]  c1_s, c2_s, c3_s;
    reg        c1_cl, c2_cl, c3_cl;
    reg [7:0]  c1_t, c2_t, c3_t, c4_t, c5_t;
    reg [18:0] c1_n, c2_n, c3_n;           // the CHECKed arm's nelems, taken at decode (a re-ARM may follow at once)

    // ------------------------------------------------------------------ P3 count, P4 check
    reg [19:0] cnt [0:NSLOT-1];
    reg [NSLOT-1:0] armq;                 // ARM of slot s reached P2 (clear the count with that cycle's old-range sum)
    reg        pend_chk; reg [2:0] pend_s; reg pend_cl;
    reg [10:0] flt;
    // native outstanding
    reg [$clog2(VQD+1):0] vout;
    reg [1:0] vf_s;
    always @(posedge clk) begin : p_main reg [9:0] tot; integer z;
        vf_s <= {vf_s[0], v_flt};
        if (!rn) begin
            s_open <= 0; s_sparse <= 0; s_cl <= 0; s_ok <= 0; flt <= 11'd0; armq <= 0;
            c1_v <= 1'b0; c2_v <= 1'b0; c3_v <= 1'b0; c4_v <= 1'b0; c5_v <= 1'b0; c1_chk <= 1'b0; c2_chk <= 1'b0; c3_chk <= 1'b0;
            c1_arm <= 1'b0; c2_arm <= 1'b0; v_cv <= 1'b0; vout <= 0; t_inp_su <= 1'b0; t_inp_hc <= 1'b0;
            for (z = 0; z < NSLOT; z = z + 1) begin cnt[z] <= 20'd0; s_lo[z] <= 14'd0; s_hi[z] <= 15'd0; s_need[z] <= 19'd0; end
        end else begin
            // ---- P1: slot state
            if (d_arm) begin
                if (s_open[d_s]) flt[4] <= 1'b1;
                if (|ovl) flt[5] <= 1'b1;
                if (d_end > 15'd16384) flt[6] <= 1'b1;
                s_open[d_s] <= 1'b1; s_ok[d_s] <= 1'b0; s_cl[d_s] <= d_cli;
                s_sparse[d_s] <= d_sparse; s_lo[d_s] <= d_base[13:0]; s_hi[d_s] <= d_end; s_need[d_s] <= d_need;
            end
            if (d_chk) begin
                if (!s_open[d_s]) flt[2] <= 1'b1;
                else if ((s_cl[d_s] != d_cli || s_sparse[d_s] != d_sparse)) flt[3] <= 1'b1;
                s_open[d_s] <= 1'b0;      // reads at pin >= CHECK pin + 1 are legal
            end
            if (|early) flt[7] <= 1'b1;
            c1_n <= s_need[d_s]; c1_v <= p0_v; c1_chk <= d_chk; c1_arm <= d_arm; c1_s <= d_s; c1_cl <= d_cli; c1_t <= {p0_d[83], p0_d[6:0]};
            // ---- native forward (pin + 2)
            v_cv <= d_nat; v_cd <= p0_d;
            if (v_dv && vout == 0) flt[8] <= 1'b1;
            if (vout + (d_nat ? 1 : 0) - ((v_dv && vout != 0) ? 1 : 0) > VQD) flt[9] <= 1'b1;
            vout <= vout + (d_nat ? 1 : 0) - ((v_dv && vout != 0) ? 1 : 0);
            if (vf_s[1]) flt[10] <= 1'b1;
            // ---- P2 stage of the command
            c2_n <= c1_n; c2_v <= c1_v; c2_chk <= c1_chk; c2_arm <= c1_arm; c2_s <= c1_s; c2_cl <= c1_cl; c2_t <= c1_t;
            // ---- P3: accumulate (pin-t commits: pc at t+2, ps at t+3, count at t+4)
            for (z = 0; z < NSLOT; z = z + 1) begin
                tot = {2'b0, ps[32*z +: 8]} + {2'b0, ps[32*z + 8 +: 8]} + {2'b0, ps[32*z + 16 +: 8]} + {2'b0, ps[32*z + 24 +: 8]};
                if (c2_arm && c2_s == z) cnt[z] <= {10'd0, tot};       // first new-range sums (pin ARM+1)
                else cnt[z] <= cnt[z] + {10'd0, tot};
                if (!(c2_arm && c2_s == z) && !(c1_arm && c1_s == z) && cnt[z] > {1'b0, s_need[z]}) flt[1] <= 1'b1;
            end
            c3_n <= c2_n; c3_v <= c2_v; c3_chk <= c2_chk; c3_s <= c2_s; c3_cl <= c2_cl; c3_t <= c2_t;
            // ---- P4: CHECK compare (count now holds commits pinned <= CHECK pin)
            if (c3_chk) begin
                if (cnt[c3_s] != {1'b0, c3_n}) flt[0] <= 1'b1;
                // verified unless the slot was re-armed after this CHECK (ARM pin <= CHECK pin + 3)
                else if (!s_open[c3_s] && !(d_arm && d_s == c3_s)) s_ok[c3_s] <= 1'b1;
            end
            c4_v <= c3_v; c4_t <= c3_t;
            c5_v <= c4_v; c5_t <= c4_t;
            begin : p_inp reg su, hc;
                su = 1'b0; hc = 1'b0;
                for (z = 0; z < NSLOT; z = z + 1) begin
                    if (s_ok[z] && !s_cl[z]) su = 1'b1;
                    if (s_ok[z] &&  s_cl[z]) hc = 1'b1;
                end
                t_inp_su <= su; t_inp_hc <= hc;
            end
        end
    end
    // ------------------------------------------------------------------ P6 done / status (die-face flops)
`ifdef OT_VMSS_MUT_DLAT
    wire       dn_v = c4_v;  wire [7:0] dn_t = c4_t;                     // MUTANT: one stage early
`else
    wire       dn_v = c5_v;  wire [7:0] dn_t = c5_t;
`endif
    always @(posedge clk or negedge rst[0])
        if (!rst[0]) begin c_done <= 9'd0; c_st <= 2'b00; end
        else begin c_done <= (dn_v && rn) ? {1'b1, dn_t} : 9'd0; c_st <= {rn, |flt}; end
endmodule
`default_nettype wire
