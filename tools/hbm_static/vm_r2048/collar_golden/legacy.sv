`timescale 1ns/1ps
`default_nettype none
// Opt-in source-bound IDX256 successor of the static F20 collar; canonical source stays unchanged.
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
// FAN32 (L2H-PAD 2026-10-19, SAFE-DESIGN review of the GEN2e3 IDX256R master): the packed face is ported onto the
// FAN32 structure of the closed-timing IDX256 successor (hdie_col_idx256_1019, 0 nets > 32 loads mapped): 16 protected
// 16-bit banks with local kept cv/ct/ca copies, registered next-onehot record select, private counter/run copies and 25
// kept reset stage-2 copies. Operand words store ONLY the 769 used bits (masked words; reserved bits have no flop).
// The central reserved-field check (OR of <=254 cd pin-flop bits + 6:1 row select) inhibits the banked operand load on
// the same edge and raises the sticky fault exactly as the FAN32=0 path. Mutants: 12 reserved check off (as GEN2e3),
// 14 record select rotated (was idx256 MUT 12), 13 lost counter carry, 9/10/11 depth guards, 1/2/3/8 as canonical.
// FAN32 defaults to 0 (GEN2e3 synth elaboration semantics); the tile kits hdie_col_idx256r_a/_b set FAN32=1.
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
    parameter integer FAN32=0,    // opt-in same-edge retained configuration/read selector banks
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
    output wire  [7:0] pw_addr,
    output wire  [255:0] pw_data,
    output wire  [768:0] prm,
    output reg  start_v,
    output reg  [NGO-1:0] go,
    output wire  [220:0] rec,
    output reg  ready, active, fault
);
    initial begin
        if (FAN32 != 0 && (NPR != 6 || NREC != 8 || NGO != 2))
            $fatal(1, "IDX256 FAN32 requires production NPR6/NREC8/NGO2");
        if (NPR != 6)
            $fatal(1, "IDX256R packed operand face requires NPR6");
        if (NS != 1 || PAGE_W != 1 || AW != 12 || XSER != 0)
            $fatal(1, "IDX256 collar requires NS1/PAGE_W1/AW12/XSER0");
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
    wire rst_c_n, rst_s_n, rst_stage1;
    generate if (XSER == 0) begin : g_rst_same
        reg [1:0] rc;
        assign rst_stage1=rc[0];
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
        assign rst_stage1=rc[0];
        always @(posedge clk)    rc <= {rc[0], rst_n};
        always @(posedge clk_in) rs <= {rs[0], rc[1]};
        assign rst_c_n = rc[1];
        assign rst_s_n = (MUT == 5) ? 1'b1 : rs[1];
    end endgenerate
    wire [24:0] regional_reset;
    generate if(FAN32!=0)begin:g_reset_copies
        (* keep *) reg [24:0] rr;
        always @(posedge clk)rr<={25{rst_stage1}};
        assign regional_reset=rr;
    end else assign regional_reset={25{rst_c_n}};
    endgenerate
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
    reg armed;
    (* keep *) reg run;
    wire [15:0] run_copies;
    wire run_next_phase;
    generate if(FAN32!=0)begin:g_run_copies
        (* keep *) reg [15:0] rq;
        always @(posedge clk or negedge regional_reset[18])
            if(!regional_reset[18])rq<=0;else rq<={16{run_next_phase}};
        assign run_copies=rq;
    end else assign run_copies=0;
    endgenerate
    reg [31:0] cnt;
    reg [RW-1:0] rptr;
    reg [7:0] tail;
    reg [31:0] r_off [0:RN-1];
    reg [RN-1:0] r_val;
    reg [1:0] r_go [0:RN-1];
    reg [220:0] r_pay [0:RN-1];
    reg [AW-1:0] pw_addr_raw;
    reg [255:0] pw_data_raw;
    reg [NPR*256-1:0] prm_raw;
    reg [220:0] rec_raw;
    wire [AW-1:0] pw_addr_banked;
    wire [255:0] pw_data_banked;
    wire [NPR*256-1:0] prm_banked;
    wire [220:0] rec_banked;
    wire [255:0] selected_record;
    wire [AW-1:0] pw_addr_full = FAN32 ? pw_addr_banked : pw_addr_raw;
    assign pw_addr = pw_addr_full[7:0];   // IDX256 guard: lin<256 on every successful write
    assign pw_data = FAN32 ? pw_data_banked : pw_data_raw;
    wire [NPR*256-1:0] prm_full = FAN32 ? prm_banked : prm_raw;
    // packed operand face (LH-UNREAD F-P): used operand bits in ascending order
    assign prm = {prm_full[1459:1450], prm_full[1107:766], prm_full[423:51], prm_full[43:0]};
    assign rec = FAN32 ? rec_banked : rec_raw;
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
    wire resv_row_bad = ca[11:10] == 2'b10 && ca[9:3] == 7'd0 && resv_nz && MUT != 12;
    wire install_resv_bad = hit && resv_row_bad;
    reg inst_ok;
    integer s;
    always @* begin
        inst_ok = need_set && (&loaded);
        for (s = 0; s < NS; s = s + 1) if (hwm[s] < need[s] && MUT != 2) inst_ok = 0;
    end
    wire recs_done = (NREC == 0) || (rptr >= NREC) || !selected_record[32];
    wire [31:0] cur_off = selected_record[31:0];
    wire [31:0] cmp_cnt = (MUT == 3) ? cnt + 1 : cnt;
    wire launch_ok = lv && armed && inst_ok && !fault && !run && !install_depth_bad && !install_resv_bad;
    wire record_step = run && !recs_done && cur_off == cmp_cnt;
    wire [RW-1:0] rptr_next = !regional_reset[23] ? {RW{1'b0}} :
        record_step ? rptr + 1'b1 : launch_ok ? {RW{1'b0}} : rptr;
    wire [3:0] count_run;
    wire [31:0] count_increment=(MUT==13)?{cnt[31:8],(cnt[7:0]+8'd1)}:cnt+32'd1;
    wire [31:0] count_unreset_next;
    generate if(FAN32!=0)begin:g_counter_flags
        (* keep *) reg [3:0] cr;
        always @(posedge clk or negedge regional_reset[24])
            if(!regional_reset[24])cr<=0;else cr<={4{run_next_phase}};
        assign count_run=cr;
    end else assign count_run={4{run}};
    endgenerate
    genvar cb;
    generate for(cb=0;cb<4;cb=cb+1)begin:g_counter_chunk
        assign count_unreset_next[cb*8+:8]=count_run[cb]?count_increment[cb*8+:8]:launch_ok?8'd0:cnt[cb*8+:8];
    end endgenerate
    wire [31:0] cnt_next={regional_reset[24]?count_unreset_next[31:16]:16'd0,
                         regional_reset[22]?count_unreset_next[15:0]:16'd0};
    wire programme_accept = hit && !run && !ca[11] && !depth_write_bad &&
        (((lin == hwm[sel] || MUT == 1) && !hwm[sel][AW]) ||
         (lin != hwm[sel] && MUT != 1 && lin == 0));
    generate if (FAN32 != 0) begin : g_fan32
        ot_hbm_idx256r_banks #(.AW(AW),.MUT(MUT)) u_banks(
            .clk(clk),.rst_c_n(rst_c_n),.regional_reset(regional_reset[16:0]),.cfg_v(cfg_v),.cfg_target(cfg_target),
            .cfg_addr(cfg_addr),.cd(cd),.tg(tg),.run_state(run_copies),.recs_done(recs_done),
            .cur_off(cur_off),.cnt_next(cnt_next),.rptr_next(rptr_next),
            .programme_accept(programme_accept),.resv_bad(resv_row_bad),.lin(lin[AW-1:0]),
            .selected_record(selected_record),.pw_addr(pw_addr_banked),.pw_data(pw_data_banked),
            .prm(prm_banked),.rec(rec_banked));
    end else begin : g_original_banks
        assign selected_record = {r_pay[rptr],r_go[rptr],r_val[rptr],r_off[(NREC == 0) ? 0 : rptr]};
        assign pw_addr_banked = 0;
        assign pw_data_banked = 0;
        assign prm_banked = 0;
        assign rec_banked = 0;
    end endgenerate
    generate if(FAN32==0)begin:g_original_control
    assign run_next_phase=1'b0;
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
                        else begin pw_we[sel] <= 1; pw_addr_raw <= lin[AW-1:0]; pw_data_raw <= cd; hwm[sel] <= lin + 1'b1; end
                    end else if (lin == 0) begin
                        pw_we[sel] <= 1; pw_addr_raw <= 0; pw_data_raw <= cd; hwm[sel] <= 1;
                    end else fault <= 1;
                end else if (ca[11:10] == 2'b10) begin
                    if (ca[9:0] >= NPR) fault <= 1;
                    else begin prm_raw[ca[9:0]*256 +: 256] <= cd; loaded[ca[9:0]] <= 1; end
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
                        go <= selected_record[33 +: NGO]; rec_raw <= selected_record[255:35]; rptr <= rptr + 1'b1; tail <= TAIL[7:0];
                    end else if (cur_off < cnt) fault <= 1;
                end else if (!start_v && tail == 0 && !(|busy_q) && !wait_done && go == 0) run <= 0;
            end
            active <= run || (lv && armed);
            ready <= armed && inst_ok && !fault && !run && !hit;
        end
    end
    end else begin:g_distributed_control
        integer k;
        reg [NS-1:0] n_pw_we;
        reg [1-1:0] n_start_v;
        reg [NGO-1:0] n_go;
        reg [1-1:0] n_ready;
        reg [1-1:0] n_active;
        reg [1-1:0] n_fault;
        reg [SW-1:0] n_sel;
        reg [1-1:0] n_need_set;
        reg [1-1:0] n_wait_mask;
        reg [1-1:0] n_wait_done;
        reg [NPR-1:0] n_loaded;
        reg [1-1:0] n_armed;
        reg [1-1:0] n_run;
        assign run_next_phase=n_run;
        reg [32-1:0] n_cnt;
        reg [RW-1:0] n_rptr;
        reg [8-1:0] n_tail;
        reg [RN-1:0] n_r_val;
        reg [AW-1:0] n_pw_addr_raw;
        reg [256-1:0] n_pw_data_raw;
        reg [NPR*256-1:0] n_prm_raw;
        reg [221-1:0] n_rec_raw;
        reg [AW+1-1:0] n_hwm[0:NS-1];
        reg [AW+1-1:0] n_need[0:NS-1];
        reg [PAGE_W-1:0] n_page[0:NS-1];
        reg [32-1:0] n_r_off[0:RN-1];
        reg [2-1:0] n_r_go[0:RN-1];
        reg [221-1:0] n_r_pay[0:RN-1];
        always @*begin
            n_pw_we=pw_we;
            n_start_v=start_v;
            n_go=go;
            n_ready=ready;
            n_active=active;
            n_fault=fault;
            n_sel=sel;
            n_need_set=need_set;
            n_wait_mask=wait_mask;
            n_wait_done=wait_done;
            n_loaded=loaded;
            n_armed=armed;
            n_run=run;
            n_cnt=count_unreset_next;
            n_rptr=rptr;
            n_tail=tail;
            n_r_val=r_val;
            n_pw_addr_raw=pw_addr_raw;
            n_pw_data_raw=pw_data_raw;
            n_prm_raw=prm_raw;
            n_rec_raw=rec_raw;
            for(k=0;k<NS;k=k+1)n_hwm[k]=hwm[k];
            for(k=0;k<NS;k=k+1)n_need[k]=need[k];
            for(k=0;k<NS;k=k+1)n_page[k]=page[k];
            for(k=0;k<RN;k=k+1)n_r_off[k]=r_off[k];
            for(k=0;k<RN;k=k+1)n_r_go[k]=r_go[k];
            for(k=0;k<RN;k=k+1)n_r_pay[k]=r_pay[k];
            n_pw_we = 0; n_start_v = 0; n_go = 0;
            if (|cf_q || xfault) n_fault = 1;
            // ------------ configuration frames
            if (hit) begin
                n_armed = 0;
                if (run) n_fault = 1;
                else if (install_depth_bad || install_resv_bad) n_fault = 1;
                else if (!ca[11]) begin
                    if (lin == hwm[sel] || MUT == 1) begin
                        if (hwm[sel][AW]) n_fault = 1;
                        else begin n_pw_we[sel] = 1; n_pw_addr_raw = lin[AW-1:0]; n_pw_data_raw = cd; n_hwm[sel] = lin + 1'b1; end
                    end else if (lin == 0) begin
                        n_pw_we[sel] = 1; n_pw_addr_raw = 0; n_pw_data_raw = cd; n_hwm[sel] = 1;
                    end else n_fault = 1;
                end else if (ca[11:10] == 2'b10) begin
                    if (ca[9:0] >= NPR) n_fault = 1;
                    else begin n_prm_raw[ca[9:0]*256 +: 256] = cd; n_loaded[ca[9:0]] = 1; end
                end else if (ca[11:9] == 3'b110) begin
                    if (ca[8:0] >= NREC) n_fault = 1;
                    else begin
                        n_r_off[ca[8:0]] = cd[31:0]; n_r_val[ca[8:0]] = cd[32];
                        n_r_go[ca[8:0]] = cd[34:33]; n_r_pay[ca[8:0]] = cd[255:35];
                        if (NGO < 2 && cd[34]) n_fault = 1;
                    end
                end else if (ca == 12'hE00) begin
                    if (cd[7:0] >= NS) n_fault = 1;
                    else begin n_sel = cd[SW-1:0]; n_page[cd[SW-1:0]] = cd[8 +: PAGE_W]; end
                end else if (ca == 12'hE01) begin
                    for (k = 0; k < NS; k = k + 1) n_need[k] = cd[k*32 +: AW+1];
                    n_wait_mask = cd[128]; n_need_set = 1;
                end else n_fault = 1;
            end
            if (dhit) begin
                if (run || hit) n_fault = 1; else n_armed = 1;
            end
            // ------------ launch: only an armed target participates
            if (lv && armed) begin
                n_armed = 0;
                if (!(inst_ok && !fault && !run && !install_depth_bad && !install_resv_bad)) n_fault = 1;
                else begin
                    n_start_v = 1; n_run = 1;  n_rptr = 0; n_tail = TAIL[7:0];
                    n_wait_done = wait_mask;
                end
            end
            // ------------ execution: fixed record calendar
            if (run) begin
                
                if (tail != 0 && !start_v) n_tail = tail - 1'b1;
                if (done_q) n_wait_done = 0;
                if (!recs_done) begin
                    if (cur_off == cmp_cnt) begin
                        n_go = selected_record[33 +: NGO]; n_rec_raw = selected_record[255:35]; n_rptr = rptr + 1'b1; n_tail = TAIL[7:0];
                    end else if (cur_off < cnt) n_fault = 1;
                end else if (!start_v && tail == 0 && !(|busy_q) && !wait_done && go == 0) n_run = 0;
            end
            n_active = run || (lv && armed);
            n_ready = armed && inst_ok && !fault && !run && !hit;

        end
        always @(posedge clk or negedge regional_reset[17])begin:seq_0
            integer z;
            if(!regional_reset[17])begin pw_we<=0;start_v<=0;go<=0;ready<=0;active<=0;fault<=0; end
            else begin pw_we<=n_pw_we;start_v<=n_start_v;go<=n_go;ready<=n_ready;active<=n_active;fault<=n_fault; end
        end
        always @(posedge clk or negedge regional_reset[18])begin:seq_1
            integer z;
            if(!regional_reset[18])begin sel<=0;need_set<=0;wait_mask<=0;wait_done<=0;loaded<=0;armed<=0;run<=0; end
            else begin sel<=n_sel;need_set<=n_need_set;wait_mask<=n_wait_mask;wait_done<=n_wait_done;loaded<=n_loaded;armed<=n_armed;run<=n_run; end
        end
        always @(posedge clk or negedge regional_reset[19])begin:seq_2
            integer z;
            if(!regional_reset[19])begin cnt<=0; end
            else begin cnt<=n_cnt; end
        end
        always @(posedge clk or negedge regional_reset[20])begin:seq_3
            integer z;
            if(!regional_reset[20])begin rptr<=0;tail<=0;r_val<=0; end
            else begin rptr<=n_rptr;tail<=n_tail;r_val<=n_r_val; end
        end
        always @(posedge clk or negedge regional_reset[21])begin:seq_4
            integer z;
            if(!regional_reset[21])begin for(z=0;z<NS;z=z+1)hwm[z]<=0;for(z=0;z<NS;z=z+1)need[z]<=0;for(z=0;z<NS;z=z+1)page[z]<=0; end
            else begin for(z=0;z<NS;z=z+1)hwm[z]<=n_hwm[z];for(z=0;z<NS;z=z+1)need[z]<=n_need[z];for(z=0;z<NS;z=z+1)page[z]<=n_page[z]; end
        end
        always @(posedge clk)begin:seq_unreset
            integer z;
            if(rst_c_n)begin prm_raw<=n_prm_raw; pw_addr_raw<=n_pw_addr_raw; pw_data_raw<=n_pw_data_raw; for(z=0;z<RN;z=z+1)r_go[z]<=n_r_go[z]; for(z=0;z<RN;z=z+1)r_off[z]<=n_r_off[z]; for(z=0;z<RN;z=z+1)r_pay[z]<=n_r_pay[z]; rec_raw<=n_rec_raw; end
        end
    end endgenerate
endmodule

// Same physical edge as the original pin/state registers. The canonical
// ot_keep_regs.tcl synthesis hook must retain these declared register copies.
// Hierarchy protects each 16-bit bank from global ABC enable absorption.
module ot_hbm_idx256r_banks #(parameter integer AW=12,MUT=0)(
 input wire clk,rst_c_n,cfg_v,recs_done,programme_accept,resv_bad,
 input wire [15:0] run_state,
 input wire [16:0] regional_reset,
 input wire [7:0] cfg_target,tg,
 input wire [11:0] cfg_addr,
 input wire [255:0] cd,
 input wire [31:0] cur_off,cnt_next,
 input wire [3:0] rptr_next,
 input wire [AW-1:0] lin,
 output wire [255:0] selected_record,
 output reg [AW-1:0] pw_addr,
 output wire [255:0] pw_data,
 output wire [1535:0] prm,
 output wire [220:0] rec
);
 wire [7:0] next_onehot=(rptr_next<8)?(8'd1<<rptr_next):8'd0;
 genvar g,r;
 generate for(g=0;g<16;g=g+1)begin:g_bank
  wire [95:0] local_prm;
  wire [15:0] local_rec;
  (* keep_hierarchy *) ot_hbm_idx256r_payload_bank #(.LO(g*16),.MUT(MUT)) u_payload(
   .clk(clk),.rst_c_n(regional_reset[g]),.cfg_v(cfg_v),.run(run_state[g]),.recs_done(recs_done),
   .programme_accept(programme_accept),.resv_bad(resv_bad),.cfg_target(cfg_target),.tg(tg),
   .cfg_addr(cfg_addr),.cd(cd[g*16+:16]),.valid_data(cd[32]),
   .cur_off(cur_off),.cnt_next(cnt_next),.onehot_next(next_onehot),
   .selected_record(selected_record[g*16+:16]),.pw_data(pw_data[g*16+:16]),
   .prm(local_prm),.rec(local_rec));
  for(r=0;r<6;r=r+1)begin:g_operand_wires
   assign prm[r*256+g*16+:16]=local_prm[r*16+:16];
  end
  if(g>=3)assign rec[g*16-35+:16]=local_rec;
  else if(g==2)assign rec[0+:13]=local_rec[3+:13];
 end endgenerate
 (* keep *) reg addr_cv;
 always @(posedge clk or negedge regional_reset[16])if(!regional_reset[16])addr_cv<=0;else addr_cv<=cfg_v;
 always @(posedge clk)if(programme_accept && addr_cv)pw_addr<=lin;
endmodule

(* keep_hierarchy *) module ot_hbm_idx256r_payload_bank #(parameter integer LO=0,MUT=0)(
 input wire clk,rst_c_n,cfg_v,run,recs_done,programme_accept,valid_data,resv_bad,
 input wire [7:0] cfg_target,tg,
 input wire [11:0] cfg_addr,
 input wire [15:0] cd,
 input wire [31:0] cur_off,cnt_next,
 input wire [7:0] onehot_next,
 output wire [15:0] selected_record,
 output wire [15:0] pw_data,
 output wire [95:0] prm,
 output wire [15:0] rec
);
 (* keep *) reg cv;
 (* keep *) reg [7:0] ct;
 (* keep *) reg [11:0] ca;
 always @(posedge clk or negedge rst_c_n)if(!rst_c_n)cv<=0;else cv<=cfg_v;
 always @(posedge clk)begin ct<=cfg_target;ca<=cfg_addr;end
 (* keep *) reg [7:0] rd_oh;
 wire [7:0] bad_onehot={onehot_next[6:0],onehot_next[7]};
 always @(posedge clk)rd_oh<=(MUT==14 && LO==32)?bad_onehot:onehot_next;
 wire [15:0] rows[0:7];
 wire record_cfg=cv && ct==tg && !run && ca[11:9]==3'b110 && ca[8:0]<8;
 wire operand_cfg=cv && ct==tg && !run && ca[11:10]==2'b10 && ca[9:0]<6 && !resv_bad;
 (* keep_hierarchy *) ot_hbm_idx256r_word u_programme(.clk(clk),.en(programme_accept && cv),.d(cd),.q(pw_data));
 genvar r,b;
 generate for(r=0;r<8;r=r+1)begin:g_record
  if(LO==32)begin:g_no_duplicate_valid
   wire [14:0] stored;
   (* keep_hierarchy *) ot_hbm_idx256r_word #(.W(15)) u_word(.clk(clk),.en(record_cfg && ca[8:0]==r),.d(cd[15:1]),.q(stored));
   assign rows[r]={stored,1'b0};
  end else begin:g_full_word
   (* keep_hierarchy *) ot_hbm_idx256r_word u_word(.clk(clk),.en(record_cfg && ca[8:0]==r),.d(cd),.q(rows[r]));
  end
 end endgenerate
 reg [15:0] selected;
 integer j;
 always @*begin
  selected=0;
  for(j=0;j<8;j=j+1)selected=selected|(rows[j]&{16{rd_oh[j]}});
 end
 generate if(LO==32)begin:g_valid
  reg [7:0] val;
  integer v;
  always @(posedge clk or negedge rst_c_n)
   if(!rst_c_n)val<=0;
   else for(v=0;v<8;v=v+1)if(record_cfg && ca[8:0]==v)val[v]<=valid_data;
  assign selected_record={selected[15:1],|(val&rd_oh)};
 end else assign selected_record=selected;
 for(r=0;r<6;r=r+1)begin:g_operand
  wire [15:0] operand;
  (* keep_hierarchy *) ot_hbm_idx256r_mword #(.BASE(r*256+LO)) u_word(.clk(clk),.en(operand_cfg && ca[9:0]==r),.d(cd),.q(operand));
  assign prm[r*16+:16]=operand;
 end
 if(LO>=32)begin:g_emit
  (* keep *) reg [31:0] local_cnt;
  always @(posedge clk)local_cnt<=cnt_next;
  wire [31:0] local_cmp=(MUT==3)?local_cnt+1'b1:local_cnt;
  wire step=run && !recs_done && cur_off==local_cmp;
  reg [15:0] emitted;
  always @(posedge clk)if(step)emitted<=selected_record;
  assign rec=emitted;
 end else assign rec=16'b0;
 endgenerate
endmodule
(* keep_hierarchy *) module ot_hbm_idx256r_word #(parameter integer W=16)(input wire clk,en,input wire [W-1:0] d,output reg [W-1:0] q);
 always @(posedge clk)if(en)q<=d;
endmodule
// IDX256R masked operand word: a flop only for used operand bits (op index BASE+b); reserved bits read 0.
(* keep_hierarchy *) module ot_hbm_idx256r_mword #(parameter integer BASE=0)(input wire clk,en,input wire [15:0] d,output wire [15:0] q);
 genvar b;
 generate for(b=0;b<16;b=b+1)begin:g_bit
  if((BASE+b)<44 || ((BASE+b)>=51 && (BASE+b)<424) || ((BASE+b)>=766 && (BASE+b)<1108) || ((BASE+b)>=1450 && (BASE+b)<1460))begin:g_used
   reg f;
   always @(posedge clk)if(en)f<=d[b];
   assign q[b]=f;
  end else begin:g_resv
   assign q[b]=1'b0;
  end
 end endgenerate
endmodule
`default_nettype wire
