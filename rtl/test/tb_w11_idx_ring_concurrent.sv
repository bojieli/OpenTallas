`timescale 1ns/1ps
// W11: key writes DURING a scan, through the ring K-port arbiter
// (ot_hdc_v41x_idx_ring_port, READ_FENCE = 0: no alternate phases).
//
// Full-shape ring layout (30-bit sectors, RSB 64 + 32-key tail), timed HBM
// models with backing storage.  User UA's NA keys are placed in its ring by
// the bench (the placement of ot_hdc_v41x_idx_ring_ranges); then
//   1. user UA is scanned alone (four ot_hdc_v41x_idx_kstream_ring + the
//      quarter join), every key checked;
//   2. the writer is kept saturated with decode steps of user UB (appends and,
//      every 32nd step, 48-key migrations) and user UA is scanned again while
//      it runs, every key checked;
//   3. the writer stops; user UB is scanned at the count its steps reached and
//      every key it wrote is checked.
// Reported: both scan times, and the writer's requests, steps and migrations
// that overlapped the second scan.
module tb_w11_idx_ring_concurrent #(
    parameter integer AW=30, HW=23, RSB=64, RTAIL=32,
    parameter integer KB=7444668, MEM_WORDS=1055017,
    parameter integer UA=865, UB=0, NA=262144,
    parameter integer WB=128, GA=120, CLK_PS=967, LEAD=300,
    // LEAD_STEPS > 0: user UB's first LEAD_STEPS steps complete before scan 2 starts, and DURING of its
    // steps are issued after it starts (DURING = 0: the writer is kept saturated for the whole scan)
    parameter integer LEAD_STEPS=0, DURING=0
) (input wire clk, rst_n, cmd_v);
    localparam integer NPC=32, TAGW=16, LENW=4, BEATW=4, DW=256, NW=HW+10;
    localparam integer C = RSB*1024 + RTAIL;
    localparam integer UBLK = RSB*17 + ((RTAIL != 0) ? 1 + (RTAIL + 63) / 64 : 0);
    function automatic [31:0] mix(input [31:0] x);
        reg [31:0] y;
        begin y = x ^ (x >> 16); y = y * 32'h7feb352d; y = y ^ (y >> 15); y = y * 32'h846ca68b; mix = y ^ (y >> 16); end
    endfunction
    function automatic [543:0] keygen(input integer u, input integer p);
        integer w;
        begin
            for (w = 0; w < 17; w = w + 1) keygen[32*w +: 32] = mix(32'(u) * 32'h01000193 ^ 32'(p) * 32'h9E3779B1 ^ 32'(w) * 32'h85ebca6b);
        end
    endfunction
    function automatic ref_key(input [31:0] scale);
        ref_key = (scale[7:0] >= 253 || scale[15:8] >= 253 || scale[23:16] >= 253 || scale[31:24] >= 253);
    endfunction

    wire [4*NPC-1:0] h_v, h_rdy, h_we, h_rsp_v, h_rsp_rdy, h_wr_done;
    wire [4*NPC*AW-1:0] h_addr;
    wire [4*NPC*LENW-1:0] h_len;
    wire [4*NPC*TAGW-1:0] h_tag, h_rsp_tag;
    wire [4*NPC*DW-1:0] h_wdata, h_rsp_data;
    wire [4*NPC*(DW/8)-1:0] h_wstrb;
    wire [4*NPC*BEATW-1:0] h_rsp_beat;
    wire [4*NPC-1:0] r_v, r_rdy, r_rsp_v, r_rsp_rdy;
    wire [4*NPC*AW-1:0] r_addr;
    wire [4*NPC*LENW-1:0] r_len;
    wire [4*NPC*TAGW-1:0] r_tag;
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_stack
        ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(DW),.MEM_WORDS(MEM_WORDS),.TAGW(TAGW),.LENW(LENW),
            .BEATW(BEATW),.QD(64),.RQD(32),.CLK_PS(CLK_PS),.REFPB(3),.MEM_MODE(0)) hm (
            .clk(clk),.rst_n(rst_n),.req_v(h_v[s*NPC +:NPC]),.req_rdy(h_rdy[s*NPC +:NPC]),
            .req_addr(h_addr[s*NPC*AW +:NPC*AW]),.req_len(h_len[s*NPC*LENW +:NPC*LENW]),
            .req_tag(h_tag[s*NPC*TAGW +:NPC*TAGW]),.req_we(h_we[s*NPC +:NPC]),
            .req_wdata(h_wdata[s*NPC*DW +:NPC*DW]),.req_wstrb(h_wstrb[s*NPC*(DW/8) +:NPC*(DW/8)]),
            .wr_done(h_wr_done[s*NPC +:NPC]),.rsp_v(h_rsp_v[s*NPC +:NPC]),.rsp_rdy(h_rsp_rdy[s*NPC +:NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),.rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),
            .rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]));
    end endgenerate

    // ---------------- writer + arbiter ----------------
    reg          d_v;
    reg [NW-1:0] nb;
    wire         d_rdy, p_busy, p_fault;
    wire [31:0]  p_records, p_writes, p_hw, p_rstall, p_wstall;
    wire [47:0]  p_migs, p_copied;
    ot_hdc_v41x_idx_ring_port #(.NPC(NPC),.AW(AW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.RSB(RSB),
        .RTAIL(RTAIL),.RFQ(4),.READ_FENCE(0),.DIRECT(1)) port (
        .clk(clk),.rst_n(rst_n),.w_v(1'b0),.w_rdy(),.w_csec('0),.w_codes('0),.w_ssec('0),.w_sslot(3'd0),
        .w_scales(32'd0),.d_v(d_v),.d_rdy(d_rdy),.d_base(HW'(KB + UB * UBLK)),.d_n(nb),.d_key(keygen(UB, nb)),
        .r_v(r_v),.r_rdy(r_rdy),.r_addr(r_addr),.r_len(r_len),.r_tag(r_tag),.r_rsp_v(r_rsp_v),.r_rsp_rdy(r_rsp_rdy),
        .h_v(h_v),.h_rdy(h_rdy),.h_addr(h_addr),.h_len(h_len),.h_tag(h_tag),.h_we(h_we),.h_wdata(h_wdata),
        .h_wstrb(h_wstrb),.h_wr_done(h_wr_done),.h_rsp_v(h_rsp_v),.h_rsp_rdy(h_rsp_rdy),.h_rsp_tag(h_rsp_tag),
        .h_rsp_data(h_rsp_data),.busy(p_busy),.fault(p_fault),.dbg_records(p_records),.dbg_writes(p_writes),
        .dbg_fifo_highwater(p_hw),.dbg_read_stalls(p_rstall),.dbg_writer_stalls(p_wstall),
        .dbg_migrations(p_migs),.dbg_copied_sectors(p_copied));

    // ---------------- reader ----------------
    reg          scan_go;
    reg [9:0]    scan_user;
    reg [NW-1:0] scan_n;
    wire [4*HW-1:0] g_base1, g_base2;
    wire [4*10-1:0] g_skip;
    wire [4*NW-1:0] g_n1, g_n2;
    wire g_fault;
    ot_hdc_v41x_idx_ring_ranges #(.HW(HW),.UW(10),.RSB(RSB),.RTAIL(RTAIL)) geo (
        .i_nkeys(scan_n),.i_user(scan_user),.cfg_key_base_block(HW'(KB)),
        .o_base1(g_base1),.o_skip(g_skip),.o_n1(g_n1),.o_base2(g_base2),.o_n2(g_n2),.o_user_base(),.o_fault(g_fault));
    wire [3:0] s_busy, s_valid, s_ready;
    wire [4*16-1:0] s_kv;
    wire [4*16*544-1:0] s_key;
    wire [4*48-1:0] s_keys, s_beats;
    generate for (s = 0; s < 4; s = s + 1) begin : g_rd
        ot_hdc_v41x_idx_kstream_ring #(.NPC(NPC),.WB(WB),.GA(GA),.AW(AW),.HW(HW),.TAGW(TAGW),
            .LENW(LENW),.BEATW(BEATW),.DW(DW)) ks (
            .clk(clk),.rst_n(rst_n),.cmd_v(scan_go && (g_n1[s*NW +: NW] + g_n2[s*NW +: NW]) != 0),
            .cmd_base(g_base1[s*HW +: HW]),.cmd_skip(g_skip[s*10 +: 10]),.cmd_nkeys(g_n1[s*NW +: NW]),
            .cmd_base2(g_base2[s*HW +: HW]),.cmd_nkeys2(g_n2[s*NW +: NW]),.busy(s_busy[s]),
            .req_v(r_v[s*NPC +:NPC]),.req_rdy(r_rdy[s*NPC +:NPC]),.req_addr(r_addr[s*NPC*AW +:NPC*AW]),
            .req_len(r_len[s*NPC*LENW +:NPC*LENW]),.req_tag(r_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_v(r_rsp_v[s*NPC +:NPC]),.rsp_rdy(r_rsp_rdy[s*NPC +:NPC]),.rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),.rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]),
            .o_valid(s_valid[s]),.o_ready(s_ready[s]),.o_kv(s_kv[s*16 +:16]),.o_key(s_key[s*16*544 +:16*544]),
            .cnt_keys_streamed(s_keys[s*48 +:48]),.cnt_hbm_beats(s_beats[s*48 +:48]));
    end endgenerate
    wire j_busy, j_fault, out_valid;
    wire [63:0] out_kv, out_ref;
    wire [3:0] out_last;
    wire [64*544-1:0] out_key;
    ot_hdc_v41x_idx_quarter_join qjoin (
        .clk(clk),.rst_n(rst_n),.cmd_v(scan_go),.cmd_nkeys(30'(scan_n)),.cmd_skip(g_skip),
        .busy(j_busy),.fault(j_fault),.i_valid(s_valid),.i_ready(s_ready),.i_kv(s_kv),.i_key(s_key),
        .o_valid(out_valid),.o_ready(1'b1),.o_kv(out_kv),.o_last(out_last),.o_key(out_key),.o_ref(out_ref));

    // ---------------- preload of user UA (ring placement) ----------------
    task automatic put(input integer st, input longint sec, input [255:0] d, input [31:0] strb);
        longint idx;
        reg [255:0] w;
        begin
            idx = sec % MEM_WORDS;
            case (st)
                0: w = g_stack[0].hm.mem[idx]; 1: w = g_stack[1].hm.mem[idx];
                2: w = g_stack[2].hm.mem[idx]; default: w = g_stack[3].hm.mem[idx];
            endcase
            for (integer b = 0; b < 32; b = b + 1) if (strb[b]) w[8*b +: 8] = d[8*b +: 8];
            case (st)
                0: g_stack[0].hm.mem[idx] = w; 1: g_stack[1].hm.mem[idx] = w;
                2: g_stack[2].hm.mem[idx] = w; default: g_stack[3].hm.mem[idx] = w;
            endcase
        end
    endtask
    task automatic preload(input integer u, input integer n);
        integer p, q, qs, t;
        longint ub, cs, ss;
        reg [543:0] k;
        begin
            qs = (n / 32) * 8; ub = longint'(KB) + longint'(u) * UBLK;
            for (p = 0; p < n; p = p + 1) begin
                q = (p < qs) ? 0 : (p < 2 * qs) ? 1 : (p < 3 * qs) ? 2 : 3;
                t = p % C; k = keygen(u, p);
                cs = (ub + 17 * (t / 1024) + 1 + (t % 1024) / 64) * 128 + 2 * (t % 64);
                ss = (ub + 17 * (t / 1024)) * 128 + (t % 1024) / 8;
                put(q, cs, k[255:0], 32'hffffffff);
                put(q, cs + 1, k[511:256], 32'hffffffff);
                put(q, ss, 256'(k[543:512]) << (32 * (t % 8)), 32'hf << (4 * (t % 8)));
            end
        end
    endtask

    // ---------------- sequencer + checker ----------------
    localparam [3:0] T_PRE=0, T_S1=1, T_RUN=2, T_W=3, T_S2=4, T_STOP=5, T_S3=6, T_END=7;
    reg [3:0] t, after;
    integer cycle = 0, beats = 0, checked = 0, qs, exp_beats, t0 = 0, lead = 0;
    integer scan_cycles [0:2];
    integer writes0 = 0, recs0 = 0, migs0 = 0, conc_writes = 0, conc_steps = 0, conc_migs = 0, conc_hw_reqs = 0;
    integer sidx = 0, fw = 0;
    longint wreq = 0;
    reg [543:0] want;
    initial begin t = T_PRE; d_v = 0; nb = 0; scan_go = 0; end
    always @(posedge clk) if (rst_n) begin
        for (integer i = 0; i < 4*NPC; i = i + 1) if (h_v[i] && h_rdy[i] && h_tag[i*TAGW + 12]) wreq = wreq + 1;
    end
    always @(posedge clk) if (rst_n) begin
        cycle <= cycle + 1;
        scan_go <= 0;
        if (p_fault || j_fault || g_fault) $fatal(1, "fault port=%b join=%b geometry=%b", p_fault, j_fault, g_fault);
        if (d_v && d_rdy) begin
            nb <= nb + 1;
            if (DURING != 0 && t != T_W && nb + 1 == LEAD_STEPS + DURING) d_v <= 0;
        end
        case (t)
        T_PRE: begin
            preload(UA, NA);
            scan_user <= 10'(UA); scan_n <= NW'(NA); sidx <= 0; after <= T_W; t <= T_S1;
        end
        T_S1: begin   // launch a scan
            scan_go <= 1; beats <= 0; checked <= 0; t0 <= cycle;
            qs = (int'(scan_n) / 32) * 8; exp_beats = (int'(scan_n) - 3 * qs + 15) / 16;
            t <= T_RUN;
        end
        T_RUN: begin
            if (out_valid) begin : chk
                integer hits, ql, pp;
                hits = 0;
                for (integer a = 0; a < 4; a = a + 1) begin
                    ql = (a == 3) ? int'(scan_n) - 3 * qs : qs;
                    if (out_last[a] !== ((ql == 0) ? (beats == 0) : (beats == (ql - 1) / 16))) $fatal(1, "last");
                    for (integer b = 0; b < 16; b = b + 1) begin
                        pp = beats * 16 + b;
                        if (out_kv[a*16+b] !== (pp < ql)) $fatal(1, "mask beat=%0d q=%0d lane=%0d", beats, a, b);
                        if (pp < ql) begin
                            want = keygen(int'(scan_user), a * qs + pp);
                            if (out_key[(a*16+b)*544 +: 544] !== want)
                                $fatal(1, "key user=%0d position=%0d", scan_user, a * qs + pp);
                            if (out_ref[a*16+b] !== ref_key(want[543:512])) $fatal(1, "ref");
                            hits = hits + 1;
                        end else if (out_key[(a*16+b)*544 +: 544] !== 544'd0) $fatal(1, "padding");
                    end
                end
                beats <= beats + 1; checked <= checked + hits;
                if (beats + 1 == exp_beats) begin
                    scan_cycles[sidx] <= cycle + 1 - t0;
                    t <= after;
                end
            end
        end
        T_W: begin    // start the writer stream, let it fill, then scan UA again
            if (checked != NA) $fatal(1, "scan 1 checked %0d", checked);
            if (LEAD_STEPS == 0) begin
                if (lead == 0) d_v <= 1;
                lead <= lead + 1;
                if (lead == LEAD) begin
                    sidx <= 1; after <= T_STOP; t <= T_S1;
                    conc_steps <= p_records; conc_writes <= p_writes; conc_migs <= p_migs; conc_hw_reqs <= wreq;
                end
            end else begin
                if (lead == 0) begin d_v <= 1; lead <= 1; end
                else if (d_v && d_rdy && nb + 1 == LEAD_STEPS) d_v <= 0;
                else if (!d_v && lead == 1 && !p_busy && nb == LEAD_STEPS) begin
                    lead <= 2; d_v <= 1;
                    sidx <= 1; after <= T_STOP; t <= T_S1;
                    conc_steps <= p_records; conc_writes <= p_writes; conc_migs <= p_migs; conc_hw_reqs <= wreq;
                end
            end
        end
        T_STOP: begin
            if (checked != NA) $fatal(1, "scan 2 checked %0d", checked);
            conc_steps <= p_records - conc_steps; conc_writes <= p_writes - conc_writes;
            conc_migs <= p_migs - conc_migs; conc_hw_reqs <= wreq - conc_hw_reqs;
            if (DURING == 0) d_v <= 0;
            t <= T_S3;
        end
        T_S3: if (!d_v && !p_busy && (DURING == 0 || nb == LEAD_STEPS + DURING)) begin
            scan_user <= 10'(UB); scan_n <= nb; sidx <= 2; after <= T_END; t <= T_S1;
        end
        T_END: begin
            if (checked != int'(scan_n)) $fatal(1, "scan 3 checked %0d of %0d", checked, scan_n);
            $display("W11_CONC scan_alone=%0d scan_concurrent=%0d steps_during=%0d migrations_during=%0d sector_writes_during=%0d writer_requests_during=%0d",
                     scan_cycles[0], scan_cycles[1], conc_steps, conc_migs, conc_writes, conc_hw_reqs);
            $display("W11_CONC_UB user=%0d keys=%0d scan=%0d migrations=%0d copied_sectors=%0d read_stall_cycles=%0d",
                     UB, scan_n, scan_cycles[2], p_migs, p_copied, p_rstall);
            $display("W11_CONC_PASS na=%0d cycles=%0d", NA, cycle);
            $finish;
        end
        default: ;
        endcase
    end
endmodule
