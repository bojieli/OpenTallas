`timescale 1ns/1ps
`default_nettype none
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
module ot_hbm_static_cfg_collar #(
    parameter integer PAGE_W=12,   // page bits per programme space (AW = PAGE_W+11)
    parameter integer NS=2,        // programme spaces (1..4)
    parameter integer NPR=1,       // operand rows of 256 b (>=1)
    parameter integer NREC=0,      // record rows (0..512)
    parameter integer NGO=1,       // record go outputs (1..2)
    parameter integer NB=2,        // client busy inputs
    parameter integer NF=1,        // client fault inputs
    parameter integer TAIL=4,
    parameter integer XSER=0,      // 1: core clk is the 3:4 serial domain, broadcast pins on clk_in (stream)
    parameter integer MUT=0,       // bench: 1 skip sequential check, 2 ready ignores need, 3 go one edge early, 4 no event seq check,
                                   //        5 (XSER=1) stream domain left without its reset, 6 (XSER=1) binary event sequence (not Gray),
                                   //        7 (XSER=1) one synchroniser stage short, 8 (XSER=0) core state without the synchronised reset
    // SU bank/row ABI: ordered, contiguous rows inside each present bank; absent banks are never written.
    // E01 need is the exact number of programme writes in this installation generation.
    parameter integer SPARSE_SU=0,
    parameter [319:0] SU_DICT_CAP={32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3},
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
    output reg  [AW-1:0] pw_addr,
    output reg  [255:0] pw_data,
    output reg  [NPR*256-1:0] prm,
    output reg  start_v,
    output reg  [NGO-1:0] go,
    output reg  [220:0] rec,
    output reg  ready, active, fault
);
    initial begin
        if (NS<1 || NS>4 || NPR<1 || NPR>1024 || NREC<0 || NREC>512 || NGO<1 || NGO>2 || PAGE_W<1 || AW>31)
            $fatal(1, "ot_hbm_static_cfg_collar: parameter out of range");
    end
    initial if (SPARSE_SU && (NS!=1 || PAGE_W!=12))
        $fatal(1, "SPARSE_SU requires the frozen SU bank16/row7 interface");
    // Match root_h5's four 320-bank parts and pslice_c5's ten local column apertures.
    function automatic su_bank_valid(input [15:0] bank);
        integer part, local_bank, column, cap;
        begin
            su_bank_valid=0;
            for(part=0;part<4;part=part+1) begin
                if(bank>=part*320 && bank<(part+1)*320) begin
                    local_bank=bank-part*320; column=local_bank/32;
                    cap=SU_DICT_CAP[32*column+:32];
                    su_bank_valid=(local_bank%32)<(4+((cap<=3)?3:13));
                end
            end
        end
    endfunction
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
            if (pv_cv || pv_dv || pv_lv) begin h_ct <= p_ct; h_ca <= p_ca; end
        if (SPARSE_SU) begin:g_hold_words
            for(genvar w=0;w<16;w=w+1) begin:g_word
                ot_hbm_collar_sparse_word u_word(.clk(clk_in),.en(pv_cv || pv_dv || pv_lv),.d(p_cd[w*16+:16]),.q(h_cd[w*16+:16]));
            end
        end else always @(posedge clk_in) if(pv_cv || pv_dv || pv_lv) h_cd<=p_cd;
        reg [1:0] x1_seq, x2_seq, x3_seq;
        always @(posedge clk or negedge rst_c_n)
            if (!rst_c_n) begin x1_seq <= 0; x2_seq <= 0; x3_seq <= 0; end
            else begin x1_seq <= h_seq; x2_seq <= x1_seq; x3_seq <= x2_seq; end
        // MUT 7: one synchroniser stage short: captures on the edge after x1 first saw the code
        wire [1:0] q_new = (MUT == 7) ? x1_seq : x2_seq;
        wire [1:0] q_old = (MUT == 7) ? x2_seq : x3_seq;
        wire ev = q_new != q_old;
        wire [1:0] b_new = {q_new[1], q_new[1] ^ q_new[0]}, b_old = {q_old[1], q_old[1] ^ q_old[0]};
        always @(posedge clk) if (ev) begin ct <= h_ct; ca <= h_ca; end
        if (SPARSE_SU) begin:g_capture_words
            for(genvar w=0;w<16;w=w+1) begin:g_word
                ot_hbm_collar_sparse_word u_word(.clk(clk),.en(ev),.d(h_cd[w*16+:16]),.q(cd[w*16+:16]));
            end
        end else always @(posedge clk) if(ev) cd<=h_cd;
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
    reg [AW-1:0] sparse_last;
    reg sparse_seen;
    wire [22:0] sparse_linear=23'(lin), sparse_previous=23'(sparse_last);
    wire sparse_address_ok=su_bank_valid(sparse_linear[22:7]) &&
        ((lin==0) || (sparse_seen && lin>sparse_last &&
          ((sparse_linear[22:7]==sparse_previous[22:7] && {1'b0,lin[6:0]}=={1'b0,sparse_last[6:0]}+8'd1) ||
           (sparse_linear[22:7]>sparse_previous[22:7] && lin[6:0]==0))));
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
    reg inst_ok;
    integer s;
    always @* begin
        inst_ok = need_set && (&loaded);
        if (SPARSE_SU && (!sparse_seen || need[0]==0)) inst_ok = 0;
        for (s = 0; s < NS; s = s + 1) if ((SPARSE_SU ? (hwm[s] != need[s]) : (hwm[s] < need[s])) && MUT != 2) inst_ok = 0;
    end
    wire recs_done = (NREC == 0) || (rptr >= NREC) || !r_val[rptr];
    wire [31:0] cur_off = r_off[(NREC == 0) ? 0 : rptr];
    wire [31:0] cmp_cnt = (MUT == 3) ? cnt + 1 : cnt;
    generate if(SPARSE_SU && XSER==1 && NPR==1 && NREC==0) begin:g_sparse_bounded
        // Same-edge copies of the existing second reset stage, not an extra reset or data cycle.
        // Each state vector has an independent reset leaf; widths are <=32 after dead-record pruning.
        (* keep *) reg [24:0] reset_leaf;
        always @(posedge clk) reset_leaf <= {25{rst_stage1}};
        reg programme_write, operand_write;
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
        reg [32-1:0] n_cnt;
        reg [RW-1:0] n_rptr;
        reg [8-1:0] n_tail;
        reg [RN-1:0] n_r_val;
        reg [AW-1:0] n_sparse_last;
        reg [1-1:0] n_sparse_seen;
        reg [AW-1:0] n_pw_addr;
        reg [221-1:0] n_rec;
        reg [AW+1-1:0] n_hwm [0:NS-1];
        reg [AW+1-1:0] n_need [0:NS-1];
        reg [PAGE_W-1:0] n_page [0:NS-1];
        reg [32-1:0] n_r_off [0:RN-1];
        reg [2-1:0] n_r_go [0:RN-1];
        reg [221-1:0] n_r_pay [0:RN-1];
        always @* begin
            programme_write=0; operand_write=0;
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
            n_cnt=cnt;
            n_rptr=rptr;
            n_tail=tail;
            n_r_val=r_val;
            n_sparse_last=sparse_last;
            n_sparse_seen=sparse_seen;
            n_pw_addr=pw_addr;
            n_rec=rec;
            for(k=0;k<NS;k=k+1) n_hwm[k]=hwm[k];
            for(k=0;k<NS;k=k+1) n_need[k]=need[k];
            for(k=0;k<NS;k=k+1) n_page[k]=page[k];
            for(k=0;k<RN;k=k+1) n_r_off[k]=r_off[k];
            for(k=0;k<RN;k=k+1) n_r_go[k]=r_go[k];
            for(k=0;k<RN;k=k+1) n_r_pay[k]=r_pay[k];
            n_pw_we = 0; n_start_v = 0; n_go = 0;
            if (|cf_q || xfault) n_fault = 1;
            // ------------ configuration frames
            if (hit) begin
                n_armed = 0;
                if (run) n_fault = 1;
                else if (!ca[11]) begin
                    if (SPARSE_SU) begin
                        if (!sparse_address_ok || hwm[sel][AW]) n_fault = 1;
                        else begin
                            programme_write = rst_c_n; n_pw_we[sel] = 1; n_pw_addr = lin[AW-1:0]; 
                            n_sparse_last = lin[AW-1:0]; n_sparse_seen = 1;
                            if(lin==0) begin
                                n_hwm[sel] = 1; n_need_set = 0; n_loaded = 0;
                            end else n_hwm[sel] = hwm[sel]+1'b1;
                        end
                    end else if (lin == hwm[sel] || MUT == 1) begin
                        if (hwm[sel][AW]) n_fault = 1;
                        else begin programme_write = rst_c_n; n_pw_we[sel] = 1; n_pw_addr = lin[AW-1:0];  n_hwm[sel] = lin + 1'b1; end
                    end else if (lin == 0) begin
                        programme_write = rst_c_n; n_pw_we[sel] = 1; n_pw_addr = 0;  n_hwm[sel] = 1;
                    end else n_fault = 1;
                end else if (ca[11:10] == 2'b10) begin
                    if (ca[9:0] >= NPR) n_fault = 1;
                    else begin  operand_write = rst_c_n; n_loaded[ca[9:0]] = 1; end
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
                if (!(inst_ok && !fault && !run)) n_fault = 1;
                else begin
                    n_start_v = 1; n_run = 1; n_cnt = 0; n_rptr = 0; n_tail = TAIL[7:0];
                    n_wait_done = wait_mask;
                end
            end
            // ------------ execution: fixed record calendar
            if (run) begin
                n_cnt = cnt + 1'b1;
                if (tail != 0 && !start_v) n_tail = tail - 1'b1;
                if (done_q) n_wait_done = 0;
                if (!recs_done) begin
                    if (cur_off == cmp_cnt) begin
                        n_go = r_go[rptr][NGO-1:0]; n_rec = r_pay[rptr]; n_rptr = rptr + 1'b1; n_tail = TAIL[7:0];
                    end else if (cur_off < cnt) n_fault = 1;
                end else if (!start_v && tail == 0 && !(|busy_q) && !wait_done && go == 0) n_run = 0;
            end
            n_active = run || (lv && armed);
            n_ready = armed && inst_ok && !fault && !run && !hit;
        end
        always @(posedge clk or negedge reset_leaf[0]) if(!reset_leaf[0]) pw_we<=0; else pw_we<=n_pw_we;
        always @(posedge clk or negedge reset_leaf[1]) if(!reset_leaf[1]) start_v<=0; else start_v<=n_start_v;
        always @(posedge clk or negedge reset_leaf[2]) if(!reset_leaf[2]) go<=0; else go<=n_go;
        always @(posedge clk or negedge reset_leaf[3]) if(!reset_leaf[3]) ready<=0; else ready<=n_ready;
        always @(posedge clk or negedge reset_leaf[4]) if(!reset_leaf[4]) active<=0; else active<=n_active;
        always @(posedge clk or negedge reset_leaf[5]) if(!reset_leaf[5]) fault<=0; else fault<=n_fault;
        always @(posedge clk or negedge reset_leaf[6]) if(!reset_leaf[6]) sel<=0; else sel<=n_sel;
        always @(posedge clk or negedge reset_leaf[7]) if(!reset_leaf[7]) need_set<=0; else need_set<=n_need_set;
        always @(posedge clk or negedge reset_leaf[8]) if(!reset_leaf[8]) wait_mask<=0; else wait_mask<=n_wait_mask;
        always @(posedge clk or negedge reset_leaf[9]) if(!reset_leaf[9]) wait_done<=0; else wait_done<=n_wait_done;
        always @(posedge clk or negedge reset_leaf[10]) if(!reset_leaf[10]) loaded<=0; else loaded<=n_loaded;
        always @(posedge clk or negedge reset_leaf[11]) if(!reset_leaf[11]) armed<=0; else armed<=n_armed;
        always @(posedge clk or negedge reset_leaf[12]) if(!reset_leaf[12]) run<=0; else run<=n_run;
        always @(posedge clk or negedge reset_leaf[13]) if(!reset_leaf[13]) cnt<=0; else cnt<=n_cnt;
        always @(posedge clk or negedge reset_leaf[14]) if(!reset_leaf[14]) rptr<=0; else rptr<=n_rptr;
        always @(posedge clk or negedge reset_leaf[15]) if(!reset_leaf[15]) tail<=0; else tail<=n_tail;
        always @(posedge clk or negedge reset_leaf[16]) if(!reset_leaf[16]) r_val<=0; else r_val<=n_r_val;
        always @(posedge clk or negedge reset_leaf[17]) if(!reset_leaf[17]) sparse_last<=0; else sparse_last<=n_sparse_last;
        always @(posedge clk or negedge reset_leaf[18]) if(!reset_leaf[18]) sparse_seen<=0; else sparse_seen<=n_sparse_seen;
        always @(posedge clk) if(rst_c_n) pw_addr<=n_pw_addr;
        always @(posedge clk) if(rst_c_n) rec<=n_rec;
        for(genvar a_hwm=0;a_hwm<NS;a_hwm=a_hwm+1) begin:g_hwm
            always @(posedge clk or negedge reset_leaf[19]) if(!reset_leaf[19]) hwm[a_hwm]<=0; else hwm[a_hwm]<=n_hwm[a_hwm];
        end
        for(genvar a_need=0;a_need<NS;a_need=a_need+1) begin:g_need
            always @(posedge clk or negedge reset_leaf[20]) if(!reset_leaf[20]) need[a_need]<=0; else need[a_need]<=n_need[a_need];
        end
        for(genvar a_page=0;a_page<NS;a_page=a_page+1) begin:g_page
            always @(posedge clk or negedge reset_leaf[21]) if(!reset_leaf[21]) page[a_page]<=0; else page[a_page]<=n_page[a_page];
        end
        for(genvar a_r_off=0;a_r_off<RN;a_r_off=a_r_off+1) begin:g_r_off
            always @(posedge clk) if(rst_c_n) r_off[a_r_off]<=n_r_off[a_r_off];
        end
        for(genvar a_r_go=0;a_r_go<RN;a_r_go=a_r_go+1) begin:g_r_go
            always @(posedge clk) if(rst_c_n) r_go[a_r_go]<=n_r_go[a_r_go];
        end
        for(genvar a_r_pay=0;a_r_pay<RN;a_r_pay=a_r_pay+1) begin:g_r_pay
            always @(posedge clk) if(rst_c_n) r_pay[a_r_pay]<=n_r_pay[a_r_pay];
        end
        for(genvar w=0;w<16;w=w+1) begin:g_payload
            ot_hbm_collar_sparse_word u_programme(.clk(clk),.en(programme_write),.d(cd[w*16+:16]),.q(pw_data[w*16+:16]));
            ot_hbm_collar_sparse_word u_operand(.clk(clk),.en(operand_write),.d(cd[w*16+:16]),.q(prm[w*16+:16]));
        end
    end else begin:g_legacy_state
    integer k;
    always @(posedge clk or negedge rst_c_n) begin
        if (!rst_c_n) begin
            pw_we <= 0; start_v <= 0; go <= 0; ready <= 0; active <= 0; fault <= 0;
            sel <= 0; need_set <= 0; wait_mask <= 0; wait_done <= 0; loaded <= 0; armed <= 0; run <= 0;
            cnt <= 0; rptr <= 0; tail <= 0; r_val <= 0; sparse_last <= 0; sparse_seen <= 0;
            for (k = 0; k < NS; k = k + 1) begin hwm[k] <= 0; need[k] <= 0; page[k] <= 0; end
        end else begin
            pw_we <= 0; start_v <= 0; go <= 0;
            if (|cf_q || xfault) fault <= 1;
            // ------------ configuration frames
            if (hit) begin
                armed <= 0;
                if (run) fault <= 1;
                else if (!ca[11]) begin
                    if (SPARSE_SU) begin
                        if (!sparse_address_ok || hwm[sel][AW]) fault <= 1;
                        else begin
                            pw_we[sel] <= 1; pw_addr <= lin[AW-1:0]; pw_data <= cd;
                            sparse_last <= lin[AW-1:0]; sparse_seen <= 1;
                            if(lin==0) begin
                                hwm[sel] <= 1; need_set <= 0; loaded <= 0;
                            end else hwm[sel] <= hwm[sel]+1'b1;
                        end
                    end else if (lin == hwm[sel] || MUT == 1) begin
                        if (hwm[sel][AW]) fault <= 1;
                        else begin pw_we[sel] <= 1; pw_addr <= lin[AW-1:0]; pw_data <= cd; hwm[sel] <= lin + 1'b1; end
                    end else if (lin == 0) begin
                        pw_we[sel] <= 1; pw_addr <= 0; pw_data <= cd; hwm[sel] <= 1;
                    end else fault <= 1;
                end else if (ca[11:10] == 2'b10) begin
                    if (ca[9:0] >= NPR) fault <= 1;
                    else begin prm[ca[9:0]*256 +: 256] <= cd; loaded[ca[9:0]] <= 1; end
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
                if (!(inst_ok && !fault && !run)) fault <= 1;
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
    end endgenerate
endmodule
// Retained word scope prevents ABC from absorbing a shared enable into hundreds of bit muxes.
(* keep_hierarchy *) module ot_hbm_collar_sparse_word #(parameter integer W=16)(
    input wire clk,en,input wire [W-1:0] d,output reg [W-1:0] q);
    always @(posedge clk) if(en) q<=d;
endmodule
`default_nettype wire
