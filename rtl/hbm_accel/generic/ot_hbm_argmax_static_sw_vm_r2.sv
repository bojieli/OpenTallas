`timescale 1ns/1ps
`default_nettype none
// ot_hbm_argmax_static_sw_vm_r2 (HBM-TILES-B 10-17): successor of ot_hbm_argmax_static_sw_vm (= ot_hbm_argmax_static, SW
// slice, no STREAM wiring) after its pre-route gate (hbm_argmax_swvm, HBM-C): rst_n port 2,137 loads, 258 input->register
// endpoints > 3 levels (o_base -> legal_q 16 lv, vm_rr -> flt 9 lv), and 2.9k pins (vm_rr 2,056 b) that cannot fit the
// r6 slot 118.8 x 118.8 at <= 6 pins/um. Same engine (ot_hgi_argmax18_m unchanged), same calendar shape, three changes:
//  1. INPUT PIN REGISTERS on every input (command, vm_rr, cr): +1 edge from go to everything; the slice ACK counts the cr
//     pin register (ACK = 13 for the measured 12-edge slice ack). Output pins were already registers.
//  2. RESET RELAY ot_rst_relay (3 regions: control/writer, VM reader, engine); data registers (vm_rq sector, cq payload)
//     carry no reset, only their valid bits do.
//  3. NARROW VM RESPONSE: vm_rr is {lane valid8, data256} (264 b) from ot_hbm_idx_vm_share_static_am, which does the
//     8:1 sector select in the four bank-pair leaves; capture moves VMX = 5 edges later (4 merge hops + pin register).
//     The per-lane valid check (rd_bad) is unchanged. vm_rq stays 8 x 17 b (one lane per edge; sector shared):
//     vm_rq[17l+:17] = {rq_v[l], rq_d} -- the 16-bit {mirror, sector} is registered once and fanned to the 8 lanes.
// Timeline vs the original with go at G: S = G+4; capture S+j+13; L, W0, W1, done all +1+VMX; done = W1 + ACK + 1.
// Pins: 136 vm_rq + 264 vm_rr + 338 cq + 2 + 274 cr + ~110 command/status = ~1.13k (118.8 sq at <= 2.4 pins/um).
// MUT: as ot_hbm_argmax_static (1 id offset, 2 capture early, 3 no second O word) and SWMUT 1/2 as the sw_vm wrapper.
// busy EXPORT FLOP (HBM-NATIVE 10-17, after the routed native pin audit of hbm_argmax_swvm_r2_1017-r2-e4dc0b651: busy launch
// 222.4 > 220 ps): the busy PORT was the FSM state flop itself, which also gates go_p, s_beat and flt inside the tile, so
// its Q net is loaded and the flop is placed by the internal logic, not at the pin. The FSM keeps its own flop busy_i;
// the port is driven by a dedicated (* keep *) export flop busy_x that receives the SAME next state with the SAME reset
// on every edge (busy_x(t) == busy_i(t) for all t): 0 cycles, bit-identical at the pin (lockstep bench
// tb_argmax_r2_busy_export vs the closed e4dc0b651 RTL; mutant OT_ARGMAX_BUSY_EXPORT_MUT drops one clear and is rejected).
module ot_hbm_argmax_static_sw_vm_r2 #(
    parameter integer TP = 192,
    parameter integer RANK_W = (TP<=1?1:$clog2(TP)),
    parameter integer MUT = 0,
    parameter integer SWMUT = 0,
    parameter integer ACK = 13,
    parameter integer ELAT = 14,
    parameter integer VMX = 5,
    // SID (HBM-BIND B2 2026-10-24): quadrant strap = the quadrant whose VM (read group 4 share in the IDX root, hub cq/cr)
    // this engine reads and writes: a (non-mirror) and o sectors must equal it. Default 0 = the as-built SW engine (the
    // literal localparam sid = 0), bit-identical. B2 (NW + NE die): 3 (NE). No latency change.
    parameter [1:0] SID = 2'd0,
    // CNTW (HBM-BIND B2 2026-10-24): width of the E_WAIT / E_END edge counter (all-ones = the STREAM "armed" sentinel).
    // 6 (as built, bit-identical) holds ACK / ELAT <= 62. The B2 die's hub echo crosses the two-stop VM ring (ACK = 13 +
    // CR_RT, tools/hbm_b2/b2_delays.py: 111 on B2m), so the counter widens to 8 automatically when ACK or ELAT > 62.
    // Same edges for every ACK / ELAT (bench rtl/test/hbm_netlist_v16/run_argmax_r2_ack.sh; mutant = CNTW 6 at ACK 111).
    parameter integer CNTW = (ACK > 62 || ELAT > 62) ? 8 : 6
)(
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    die_id,
    input  wire          go,
    input  wire          mode,            // 0 VM; 1 STREAM = unwired on this die -> record fault
    input  wire [17:0]   imm_a,
    input  wire          a_mirror,
    input  wire [17:0]   a_base,
    input  wire [17:0]   n,
    input  wire [17:0]   o_base,
    input  wire [15:0]   o_is,
    output wire [135:0]  vm_rq,
    input  wire [263:0]  vm_rr,           // {lane valid8, data256} from ot_hbm_idx_vm_share_static_am
    output wire [337:0]  cq,
    output reg  [1:0]    cq_seq,
    input  wire [273:0]  cr,
    output wire          busy,
    output reg           done, fault, nan_flag
);
    localparam [1:0] sid = SID;
    reg busy_i;                                                         // FSM state (internal loads)
    (* keep = "true", dont_touch = "true" *) reg busy_x;           // pin export copy (drives only the busy port)
    assign busy = busy_x;
    // ---------------------------------------------------------------- reset relay (3 regions)
    wire [2:0] rr_n;
    ot_rst_relay #(.REGIONS(3)) u_rst(.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    wire rst_ctl = rr_n[0], rst_rd = rr_n[1], rst_eng = rr_n[2];
    // ---------------------------------------------------------------- input pin registers
    reg go_p, mode_p, am_p; reg [17:0] imm_p, ab_p, n_p, ob_p; reg [15:0] ois_p; reg [7:0] die_p;
    reg [263:0] rr_p; reg [273:0] cr_p;
    always @(posedge clk or negedge rst_ctl) if (!rst_ctl) go_p <= 1'b0; else go_p <= go;
    always @(posedge clk) begin
        mode_p <= (SWMUT == 1) ? mode : 1'b0;                          // engine sees VM mode only
        imm_p <= ((SWMUT == 1) ? 1'b0 : (SWMUT == 2) ? 1'b1 : mode) ? 18'h3FFFF : imm_a;   // STREAM record = ILLEGAL
        am_p <= a_mirror; ab_p <= a_base; n_p <= n; ob_p <= o_base; ois_p <= o_is; die_p <= die_id;
        rr_p <= vm_rr; cr_p <= cr;
    end
    wire [7:0] die_id_q = die_p;
    // ---------------------------------------------------------------- outputs
    reg [7:0] rq_v; reg [15:0] rq_d; reg cq_v; reg [336:0] cq_d;
    for (genvar l = 0; l < 8; l = l + 1) begin : g_rq assign vm_rq[17*l +: 17] = {rq_v[l], rq_d}; end   // sector is don't-care when !v
    assign cq = {cq_v, cq_d};
    localparam [3:0] E_IDLE=0, E_CHK=1, E_ROW=2, E_RD=3, E_WAIT=4, E_W0=5, E_W1=6, E_END=7;
    reg [3:0] st; reg [CNTW-1:0] cnt; reg flt;
    localparam [CNTW-1:0] CSENT = {CNTW{1'b1}};
    reg mode_q, am_q; reg [17:0] imm_q, ab_q, n_q, ob_q; reg [15:0] ois_q; reg legal_q;
    wire legal = n_p != 18'd0 && imm_p < 18'd262143 &&
                 (mode_p || (am_p ? ab_p[17:16] == 2'd0 : ab_p[17:16] == sid)) &&
                 ob_p[17:16] == sid && ((ob_p + {2'd0, ois_p}) >> 16) == {16'd0, sid};
    always @(posedge clk) if (go_p && !busy_i) begin
        mode_q <= mode_p; am_q <= am_p; imm_q <= imm_p; ab_q <= ab_p; n_q <= n_p; ob_q <= ob_p;
        ois_q <= ois_p; legal_q <= legal;
    end
    // ---------------------------------------------------------------- VM reader (one sector per edge)
    reg [14:0] i_sec, i_left; reg i_first; reg [17:0] le;
    wire rd_now = st == E_RD;
    wire rd_last = rd_now && i_left == 15'd0;
    reg [11:0] dp [0:8+VMX];              // {v, bank3, first, last, off3, lastw3}
    wire [11:0] di = dp[(MUT == 2) ? 6+VMX : 7+VMX];
    reg cap_v, cap_first, cap_last; reg [2:0] cap_off, cap_lastw; reg [255:0] cap_d;
    always @(posedge clk or negedge rst_rd)
        if (!rst_rd) begin rq_v <= 8'd0; cap_v <= 1'b0; for (integer d = 0; d < 9+VMX; d = d + 1) dp[d] <= 12'd0; end
        else begin
            rq_v <= 8'd0; dp[0] <= 12'd0;
            for (integer d = 1; d < 9+VMX; d = d + 1) dp[d] <= dp[d-1];
            if (rd_now) begin
                rq_v[i_sec[2:0]] <= 1'b1;
                dp[0] <= {1'b1, i_sec[2:0], i_first, rd_last, i_first ? ab_q[2:0] : 3'd0, le[2:0]};
            end
            cap_v <= di[11];
        end
    always @(posedge clk) begin rq_d <= {am_q, i_sec}; cap_d <= rr_p[255:0]; {cap_first, cap_last, cap_off, cap_lastw} <= di[7:0]; end
    reg rd_bad;
    always @* begin
        rd_bad = 1'b0;
        for (integer l = 0; l < 8; l = l + 1) if (rr_p[256+l] != (di[11] && di[10:8] == 3'(l))) rd_bad = 1'b1;
    end
    // ---------------------------------------------------------------- stream pins
    wire [522:0] as_q = 523'd0;           // SW VM die: no STREAM wiring (as ot_hbm_argmax_static_sw_vm)
    // ---------------------------------------------------------------- engine (closed, unchanged)
    reg e_v, e_last, e_be; reg [7:0] e_m; reg [255:0] e_vals, e_bias;
    wire s_beat = busy_i && mode_q && as_q[0];
    always @(posedge clk or negedge rst_rd)
        if (!rst_rd) begin e_v <= 1'b0; e_last <= 1'b0; end
        else begin
            e_v <= mode_q ? s_beat : cap_v; e_last <= mode_q ? (s_beat && as_q[1]) : (cap_v && cap_last);
        end
    always @(posedge clk) begin
        if (mode_q) begin e_m <= as_q[9:2]; e_vals <= as_q[265:10]; e_bias <= as_q[521:266]; e_be <= as_q[522]; end
        else begin
            for (integer l = 0; l < 8; l = l + 1)
                e_m[l] <= (!cap_first || l[2:0] >= cap_off) && (!cap_last || l[2:0] <= cap_lastw);
            e_vals <= cap_d; e_bias <= 256'd0; e_be <= 1'b0;
        end
    end
    wire o_v, o_nan, o_f, o_rf; wire [17:0] o_idx; wire [31:0] o_val;
    ot_hgi_argmax18_m #(.LP(8), .GENERIC18(1), .RANK_W(RANK_W)) u_e (.clk(clk), .rst_n(rst_eng), .in_v(e_v), .in_last(e_last),
        .in_bias_en(e_be), .in_mask(e_m), .in_vals(e_vals), .in_bias(e_bias), .cfg_rank(RANK_W'(die_id_q)), .cfg_imm_a(imm_q),
        .out_v(o_v), .out_idx(o_idx), .out_nan(o_nan), .fault(o_f), .out_range_fault(o_rf), .out_value(o_val));
    // ---------------------------------------------------------------- result and writes
    reg [31:0] res_val, res_id; reg res_bad;
    wire [17:0] wa = (st == E_W1) ? ob_q + {2'd0, ois_q} : ob_q;
    wire [31:0] wdat = (st == E_W1) ? res_id : res_val;
    reg [2:0] ap [0:ACK]; reg cr_v; reg [15:0] cr_tag; reg cr_we; reg wr_now;
    wire [2:0] ax = ap[ACK-1];
    wire ack_bad = cr_v != ax[2] || (ax[2] && (cr_tag != {14'h1E80, ax[1:0]} || !cr_we));
    always @(posedge clk or negedge rst_ctl)
        if (!rst_ctl) begin cr_v <= 1'b0; for (integer d = 0; d <= ACK; d = d + 1) ap[d] <= 3'd0; end
        else begin
            cr_v <= cr_p[273]; ap[0] <= {wr_now, cq_seq};
            for (integer d = 1; d <= ACK; d = d + 1) ap[d] <= ap[d-1];
        end
    always @(posedge clk) begin cr_tag <= cr_p[272:257]; cr_we <= cr_p[256]; end
    wire kill = flt || res_bad || (MUT == 3 && st == E_W1);
    always @(posedge clk) if (st == E_W0 || st == E_W1) cq_d <= {1'b1, 11'd0, 1'b0, wa[17:3], 5'd0, {8{wdat}},
                           kill ? 32'd0 : (32'hF << (4 * wa[2:0])), {14'h1E80, (st == E_W1) ? 2'd1 : 2'd0}};
    always @(posedge clk or negedge rst_ctl) begin
        if (!rst_ctl) begin
            st <= E_IDLE; busy_i <= 1'b0; busy_x <= 1'b0; done <= 1'b0; fault <= 1'b0; nan_flag <= 1'b0; flt <= 1'b0; cq_v <= 1'b0;
            cq_seq <= 2'd0; wr_now <= 1'b0; cnt <= '0; res_bad <= 1'b0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cq_v <= 1'b0; wr_now <= 1'b0;
            if (busy_i && st != E_CHK && (ack_bad || (!mode_q && rd_bad))) flt <= 1'b1;
            if (o_v && !(st == E_WAIT && cnt == '0)) flt <= 1'b1;      // engine out must be exactly on L+ELAT
            case (st)
                E_IDLE: if (go_p) begin busy_i <= 1'b1; busy_x <= 1'b1; st <= E_CHK; end
                E_CHK: begin
                    flt <= 1'b0; res_bad <= 1'b0; le <= ab_q + n_q - 18'd1;
                    if (!legal_q) begin fault <= 1'b1; busy_i <= 1'b0; busy_x <= 1'b0; st <= E_IDLE; end
                    else st <= mode_q ? E_WAIT : E_ROW;
                    cnt <= CSENT;                          // STREAM: armed by the last beat
                end
                E_ROW: begin i_sec <= ab_q[17:3]; i_left <= le[17:3] - ab_q[17:3]; i_first <= 1'b1; st <= E_RD; end
                E_RD: begin
                    i_sec <= i_sec + 15'd1; i_left <= i_left - 15'd1; i_first <= 1'b0;
                    if (rd_last) st <= E_WAIT;
                end
                E_WAIT: begin
                    if (e_v && e_last) cnt <= CNTW'(ELAT - 1);   // the engine samples the last beat at this edge: L
                    else if (cnt != CSENT && cnt != '0) cnt <= cnt - 1'b1;
                    if (cnt == '0) begin                       // L + ELAT: engine out_v
                        if (!o_v) flt <= 1'b1;
                        res_val <= o_val;
                        res_id <= {14'd0, o_idx} - ((MUT == 1 || mode_q) ? 32'd0 : {29'd0, ab_q[2:0]});
                        res_bad <= o_f || o_rf;
                        if (o_nan) nan_flag <= 1'b1;
                        st <= E_W0;
                    end
                end
                E_W0, E_W1: begin                               // W0 = L+ELAT+1, W1 = W0+1
                    wr_now <= 1'b1; cq_seq <= (st == E_W1) ? 2'd1 : 2'd0;
                    cq_v <= 1'b1;
                    if (st == E_W1) begin cnt <= CNTW'(ACK); st <= E_END; end else st <= E_W1;
                end
                E_END: if (cnt == '0) begin                  // W1 + ACK + 1
                    done <= !(flt || res_bad || ack_bad); fault <= flt || res_bad || ack_bad; busy_i <= 1'b0;
`ifndef OT_ARGMAX_BUSY_EXPORT_MUT
                    busy_x <= 1'b0;
`endif
                    st <= E_IDLE;
                end else cnt <= cnt - 1'b1;
                default: st <= E_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
