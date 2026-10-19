#!/usr/bin/env python3
"""QXF-LINK 2026-10-18 (TOKEN-XDIE-QWEN F4) unit test: the D2D die masters' TXDP is a compiler output.

  python3 tools/qwen_split/test_d2d_txdp.py      (repository root; also collected by pytest)

1. the producer law (d2d_link_calendar.producer_txd + the PR pin flops) on the die seam stages reproduces the
   LAYERBENCH-QWEN compiled_L1 program's TXD (QW-L1SEAM 10-19: compute [8,3,1,10] on dv2f18dh2, KV [23,4,3,3] on kvs14c;
   before: compute [8,3,1,9], KV [23,4,3,3]: QLB-C4 10-18 recompiled compiled_L1 on
   the dv2f14bq die-run table, where QXF-SEAMC lands C.tx_record at age 2 -> SC_TX 2); dv2f14bn's SC_TX 0 (tx_v +
   tx_payload direct) gave [6,3,1,9];
2. the generated masters carry TXDP as a parameter with no production default (d2d_pinreg_gen.py) and no hard-wired
   PR vector;
3. the committed die-sequencer image equals the compiler's production compile and carries D2D_TXDP_C / D2D_TXDP_K.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_split'))
import d2d_link_calendar as L   # noqa: E402

DIE = '2,2,2,3,2,2/11,11,9,9,9,9,9'      # MU-DQ-TXDP 10-19: the MU release pair seam (dv2f18 / kvs14r-mu)
PROG = ROOT / 'results/rtl/qwen_layer_tput_1018/compiled_L1/d2d/program/calendar.json'
DIES = ROOT / 'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv'
IMG = ROOT / 'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh'


def pr(txd):
    return {e: [x + p for x, p in zip(txd[e], L.PINREG_EXT[e])] for e in txd}


def test_producer_law_matches_compiler():
    got = pr(L.producer_txd(L.parse_stages(DIE)))
    assert got == {'C': [8, 3, 1, 10], 'K': [21, 4, 3, 3]}, got        # MU-DQ-TOK pair co-sim on the netlisted MU seams
    assert L.txdp_word(got['C']) == 0x0a010308 and L.txdp_word(got['K']) == 0x03030415
    q = pr(L.producer_txd(L.parse_stages('2,2,2,2,2,2/11,11,9,9,9,11,11')))   # QLB-C4 dv2f14bq (pre-MU compiled_L1)
    assert q == {'C': [8, 3, 1, 9], 'K': [23, 4, 3, 3]}
    # QW-L1SEAM 10-19: compiled_L1 = the dv2f18dh2 compute seam (record_bundles.seam_stages, the strict-bind source)
    # + the kvs14c KV table (KV MU die table pending): C = the MU pair C; K = the kvs14c K until the KV MU recompile
    c = pr(L.producer_txd(L.parse_stages('2,2,2,3,2,2/11,11,9,9,9,11,11')))
    assert c == json.loads(PROG.read_text())['txd'] and c['C'] == got['C'] and c['K'] == [23, 4, 3, 3]
    bn = pr(L.producer_txd(L.parse_stages('2,2,2,2,0,2/11,11,9,9,9,11,11')))      # dv2f14bn (tx_record direct)
    assert bn['C'] == [6, 3, 1, 9]
    assert L.txdp_word(q['C']) == 0x09010308 and L.txdp_word(q['K']) == 0x03030417


def test_masters_take_txdp_parameter():
    t = DIES.read_text()
    for m in ('qfd_d2d_static', 'qkd_d2d_static'):
        hdr = t[t.index(f'module {m} #('):]
        hdr = hdr[:hdr.index(') (')]
        assert "parameter [31:0] TXDP = 32'd0" in hdr, (m, hdr)
    assert t.count('.TXDP(PR ? TXDP :') == 2
    assert "PR ? {8'd4, 8'd1, 8'd3, 8'd3}" not in t and "PR ? {8'd3, 8'd3, 8'd4, 8'd3}" not in t
    assert t.count('D2D_TXDP_NOT_COMPILED__set_TXDP_from_the_compiler') == 2


def test_committed_image_is_the_compilers():
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(['bash', 'tools/qwen_split/d2d_cal_image_production.sh', d], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL)
        assert Path(d, 'd2d_cal_image.svh').read_text() == IMG.read_text()
        assert "QFD_D2D_TXDP = 32'h0a010308" in Path(d, 'program', 'txdp.svh').read_text()
    t = IMG.read_text()
    assert "localparam [31:0] D2D_TXDP_C = 32'h0a010308;" in t and "localparam [31:0] D2D_TXDP_K = 32'h03030415;" in t


if __name__ == '__main__':
    for f in (test_producer_law_matches_compiler, test_masters_take_txdp_parameter, test_committed_image_is_the_compilers):
        f()
        print('PASS', f.__name__)
    print('TEST_D2D_TXDP_PASS')
