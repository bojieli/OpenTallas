`timescale 1ns/1ps
`default_nettype none
// Opt-in source-bound IDX256 successor of the static F20 collar; canonical source stays unchanged.
// IDX256R (LH-UNREAD F-P 2026-10-19): opt-in successor of ot_hbm_static_cfg_collar_idx256 for the single IDX instance
// col_idx. The host operand-row ABI (row addresses 0x800-0x805, field bit positions) is UNCHANGED; only the bits a die
// consumer reads are stored and exported. prm is the PACKED 769-bit operand face (operand bit -> prm bit):
//   op[43:0]->prm[43:0]  op[423:51]->prm[416:44]  op[767:766]->prm[418:417]  op[1023:768]->prm[674:419]
//   op[1107:1024]->prm[758:675]  op[1459:1450]->prm[768:759]
// Reserved operand bits (767: op[50:44], [765:424], [1449:1108], [1535:1460]) are neither stored nor exported; a
// configuration frame that writes a NONZERO reserved bit raises the existing sticky fault on the same edge and does
// not load the row (hardware rejects a nonzero reserved field; no silent drop). pw_addr is exported at the real
// 8-bit programme depth: the IDX256 guard already faults every write with lin>=256, so pw_addr[11:8] of the idx256
// master was constant 0 on every successful write. Successful-path latency/edges: unchanged (0 cycles added).
// MUT 12 (bench only): the reserved-field check is disabled (nonzero reserved bits are silently dropped).
// SAFE-DESIGN checklist (owner 10-19): 1 pins: unchanged pin flops on every input/output, 2-stage reset landing PASS;
// 2 reach: soft collar, no new long wire (fewer prm pins) PASS; 3 fanout: cd row bits fan out to <=1 store + 1 OR tree,
// row decode ca[2:0] drives <=8 loads PASS; 4 depth: reserved check = OR of <=254 pin-flop bits (8 levels) + 6:1 row
// select into the existing fault flop, < 20 levels PASS; 5 storage: 769 operand FFs (was 1536), held configuration
// registers loaded only on install, not runtime-indexed reads PASS; 6 floorplan: SYNTH view, 767 fewer output pins
// (fixed by GEN placement) n/a; 7 clock: single clk root as idx256 PASS; 8 schedule: static, 0 added cycles PASS.
// Static F20 target collar for heterogeneous programme/operand layouts (H-NETLIST cp2, 2026-10-15).
// ONE parameterised master serves every target whose local ABI is not the plain PCW row port of
// ot_static_program_target: SU (bank16/row7 programme), SFU (two striped programmes + IO start),
// IDX (programme + per-launch operands) and the TOPK/ARGMAX record issuers.
//
// Configuration only (host elastic boundary ends at the ingress); execution is one launch event plus
// compiler-fixed record cycles. No ready/credit/backpressure on any output.
//
// Target identity: tgt[7:0] is a declared identity strap (the F20 target number of this instance).
// Row address map (ingress F20 row, auto-incremented per 256-bit frame):
//   0x000-0x7FF  programme row: linear L = {page[space], addr[10:0]} into the selected space.
//                Writes must be sequential per space (L == installed high-water mark) or restart at L==0
//                (hwm := 1). This is the finite local installation validator: rows [0,hwm) are written.
//   0x800-0xBFF  operand row r=addr[9:0] (< NPR): prm[r*256+:256] := data   (held operand registers)
//   0xC00-0xDFF  record row r=addr[8:0] (< NREC): {payload221, gomask2, valid1, offset32}
//   0xE00        select: data[7:0]=space (< NS), data[8+:PAGE_W]=page of that space
//   0xE01        need:   data[s*32+:AW+1]=rows that must be installed in space s; data[128]=wait for c_done
//   other        fault
// Descriptor (F28/F2c) for tgt arms the target for the next launch; any later write disarms it.
// Launch (F30): if armed -> ready must hold (else fault); start_v pulses, records run; if not armed -> no-op
// (non-participating target). ready = armed & need written & all operand rows written & hwm>=need & !fault.
// Records: record i (row order, offsets strictly increasing) asserts go[gomask]/rec[] offset_i+1 edges
// after the edge start_v rises (offset 0 = the edge after start_v). A late/non-increasing offset faults.
// active = from launch until records exhausted, TAIL edges after the last start/go, c_busy low and
// (if requested) c_done seen.
// Pins: every input lands in a pin flop, every output is a flop Q (owner rule 19:50).
// Fixed latency (XSER=0): launch_v -> start_v = 2 edges; cfg frame -> pw_we = 2 edges; record go = offset+1
// edges after start_v. XSER=1 adds the synchronised 3:4 crossing (stream pin + hold + 3 serial edges), a fixed value
// for every launch issued on a stream phase >= 555 ps before the next serial edge (the compiler issues F30 there).
module ot_hbm_static_cfg_collar_idx256r #(
    parameter integer PAGE_W=1,   // page bits per programme space (AW = PAGE_W+11)
    parameter integer NS=1,        // programme spaces (1..4)
    parameter integer NPR=6,       // operand rows of 256 b (>=1)
    parameter integer NREC=8,      // record rows (0..512)
    parameter integer NGO=2,       // record go outputs (1..2)
    parameter integer NB=2,        // client busy inputs
    parameter integer NF=5,        // client fault inputs
    parameter integer TAIL=4,
    parameter integer XSER=0,      // 1: core clk is the 3:4 serial domain, broadcast pins on clk_in (stream)
    parameter integer MUT=0,       // bench: 1 skip sequential check, 2 ready ignores need, 3 go one edge early, 4 no event seq check,
                                   //        5 (XSER=1) stream domain left without its reset, 6 (XSER=1) binary event sequence (not Gray),
                                   //        7 (XSER=1) one synchroniser stage short, 8 (XSER=0) core state without the synchronised reset
    parameter integer AW=PAGE_W+11
)(
    input  wire clk, clk_in, rst_n,
    input  wire [7:0] tgt,
    input  wire cfg_v,
    input  wire [7:0] cfg_target,
    input  wire [11:0] cfg_addr,
    input  wire [255:0] cfg_data,
    input  wire desc_v,
    input  wire launch_v,
    input  wire [NB-1:0] c_busy,
    input  wire c_done,
    input  wire [NF-1:0] c_fault,
    output reg  [NS-1:0] pw_we,
    output reg  [7:0] pw_addr,
    output reg  [255:0] pw_data,
    output reg  [768:0] prm,
    output reg  start_v,
    output reg  [NGO-1:0] go,
    output reg  [220:0] rec,
    output reg  ready, active, fault
);
    initial begin
        if (NS != 1 || PAGE_W != 1 || AW != 12 || XSER != 0)
            $fatal(1, "IDX256 collar requires NS1/PAGE_W1/AW12/XSER0");
        if (NPR != 6)
            $fatal(1, "IDX256R packed operand face requires NPR6");
        if (NS<1 || NS>4 || NPR<1 || NPR>1024 || NREC<0 || NREC>512 || NGO<1 || NGO>2 || PAGE_W<1 || AW>31)
            $fatal(1, "ot_hbm_static_cfg_collar: parameter out of range");
    end
    localparam integer SW = (NS>1) ? $clog2(NS) : 1;
    localparam integer RN = (NREC>0) ? NREC : 1;
    localparam integer RW = (NREC>1) ? $clog2(NREC+1) : 1;
    // ---------------- per-domain reset (HBMA-HOST2 2026-10-17)
    // XSER=1: rst_n is a serial-domain (por_serial) pin. It lands in a plain pin flop on clk and a second clk stage;
    // that Q (rst_c_n) is the core-domain reset (in-domain recovery/removal, full serial period). The stream domain
    // gets its own reset: rst_c_n is re-timed by two clk_in flops (rs[0] is a synchroniser stage 1, CDC-bounded in
    // xser_cdc.sdc like the event sequence) and that Q (rst_s_n) clears the clk_in flops. Before this, the raw serial rst_n async-cleared
    // the clk_in flops directly (pin -> RESETN at the tightest 3:4 edge pair: recovery -129 ps, removal -50 ps).
    // Release: core +2 serial edges, stream +2 stream edges after that; no datapath latency changes (configuration
    // events arrive from the elastic host ingress long after power-on reset).
    // XSER=0 (HBM-NATIVE 2026-10-17): the same 2-flop pin synchroniser as the XSER=1 core path. The native pin audit of
    // the closed r1 views (col_sfu capture 455.7 ps, col_idx 499.0 ps > 190) found the raw rst_n pin async-clearing every
    // collar flop; now the pin drives ONE plain clk flop, whose stage-2 Q is the reset of every flop (single domain:
    // rst_s_n = rst_c_n). Assert and release both take +2 clk edges; no datapath / event latency changes (cycles 0).
    // MUT 8 (bench): a mid-run reset does not reach the core state (configuration, armed, hwm, records).
    // XSER=1 elaboration is unchanged (g_rst_sync below, byte-identical text; col_su r3 closed view).
    wire rst_c_n, rst_s_n;
    generate if (XSER == 0) begin : g_rst_same
        reg [1:0] rc;
        always @(posedge clk) rc <= {rc[0], rst_n};
        if (MUT == 8) begin : g_mut8   // bench mutant: only the power-on reset reaches the core state
            reg por_done = 1'b0;
            always @(posedge clk) if (rc[1] === 1'b1) por_done <= 1'b1;
            assign rst_c_n = rc[1] | por_done;
        end else begin : g_rc
            assign rst_c_n = rc[1];
        end
        assign rst_s_n = rc[1];
    end else begin : g_rst_sync
        reg [1:0] rc, rs;
        always @(posedge clk)    rc <= {rc[0], rst_n};
        always @(posedge clk_in) rs <= {rs[0], rc[1]};
        assign rst_c_n = rc[1];
        assign rst_s_n = (MUT == 5) ? 1'b1 : rs[1];
    end endgenerate
    // ---------------- pin flops
    reg cv, dv, lv, done_q, xfault;
    reg [7:0] ct, tg;
    reg [11:0] ca;
    reg [255:0] cd;
    reg [NB-1:0] busy_q;
    reg [NF-1:0] cf_q;
    always @(posedge clk) tg <= tgt;
    always @(posedge clk or negedge rst_c_n)
        if (!rst_c_n) begin done_q <= 0; busy_q <= 0; cf_q <= 0; end
        else begin done_q <= c_done; busy_q <= c_busy; cf_q <= c_fault; end
    generate if (XSER == 0) begin : g_same
        // broadcast pins in the core clock (clk_in is the same root)
        always @(posedge clk) begin ct <= cfg_target; ca <= cfg_addr; cd <= cfg_data; end
        always @(posedge clk or negedge rst_s_n)
            if (!rst_s_n) begin cv <= 0; dv <= 0; lv <= 0; xfault <= 0; end
            else begin cv <= cfg_v; dv <= desc_v; lv <= launch_v; xfault <= 0; end
    end else begin : g_xser
        // 3:4 crossing as a SYNCHRONISED boundary (HBM-COLSU 2026-10-17; replaces the flop-to-flop crossing timed at the
        // tightest edge pair). In the die, clk_in and clk are separate entries of the regional tree (neighbour-relative
        // clocking): every pair of different entries carries the die-skew reserve (setup 150 / hold 100 ps), so a direct
        // stream->serial flop arc has to satisfy 278 ps - 150 setup AND >= 100 ps + hold at once. r2 measured it: FF -81.0 ps
        // on all 282 crossing endpoints (256 h_cd->s_cd, 12 ca, 8 ct, 2 seq, cv/dv/lv, the reset re-timer) and the hold
        // ECO found every one infeasible. Structure now:
        //   stream: pin flops -> held event (h_*: payload + cv/dv/lv) and a 2-bit GRAY event sequence, all launched by
        //           the same stream edge t0; h_* then stays unchanged until the next event (>= 4 stream edges later).
        //   serial: x1 <- h_seq is the synchroniser stage 1 (the only flop that may sample h_seq mid-change; Gray: one
        //           bit changes per event, so x1 resolves to the old or the new code, never a third), x2, x3 follow.
        //           ev = x2 != x3 (synchronised count only, never x1). The capture registers ct/ca/cd/cv/dv/lv load h_*
        //           ONLY when ev (gated capture, COLSU-2 2026-10-17; replaces the free-running sh_* shadows, -279 flops,
        //           same latency): the capture edge is >= 2 serial periods after the edge on which x1 could first see the
        //           code, so h_* has been stable >= 2222 ps - skew and stays so >= 2 more serial edges (events >= 4 stream
        //           edges apart).
        //   CDC constraints: ref_tile cdc_synchronizers (spec; tools/ref_tile/cdc_sync_constraints.py lints the Gray
        //   source, the chain and the gated capture on the elaborated RTL): h_seq -> x1 and rc[1] -> rs[0] bounded
        //   250 / 0 ps, h_* -> capture bounded 833 / 0 ps (-ignore_clock_latency); every other arc fully timed.
        // Latency: +1 serial edge over r2 (x1 -> x2 -> x3). It is fixed for every event whose publish edge t0 is >= 2 VCO
        // ticks (555 ps) before the next serial edge (2 of the 4 stream phases of the common epoch: 250 ps bound + skew +
        // setup fit); the compiler issues F30 on such a phase. Config frames (cfg/desc) tolerate the +-1 serial edge of
        // the other phases (the host boundary is elastic; readiness waits for them). A skipped Gray code (events closer
        // than the serial edges can see) faults, as before.
        reg pv_cv, pv_dv, pv_lv; reg [7:0] p_ct; reg [11:0] p_ca; reg [255:0] p_cd;
        reg [1:0] h_seq; reg h_cv, h_dv, h_lv; reg [7:0] h_ct; reg [11:0] h_ca; reg [255:0] h_cd;
        always @(posedge clk_in) begin p_ct <= cfg_target; p_ca <= cfg_addr; p_cd <= cfg_data; end
        always @(posedge clk_in or negedge rst_s_n)
            if (!rst_s_n) begin pv_cv <= 0; pv_dv <= 0; pv_lv <= 0; h_seq <= 0; h_cv <= 0; h_dv <= 0; h_lv <= 0; end
            else begin
                pv_cv <= cfg_v; pv_dv <= desc_v; pv_lv <= launch_v;
                if (pv_cv || pv_dv || pv_lv) begin
                    // Gray increment 00 -> 01 -> 11 -> 10 -> 00 (MUT 6: binary, which the serial Gray decode faults)
                    h_seq <= (MUT == 6) ? h_seq + 1'b1 : {h_seq[0], ~h_seq[1]};
                    h_cv <= pv_cv; h_dv <= pv_dv; h_lv <= pv_lv;
                end
            end
        // held payload: plain enabled flops outside the async-reset block (HBMA-HOST 2026-10-17). Inside it, synthesis
        // folded the serial-domain rst_n into the stream-domain DFFE enable (a reset on the datapath, crossing domains;
        // OT_MULTI_ROOT). pv_* are cleared by the stream reset, so the enable is low under reset exactly as before: bit-identical.
        always @(posedge clk_in)
            if (pv_cv || pv_dv || pv_lv) begin h_ct <= p_ct; h_ca <= p_ca; h_cd <= p_cd; end
        reg [1:0] x1_seq, x2_seq, x3_seq;
        always @(posedge clk or negedge rst_c_n)
            if (!rst_c_n) begin x1_seq <= 0; x2_seq <= 0; x3_seq <= 0; end
            else begin x1_seq <= h_seq; x2_seq <= x1_seq; x3_seq <= x2_seq; end
        // MUT 7: one synchroniser stage short: captures on the edge after x1 first saw the code
        wire [1:0] q_new = (MUT == 7) ? x1_seq : x2_seq;
        wire [1:0] q_old = (MUT == 7) ? x2_seq : x3_seq;
        wire ev = q_new != q_old;
        wire [1:0] b_new = {q_new[1], q_new[1] ^ q_new[0]}, b_old = {q_old[1], q_old[1] ^ q_old[0]};
        always @(posedge clk) if (ev) begin ct <= h_ct; ca <= h_ca; cd <= h_cd; end
        always @(posedge clk or negedge rst_c_n)
            if (!rst_c_n) begin cv <= 0; dv <= 0; lv <= 0; xfault <= 0; end
            else begin
                cv <= ev && h_cv; dv <= ev && h_dv; lv <= ev && h_lv;
                xfault <= ev && (b_new - b_old) != 2'd1 && MUT != 4;
            end
    end endgenerate
    // ---------------- state
    reg [SW-1:0] sel;
    reg [PAGE_W-1:0] page [0:NS-1];
    reg [AW:0] hwm [0:NS-1];
    reg [AW:0] need [0:NS-1];
    reg need_set, wait_mask, wait_done;
    reg [NPR-1:0] loaded;
    reg armed, run;
    reg [31:0] cnt;
    reg [RW-1:0] rptr;
    reg [7:0] tail;
    reg [31:0] r_off [0:RN-1];
    reg [RN-1:0] r_val;
    reg [1:0] r_go [0:RN-1];
    reg [220:0] r_pay [0:RN-1];
    wire hit = cv && ct == tg;
    wire dhit = dv && ct == tg;
    wire [AW:0] lin = {1'b0, page[sel], ca[10:0]};
    // Source-bound IDX256 installation contract. MUT9/10/11 independently disable
    // write/page/need guards for the negative bench; production MUT0 enforces all.
    wire depth_write_bad = !ca[11] && (lin >= 13'd256) && MUT != 9;
    wire depth_page_bad = ca == 12'hE00 && (|cd[8 +: PAGE_W]) && MUT != 10;
    wire depth_need_bad = ca == 12'hE01 && cd[31:0] > 32'd256 && MUT != 11;
    wire install_depth_bad = hit && (depth_write_bad || depth_page_bad || depth_need_bad);
    // IDX256R reserved operand fields: nonzero data in a reserved bit of operand row ca[2:0] faults (MUT 12 disables).
    reg resv_nz;
    always @* begin
        case (ca[2:0])
            3'd0: resv_nz = |cd[50:44];
            3'd1: resv_nz = |cd[255:168];
            3'd2: resv_nz = |cd[253:0];
            3'd4: resv_nz = |cd[255:84];
            3'd5: resv_nz = (|cd[169:0]) || (|cd[255:180]);
            default: resv_nz = 1'b0;
        endcase
    end
    wire install_resv_bad = hit && ca[11:10] == 2'b10 && ca[9:3] == 7'd0 && resv_nz && MUT != 12;
    reg inst_ok;
    integer s;
    always @* begin
        inst_ok = need_set && (&loaded);
        for (s = 0; s < NS; s = s + 1) if (hwm[s] < need[s] && MUT != 2) inst_ok = 0;
    end
    wire recs_done = (NREC == 0) || (rptr >= NREC) || !r_val[rptr];
    wire [31:0] cur_off = r_off[(NREC == 0) ? 0 : rptr];
    wire [31:0] cmp_cnt = (MUT == 3) ? cnt + 1 : cnt;
    integer k;
    always @(posedge clk or negedge rst_c_n) begin
        if (!rst_c_n) begin
            pw_we <= 0; start_v <= 0; go <= 0; ready <= 0; active <= 0; fault <= 0;
            sel <= 0; need_set <= 0; wait_mask <= 0; wait_done <= 0; loaded <= 0; armed <= 0; run <= 0;
            cnt <= 0; rptr <= 0; tail <= 0; r_val <= 0;
            for (k = 0; k < NS; k = k + 1) begin hwm[k] <= 0; need[k] <= 0; page[k] <= 0; end
        end else begin
            pw_we <= 0; start_v <= 0; go <= 0;
            if (|cf_q || xfault) fault <= 1;
            // ------------ configuration frames
            if (hit) begin
                armed <= 0;
                if (run) fault <= 1;
                else if (install_depth_bad || install_resv_bad) fault <= 1;
                else if (!ca[11]) begin
                    if (lin == hwm[sel] || MUT == 1) begin
                        if (hwm[sel][AW]) fault <= 1;
                        else begin pw_we[sel] <= 1; pw_addr <= lin[7:0]; pw_data <= cd; hwm[sel] <= lin + 1'b1; end
                    end else if (lin == 0) begin
                        pw_we[sel] <= 1; pw_addr <= 0; pw_data <= cd; hwm[sel] <= 1;
                    end else fault <= 1;
                end else if (ca[11:10] == 2'b10) begin
                    if (ca[9:0] >= NPR) fault <= 1;
                    else begin
                        case (ca[2:0])
                            3'd0: begin prm[43:0] <= cd[43:0]; prm[248:44] <= cd[255:51]; end
                            3'd1: prm[416:249] <= cd[167:0];
                            3'd2: prm[418:417] <= cd[255:254];
                            3'd3: prm[674:419] <= cd[255:0];
                            3'd4: prm[758:675] <= cd[83:0];
                            default: prm[768:759] <= cd[179:170];
                        endcase
                        loaded[ca[9:0]] <= 1;
                    end
                end else if (ca[11:9] == 3'b110) begin
                    if (ca[8:0] >= NREC) fault <= 1;
                    else begin
                        r_off[ca[8:0]] <= cd[31:0]; r_val[ca[8:0]] <= cd[32];
                        r_go[ca[8:0]] <= cd[34:33]; r_pay[ca[8:0]] <= cd[255:35];
                        if (NGO < 2 && cd[34]) fault <= 1;
                    end
                end else if (ca == 12'hE00) begin
                    if (cd[7:0] >= NS) fault <= 1;
                    else begin sel <= cd[SW-1:0]; page[cd[SW-1:0]] <= cd[8 +: PAGE_W]; end
                end else if (ca == 12'hE01) begin
                    for (k = 0; k < NS; k = k + 1) need[k] <= cd[k*32 +: AW+1];
                    wait_mask <= cd[128]; need_set <= 1;
                end else fault <= 1;
            end
            if (dhit) begin
                if (run || hit) fault <= 1; else armed <= 1;
            end
            // ------------ launch: only an armed target participates
            if (lv && armed) begin
                armed <= 0;
                if (!(inst_ok && !fault && !run && !install_depth_bad && !install_resv_bad)) fault <= 1;
                else begin
                    start_v <= 1; run <= 1; cnt <= 0; rptr <= 0; tail <= TAIL[7:0];
                    wait_done <= wait_mask;
                end
            end
            // ------------ execution: fixed record calendar
            if (run) begin
                cnt <= cnt + 1'b1;
                if (tail != 0 && !start_v) tail <= tail - 1'b1;
                if (done_q) wait_done <= 0;
                if (!recs_done) begin
                    if (cur_off == cmp_cnt) begin
                        go <= r_go[rptr][NGO-1:0]; rec <= r_pay[rptr]; rptr <= rptr + 1'b1; tail <= TAIL[7:0];
                    end else if (cur_off < cnt) fault <= 1;
                end else if (!start_v && tail == 0 && !(|busy_q) && !wait_done && go == 0) run <= 0;
            end
            active <= run || (lv && armed);
            ready <= armed && inst_ok && !fault && !run && !hit;
        end
    end
endmodule
`default_nettype wire
