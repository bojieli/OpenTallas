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


CRCF = """    // margin-first CRC pipeline helpers: crc_fold(s, w) = crc_fold(s, 0) ^ crc_fold(0, w_lo) ^ crc_fold(0, w_hi)
    function automatic [31:0] crc_s(input [31:0] s); crc_s = crc_fold(s, 256'd0); endfunction
    function automatic [31:0] crc_lo(input [255:0] w); crc_lo = crc_fold(32'd0, {128'd0, w[127:0]}); endfunction
    function automatic [31:0] crc_hi(input [255:0] w); crc_hi = crc_fold(32'd0, {w[255:128], 128'd0}); endfunction
"""

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
