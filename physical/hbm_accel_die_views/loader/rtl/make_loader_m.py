#!/usr/bin/env python3
"""Margin-first loader (CLAUDE HBM-ABSTRACTS spine, owner rule 2026-10-06): copies of the loader host, LOAD and STORE
engines (rtl/hbm_accel/loader/ot_hbm_accel_{loader_host,loader,store}.sv, unchanged) with every CRC-32 fold pipelined.

The failing class (ld3 CTS: -4229 ps at u_store crc_got, 42,497 endpoints) is the 256-bit-per-beat CRC recurrence
crc <= crc_fold(crc, w).  crc_fold is linear over GF(2): crc_fold(s, w) = crc_fold(s, 0) ^ crc_fold(0, w_lo) ^
crc_fold(0, w_hi) (w_lo / w_hi: w with the other half zeroed).  So each fold becomes
  P1  w (and its valid) registered;
  P2  the two 128-bit data partials crc_fold(0, w_lo), crc_fold(0, w_hi) registered (feed-forward XOR trees);
  P3  crc <= crc_fold(crc, 0) ^ partials (the recurrence: a 32 x 32 XOR matrix plus one XOR level).
Every consumer of a final CRC (completion status, completion record) waits until its pipeline is empty: the result is
the same value, 2 cycles later at most.  Nothing else changes.  Exactness: tb_loader_m_equiv.sv (original vs margin
hosts, same AXI-lite programs, DMA image and memory model: every memory request, every AXI DMA beat, the final CSRs).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent
SRC = ROOT / 'rtl/hbm_accel/loader'


def edit(text, reps):
    for a, b in reps:
        assert text.count(a) == 1, (a[:80], text.count(a))
        text = text.replace(a, b)
    return text


POLY = 0x04C11DB7


def _fold(s, w, n=256):
    """crc_fold(s, w) of the RTL (MSB-first shift, w[0] first) on Python ints"""
    for i in range(n):
        fb = ((s >> 31) ^ (w >> i)) & 1
        s = ((s << 1) & 0xFFFFFFFF) ^ (POLY if fb else 0)
    return s


def _masks(nin, col):
    """32 masks of nin bits: mask[j] bit i = output bit j of the linear map applied to unit vector i"""
    m = [0] * 32
    for i in range(nin):
        y = col(i)
        for j in range(32):
            if (y >> j) & 1:
                m[j] |= 1 << i
    return m


def _lp(name, masks, nin):
    v = 0
    for j, m in enumerate(masks):
        v |= m << (j * nin)
    return f"    localparam [{32 * nin - 1}:0] {name} = {32 * nin}'h{v:0{(32 * nin) // 4}x};\n"


# Margin route ldm7 (SS -3,753 ps at mp1_w -> mp2_lo, a 70-level XNOR chain): the loop-form crc_fold synthesised as
# the serial 128-step recurrence even with zero state.  The partials and the state fold are now written as explicit
# GF(2) matrices: output bit j = ^(input & M[j]) -> a balanced $reduce_xor tree (<= 7 XOR levels for 128 inputs,
# <= 5 for the 32-bit state).  Same linear maps (masks computed from crc_fold itself), so the same values.
CRCF = ("""    // margin-first CRC pipeline helpers: crc_fold(s, w) = crc_fold(s, 0) ^ crc_fold(0, w_lo) ^ crc_fold(0, w_hi),
    // each written as a constant GF(2) matrix (bit j = XOR-reduce of input & M[j]: balanced trees, not the serial loop)
""" + _lp('CRC_M_LO', _masks(128, lambda i: _fold(0, 1 << i)), 128)
        + _lp('CRC_M_HI', _masks(128, lambda i: _fold(0, 1 << (128 + i))), 128)
        + _lp('CRC_M_S', _masks(32, lambda i: _fold(1 << i, 0)), 32)
        + """    function automatic [31:0] crc_s(input [31:0] s);
        integer j; begin for (j = 0; j < 32; j = j + 1) crc_s[j] = ^(s & CRC_M_S[j*32 +: 32]); end
    endfunction
    function automatic [31:0] crc_lo(input [255:0] w);
        integer j; begin for (j = 0; j < 32; j = j + 1) crc_lo[j] = ^(w[127:0] & CRC_M_LO[j*128 +: 128]); end
    endfunction
    function automatic [31:0] crc_hi(input [255:0] w);
        integer j; begin for (j = 0; j < 32; j = j + 1) crc_hi[j] = ^(w[255:128] & CRC_M_HI[j*128 +: 128]); end
    endfunction
""")
# self-check of the matrices against the loop form (random vectors)
import random as _r
_g = _r.Random(1)
_ML = _masks(128, lambda i: _fold(0, 1 << i)); _MH = _masks(128, lambda i: _fold(0, 1 << (128 + i)))
_MS = _masks(32, lambda i: _fold(1 << i, 0))
_ap = lambda M, x: sum(((bin(x & M[j]).count('1') & 1) << j) for j in range(32))  # noqa: E731
for _ in range(200):
    _s, _w = _g.getrandbits(32), _g.getrandbits(256)
    assert _fold(_s, _w) == _ap(_MS, _s) ^ _ap(_ML, _w & ((1 << 128) - 1)) ^ _ap(_MH, _w >> 128)

# ARITH (margin-first, ldm7: after the CRC, 2,475 classes at SS -0.9 .. -2.2 ns are ripple-mapped wide counters:
# (r_idx - f_idx) < VOUT, rem = n_sec - ar_sec -> min -> ar_sec / ar_next adds, req_addr = base + idx << 5, the
# 32-bit increments).  ABC re-ripples behavioural adders in context, so every wide add is a (* keep *) Kogge-Stone
# (rtl/hdc/ot_hdc_prefix.sv), differences that only feed compares are kept as registers updated with their operands
# (rem_q == n_sec - ar_sec, vin == r_idx - f_idx, wa_q / ra_q == m_base + idx << 5 at every edge), and the burst
# length is computed on 8 bits.  Same values, same cycles (tb_loader_m_equiv.sv).
LOAD_ARITH = [
    ("""        wire [31:0] rem = n_sec - ar_sec;
        wire [31:0] to4k = 32'd128 - {25'd0, ar_next[11:5]};
        wire [31:0] blen0 = (rem < BURST) ? rem : BURST;
        wire [31:0] blen = (blen0 < to4k) ? blen0 : to4k;""",
     """        reg  [31:0] rem_q;                       // ARITH: n_sec - ar_sec
        wire [7:0]  rem8 = rem_q[7:0];
        wire        rem_small = ~|rem_q[31:8] && (rem8 < 8'(BURST));
        wire [7:0]  to4k8 = 8'd128 - {1'b0, ar_next[11:5]};
        wire [7:0]  blen0_8 = rem_small ? rem8 : 8'(BURST);
        wire [7:0]  blen8 = (blen0_8 < to4k8) ? blen0_8 : to4k8;
        wire [31:0] blen = {24'd0, blen8};
        wire [31:0] ar_sec_nx, rem_nx, cycles_nx, rx_sec_nx;
        wire [51:0] ar_hi_nx;
        wire [7:0]  ar_lo_nx = {1'b0, ar_next[11:5]} + blen8;
        ot_hdc_ksadd_k #(.W(32)) u_k_arsec (.a(ar_sec), .b(blen), .cin(1'b0), .s(ar_sec_nx), .cout());
        ot_hdc_ksadd_k #(.W(32)) u_k_rem (.a(rem_q), .b(~blen), .cin(1'b1), .s(rem_nx), .cout());
        ot_hdc_inc_k #(.W(52)) u_k_arhi (.a(ar_next[63:12]), .inc(ar_lo_nx[7]), .y(ar_hi_nx), .co());
        ot_hdc_inc_k #(.W(32)) u_k_cyc (.a(cycles), .inc(1'b1), .y(cycles_nx), .co());
        ot_hdc_inc_k #(.W(32)) u_k_rx (.a(rx_sec), .inc(1'b1), .y(rx_sec_nx), .co());"""),
    ("n_sec <= 0; ar_sec <= 0; rx_sec <= 0; out_bursts <= 0; axi_err <= 0; cmd_pend <= 0; crc_bad <= 0;",
     "n_sec <= 0; ar_sec <= 0; rem_q <= 0; rx_sec <= 0; out_bursts <= 0; axi_err <= 0; cmd_pend <= 0; crc_bad <= 0;"),
    ("busy <= 1; n_sec <= nbytes >> 5; ar_sec <= 0; rx_sec <= 0; out_bursts <= 0;",
     "busy <= 1; n_sec <= nbytes >> 5; ar_sec <= 0; rem_q <= nbytes >> 5; rx_sec <= 0; out_bursts <= 0;"),
    ("if (busy) cycles <= cycles + 1;", "if (busy) cycles <= cycles_nx;"),
    ("""                if (busy && !m_arvalid && ar_sec != n_sec && out_bursts < MAXOUT[7:0]) begin
                    m_arvalid <= 1; m_araddr <= ar_next; m_arlen <= blen[7:0] - 8'd1;
                    ar_sec <= ar_sec + blen; ar_next <= ar_next + {27'd0, blen, 5'd0};""",
     """                if (busy && !m_arvalid && rem_q != 32'd0 && out_bursts < MAXOUT[7:0]) begin
                    m_arvalid <= 1; m_araddr <= ar_next; m_arlen <= blen[7:0] - 8'd1;
                    ar_sec <= ar_sec_nx; rem_q <= rem_nx; ar_next <= {ar_hi_nx, ar_lo_nx[6:0], ar_next[4:0]};"""),
    ("out_bursts <= out_bursts + ((busy && !m_arvalid && ar_sec != n_sec && out_bursts < MAXOUT[7:0]) ? 8'd1 : 8'd0)",
     "out_bursts <= out_bursts + ((busy && !m_arvalid && rem_q != 32'd0 && out_bursts < MAXOUT[7:0]) ? 8'd1 : 8'd0)"),
    ("rx_sec <= rx_sec + 1;", "rx_sec <= rx_sec_nx;"),
    ("""        wire r_can = ms == M_VERIFY && r_idx != m_n && (r_idx - f_idx) < VOUT;""",
     """        reg  [VB:0] vin;                         // ARITH: r_idx - f_idx (read-backs in flight)
        reg  [31:0] wa_q, ra_q;                  // ARITH: m_base + w_idx << 5, m_base + r_idx << 5
        wire [31:0] wa_nx, ra_nx, w_idx_nx, w_ack_nx, r_idx_nx, f_idx_nx;
        ot_hdc_ksadd_k #(.W(32)) u_k_wa (.a(wa_q), .b(32'd32), .cin(1'b0), .s(wa_nx), .cout());
        ot_hdc_ksadd_k #(.W(32)) u_k_ra (.a(ra_q), .b(32'd32), .cin(1'b0), .s(ra_nx), .cout());
        ot_hdc_inc_k #(.W(32)) u_k_wi (.a(w_idx), .inc(1'b1), .y(w_idx_nx), .co());
        ot_hdc_inc_k #(.W(32)) u_k_wk (.a(w_ack), .inc(1'b1), .y(w_ack_nx), .co());
        ot_hdc_inc_k #(.W(32)) u_k_ri (.a(r_idx), .inc(1'b1), .y(r_idx_nx), .co());
        ot_hdc_inc_k #(.W(32)) u_k_fi (.a(f_idx), .inc(1'b1), .y(f_idx_nx), .co());
        wire r_can = ms == M_VERIFY && r_idx != m_n && vin < VOUT;"""),
    ("assign req_addr  = m_base + ((ms == M_WRITE ? w_idx : r_idx) << 5);", "assign req_addr  = (ms == M_WRITE) ? wa_q : ra_q;"),
    ("ms <= M_IDLE; m_base <= 0; m_n <= 0; w_idx <= 0; w_ack <= 0; r_idx <= 0; f_idx <= 0;",
     "ms <= M_IDLE; m_base <= 0; m_n <= 0; w_idx <= 0; w_ack <= 0; r_idx <= 0; f_idx <= 0; vin <= 0; wa_q <= 0; ra_q <= 0;"),
    ("if (rsp_we) w_ack <= w_ack + 1;", "if (rsp_we) w_ack <= w_ack_nx;"),
    ("w_idx <= 0; w_ack <= 0; r_idx <= 0; f_idx <= 0; vcrc <= 32'hFFFFFFFF; m_fault <= 0;",
     "w_idx <= 0; w_ack <= 0; r_idx <= 0; f_idx <= 0; vcrc <= 32'hFFFFFFFF; m_fault <= 0;\n"
     "                        vin <= 0; wa_q <= c_d[31:0]; ra_q <= c_d[31:0];"),
    ("if (req_v && req_rdy) w_idx <= w_idx + 1;", "if (req_v && req_rdy) begin w_idx <= w_idx_nx; wa_q <= wa_nx; end"),
    ("""                        if (req_v && req_rdy) r_idx <= r_idx + 1;
                        if (fold_now) f_idx <= f_idx + 1;""",
     """                        if (req_v && req_rdy) begin r_idx <= r_idx_nx; ra_q <= ra_nx; end
                        if (fold_now) f_idx <= f_idx_nx;
                        vin <= vin + (req_v && req_rdy) - fold_now;"""),
]
STORE_ARITH = [
    (""" wire[31:0] remaining=nsec-aw_sec,to4k=128-{25'b0,aw_next[11:5]};
 wire[31:0] len0=remaining<BURST?remaining:BURST;
 wire[31:0] len=len0<to4k?len0:to4k;""",
     """ // ARITH (see make_loader_m.py): rem_q == nsec - aw_sec, Kogge-Stone adds, 8-bit burst length, range checks on KS sums
 reg[31:0] rem_q;
 wire[7:0] rem8=rem_q[7:0];wire rem_small=~|rem_q[31:8]&&(rem8<8'(BURST));
 wire[7:0] to4k8=8'd128-{1'b0,aw_next[11:5]};wire[7:0] len0_8=rem_small?rem8:8'(BURST);
 wire[7:0] len8=len0_8<to4k8?len0_8:to4k8;wire[31:0] len={24'd0,len8};
 wire[31:0] aw_sec_nx,rem_nx,cycles_nx,w_sec_nx,rng_ds,issued_nx,retired_nx,ra_nx;wire[63:0] rng_hs;wire[51:0] aw_hi_nx;wire rng_dc,rng_hc;
 wire[7:0] aw_lo_nx={1'b0,aw_next[11:5]}+m_awlen+8'd1;
 ot_hdc_ksadd_k #(.W(32)) u_k_awsec(.a(aw_sec),.b({24'b0,m_awlen}),.cin(1'b1),.s(aw_sec_nx),.cout());
 ot_hdc_ksadd_k #(.W(32)) u_k_rem(.a(rem_q),.b(~{24'b0,m_awlen}),.cin(1'b0),.s(rem_nx),.cout());
 ot_hdc_inc_k #(.W(52)) u_k_awhi(.a(aw_next[63:12]),.inc(aw_lo_nx[7]),.y(aw_hi_nx),.co());
 ot_hdc_inc_k #(.W(32)) u_k_cyc(.a(cycles),.inc(1'b1),.y(cycles_nx),.co());
 ot_hdc_inc_k #(.W(32)) u_k_ws(.a(w_sec),.inc(1'b1),.y(w_sec_nx),.co());
 ot_hdc_ksadd_k #(.W(32)) u_k_rngd(.a(daddr),.b(nbytes),.cin(1'b0),.s(rng_ds),.cout(rng_dc));
 ot_hdc_ksadd_k #(.W(64)) u_k_rngh(.a(haddr),.b({32'b0,nbytes}),.cin(1'b0),.s(rng_hs),.cout(rng_hc));
 wire rng_bad=(rng_dc&&|rng_ds)||(rng_hc&&|rng_hs);   // {0,daddr}+{0,nbytes} > 2^32 || {0,haddr}+nbytes > 2^64"""),
    ("cmd_pending<=0;mem_complete<=0;axi_err<=0;nsec<=0;aw_sec<=0;", "cmd_pending<=0;mem_complete<=0;axi_err<=0;nsec<=0;aw_sec<=0;rem_q<=0;"),
    ("||{1'b0,daddr}+{1'b0,nbytes}>33'h100000000||{1'b0,haddr}+{33'b0,nbytes}>65'h10000000000000000)", "||rng_bad)"),
    ("busy<=1;cmd_pending<=1;nsec<=nbytes>>5;aw_sec<=0;", "busy<=1;cmd_pending<=1;nsec<=nbytes>>5;aw_sec<=0;rem_q<=nbytes>>5;"),
    ("if(busy)cycles<=cycles+1;", "if(busy)cycles<=cycles_nx;"),
    ("w_left==0&&aw_sec!=nsec&&outstanding<MAXOUT)", "w_left==0&&rem_q!=0&&outstanding<MAXOUT)"),
    ("aw_sec<=aw_sec+{24'b0,m_awlen}+1;aw_next<=aw_next+(({56'b0,m_awlen}+1)<<5);",
     "aw_sec<=aw_sec_nx;rem_q<=rem_nx;aw_next<={aw_hi_nx,aw_lo_nx[6:0],aw_next[4:0]};"),
    ("w_sec<=w_sec+1'b1;", "w_sec<=w_sec_nx;"),
    ("assign req_addr=base+(issued<<5);", "assign req_addr=ra_q;"),
    (" wire[VB-1:0] slot=issued[VB-1:0],", " reg[31:0] ra_q;   // ARITH: base + issued << 5\n"
     " ot_hdc_inc_k #(.W(32)) u_k_iss(.a(issued),.inc(1'b1),.y(issued_nx),.co());\n"
     " ot_hdc_inc_k #(.W(32)) u_k_ret(.a(retired),.inc(1'b1),.y(retired_nx),.co());\n"
     " ot_hdc_ksadd_k #(.W(32)) u_k_ra(.a(ra_q),.b(32'd32),.cin(1'b0),.s(ra_nx),.cout());\n"
     " wire[VB-1:0] slot=issued[VB-1:0],"),
    ("active<=0;fault<=0;base<=0;", "active<=0;fault<=0;base<=0;ra_q<=0;"),
    ("base<=cd[31:0];total<=cd[63:32];issued<=0;", "base<=cd[31:0];ra_q<=cd[31:0];total<=cd[63:32];issued<=0;"),
    ("if(send)begin issued<=issued+1'b1;", "if(send)begin issued<=issued_nx;ra_q<=ra_nx;"),
    ("if(fold)begin retired<=retired+1'b1;", "if(fold)begin retired<=retired_nx;"),
]

# ---------------- LOAD engine
t = (SRC / 'ot_hbm_accel_loader.sv').read_text()
t = edit(t, [
    ('module ot_hbm_accel_loader #(', 'module ot_hfd_loader_m #('),
    ("""    endfunction

    generate if (ENABLE == 0) begin : g_off""", """    endfunction
""" + CRCF + """
    generate if (ENABLE == 0) begin : g_off"""),
    # host side: pipelined crc_got
    ("""        wire [63:0] haddr = {haddr_hi, haddr_lo};""", """        wire [63:0] haddr = {haddr_hi, haddr_lo};
        // CRC pipeline (host): P1 beat data, P2 partials; crc_got is folded at P3
        reg         hp1_v, hp2_v;
        reg [255:0] hp1_w;
        reg [31:0]  hp2_lo, hp2_hi;
        always @(posedge clk_host or negedge rst_host_n) begin
            if (!rst_host_n) begin hp1_v <= 1'b0; hp2_v <= 1'b0; end
            else begin hp1_v <= m_rvalid && m_rready; hp2_v <= hp1_v; end
        end
        always @(posedge clk_host) begin
            hp1_w <= m_rdata; hp2_lo <= crc_lo(hp1_w); hp2_hi <= crc_hi(hp1_w);
        end
        wire hp_busy = hp1_v || hp2_v;"""),
    ("""                    crc_got <= crc_fold(crc_got, m_rdata);
""", ""),
    ("""                if (busy) cycles <= cycles + 1;""", """                if (busy) cycles <= cycles + 1;
                if (hp2_v) crc_got <= crc_s(crc_got) ^ hp2_lo ^ hp2_hi;"""),
    ("""                if (busy && cpl_v) begin""", """                if (busy && cplh_v && !hp_busy) begin"""),
    ("""                    vcrc_got <= cpl_d[31:0]; sectors <= cpl_d[63:32];
                    if (axi_err) status <= 4'd4;
                    else if (cpl_d[67:64] != 0) status <= cpl_d[67:64];
                    else if (crc_got != crc_exp) status <= 4'd1;
                    else if (verify && cpl_d[31:0] != crc_exp) status <= 4'd2;""",
     """                    vcrc_got <= cplh_d[31:0]; sectors <= cplh_d[63:32];
                    if (axi_err) status <= 4'd4;
                    else if (cplh_d[67:64] != 0) status <= cplh_d[67:64];
                    else if (crc_got != crc_exp) status <= 4'd1;
                    else if (verify && cplh_d[31:0] != crc_exp) status <= 4'd2;"""),
    ("""        wire        cpl_v;
        wire [67:0] cpl_d;                       // {status[3:0], sectors[31:0], vcrc[31:0]}""",
     """        wire        cpl_v;
        wire [67:0] cpl_d;                       // {status[3:0], sectors[31:0], vcrc[31:0]}
        // the completion is held until the CRC pipeline is empty (it is a one-cycle pulse from the crossing)
        reg         cplh_v;
        reg  [67:0] cplh_d;
        always @(posedge clk_host or negedge rst_host_n) begin
            if (!rst_host_n) begin cplh_v <= 1'b0; cplh_d <= 68'd0; end
            else if (cpl_v) begin cplh_v <= 1'b1; cplh_d <= cpl_d; end
            else if (cplh_v && !hp_busy) cplh_v <= 1'b0;
        end"""),
    # mem side: vcrc
    ("""        wire fold_now = ms == M_VERIFY && rob_v[f_idx[VB-1:0]];""", """        wire fold_now = ms == M_VERIFY && rob_v[f_idx[VB-1:0]];
        // CRC pipeline (memory): P1 the retired read-back sector, P2 partials; vcrc is folded at P3
        reg         mp1_v, mp2_v;
        reg [255:0] mp1_w;
        reg [31:0]  mp2_lo, mp2_hi;
        always @(posedge clk_mem or negedge rst_mem_n) begin
            if (!rst_mem_n) begin mp1_v <= 1'b0; mp2_v <= 1'b0; end
            else begin mp1_v <= fold_now; mp2_v <= mp1_v; end
        end
        always @(posedge clk_mem) begin
            mp1_w <= rob[f_idx[VB-1:0]]; mp2_lo <= crc_lo(mp1_w); mp2_hi <= crc_hi(mp1_w);
        end
        wire mp_busy = mp1_v || mp2_v;"""),
    ("""                        if (fold_now) begin
                            vcrc <= crc_fold(vcrc, rob[f_idx[VB-1:0]]);
                            f_idx <= f_idx + 1;
                        end""", """                        if (fold_now) f_idx <= f_idx + 1;"""),
    ("""                if (k_v && k_rdy) k_v <= 0;""", """                if (k_v && k_rdy) k_v <= 0;
                if (mp2_v) vcrc <= crc_s(vcrc) ^ mp2_lo ^ mp2_hi;"""),
    ("""                    M_CPL: if (!k_v) begin""", """                    M_CPL: if (!k_v && !mp_busy) begin"""),
])
t = edit(t, LOAD_ARITH)
(OUT / 'ot_hfd_loader_m.sv').write_text(
    '// GENERATED by make_loader_m.py from rtl/hbm_accel/loader/ot_hbm_accel_loader.sv (margin-first CRC pipeline; see there)\n' + t)

# ---------------- STORE engine
t = (SRC / 'ot_hbm_accel_store.sv').read_text()
t = edit(t, [
    ('module ot_hbm_accel_store #(', 'module ot_hfd_store_m #('),
    (""" endfunction
 generate if(!ENABLE)begin:g_off""", """ endfunction
""" + CRCF + """ generate if(!ENABLE)begin:g_off"""),
    (""" if(w)begin w_left<=w_left-1'b1;w_sec<=w_sec+1'b1;crc_got<=crc_fold(crc_got,dd);end""",
     """ if(w)begin w_left<=w_left-1'b1;w_sec<=w_sec+1'b1;end
 if(hp2_v)crc_got<=crc_s(crc_got)^hp2_lo^hp2_hi;"""),
    (""" if(busy&&mem_complete&&w_sec==nsec&&aw_sec==nsec&&outstanding==0&&!m_awvalid&&w_left==0)begin""",
     """ if(busy&&mem_complete&&w_sec==nsec&&aw_sec==nsec&&outstanding==0&&!m_awvalid&&w_left==0&&!hp_busy)begin"""),
    (""" wire data_ovf=overflow0||overflow1||overflow2;""", """ wire data_ovf=overflow0||overflow1||overflow2;
 // CRC pipeline (host): P1 the written sector, P2 partials; crc_got is folded at P3
 reg hp1_v,hp2_v;reg[255:0] hp1_w;reg[31:0] hp2_lo,hp2_hi;
 always @(posedge clk_host or negedge rst_host_n)if(!rst_host_n)begin hp1_v<=0;hp2_v<=0;end else begin hp1_v<=w;hp2_v<=hp1_v;end
 always @(posedge clk_host)begin hp1_w<=dd;hp2_lo<=crc_lo(hp1_w);hp2_hi<=crc_hi(hp1_w);end
 wire hp_busy=hp1_v||hp2_v;"""),
    (""" wire fold=kv&&krdy;""", """ wire fold=kv&&krdy;
 // CRC pipeline (memory): P1 the retired sector, P2 partials; mcrc is folded at P3
 reg mp1_v,mp2_v;reg[255:0] mp1_w;reg[31:0] mp2_lo,mp2_hi;
 always @(posedge clk_mem or negedge rst_mem_n)if(!rst_mem_n)begin mp1_v<=0;mp2_v<=0;end else begin mp1_v<=fold;mp2_v<=mp1_v;end
 always @(posedge clk_mem)begin mp1_w<=ordered_data;mp2_lo<=crc_lo(mp1_w);mp2_hi<=crc_hi(mp1_w);end
 wire mp_busy=mp1_v||mp2_v;"""),
    (""" if(fold)begin mcrc<=crc_fold(mcrc,ordered_data);retired<=retired+1'b1;valid[head]<=0;live[head]<=0;end
 if(active&&retired==total)begin""", """ if(fold)begin retired<=retired+1'b1;valid[head]<=0;live[head]<=0;end
 if(mp2_v)mcrc<=crc_s(mcrc)^mp2_lo^mp2_hi;
 if(active&&retired==total&&!mp_busy)begin"""),
])
t = edit(t, STORE_ARITH)
(OUT / 'ot_hfd_store_m.sv').write_text(
    '// GENERATED by make_loader_m.py from rtl/hbm_accel/loader/ot_hbm_accel_store.sv (margin-first CRC pipeline; see there)\n' + t)

# ---------------- host: the same, instantiating the margin engines
t = (SRC / 'ot_hbm_accel_loader_host.sv').read_text()
t = edit(t, [
    ('module ot_hbm_accel_loader_host #(', 'module ot_hfd_loader_host_m #('),
    (' ot_hbm_accel_loader #(.ENABLE(1)) u_load(', ' ot_hfd_loader_m #(.ENABLE(1)) u_load('),
    (' ot_hbm_accel_store #(.ENABLE(1),.TW(15)) u_store(', ' ot_hfd_store_m #(.ENABLE(1),.TW(15)) u_store('),
])
(OUT / 'ot_hfd_loader_host_m.sv').write_text(
    '// GENERATED by make_loader_m.py from rtl/hbm_accel/loader/ot_hbm_accel_loader_host.sv (margin engines; see there)\n' + t)
print('ok')
