#!/usr/bin/env python3
"""LAYERBENCH-S81: tests of tools/s81_dv/dv_layer_compile.py (pure python, no simulator).

1. Encoders: every field decodes at the bit range the RTL reads it (ot_dsdv_fixed_issue PW / row layout, dsdv_seq_host
   CSR intercept, ot_s81sl_xr CTL payload, ot_s81sl_vp command, ot_s81sl_xs is_d, ot_s81sl_cap cfg_d).
2. Compile L0 (smoke slice) on the die of record: calendar legal for ot_dsdv_fixed_issue (<= 128 rows, done > issue for
   commands, one command per engine per edge, exactly one KIT and one END, END after every done), host boot stream =
   length + BEGIN + 3 PW words a row + SEAL + templates, CTL templates <= 128, the op schedule reproduces the committed
   p4l layer price (results/rtl/s81_layer_tput_1018/layer_price_p4l.json), manifest hashes match the files.
   python3 tools/s81_dv/test_dv_layer_compile.py            (exit 0 = PASS)
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools'))
import dv_layer_compile as C  # noqa: E402


def bits(v, hi, lo):
    return (v >> lo) & ((1 << (hi - lo + 1)) - 1)


def test_encoders():
    # ot_dsdv_fixed_issue header: [27:26] 3, [25] seal, [24:17] 0, [16:9] length, [8:7] start phase, [6:0] stage
    h = C.pw_header(37, stage=5, start_phase=2, seal=True)
    assert (bits(h, 27, 26), bits(h, 25, 25), bits(h, 24, 17), bits(h, 16, 9), bits(h, 8, 7), bits(h, 6, 0)) == (3, 1, 0, 37, 2, 5)
    # row {done [75:52], issue [51:28], engine [27:24], arg [23:0]} and its 3 PW parts (mem[25:0], [51:26], [75:52])
    r = C.pack_row(0xABCDE1, 0x123456, 4, 0xFEDCBA)
    assert (bits(r, 75, 52), bits(r, 51, 28), bits(r, 27, 24), bits(r, 23, 0)) == (0xABCDE1, 0x123456, 4, 0xFEDCBA)
    rec = 0
    for a, d in C.pw_row_words(9, r):
        assert a == 9 and bits(d, 27, 26) in (0, 1, 2)
        k = bits(d, 27, 26)
        rec |= (bits(d, 25, 0) if k < 2 else bits(d, 23, 0)) << (26 * k)
    assert rec == r
    # dsdv_seq_host host word {type 2, x 512, v}: CSR x[7:0]; 0x10 a = x[102:96], d28 = x[59:32]
    w = C.csr_pw(0x55, 0xABCDEF1)
    x = bits(w, 512, 1)
    assert bits(w, 0, 0) == 1 and bits(w, 514, 513) == 0 and bits(x, 7, 0) == 0x10
    assert bits(x, 102, 96) == 0x55 and bits(x, 59, 32) == 0xABCDEF1
    x = bits(C.csr_len(130 & 0xFF), 512, 1)
    assert bits(x, 7, 0) == 0x11 and bits(x, 39, 32) == 130
    p = (1 << 185) | 0x1234
    x = bits(C.csr_template(127, p), 512, 1)
    assert bits(x, 7, 0) == 0x13 and bits(x, 14, 8) == 127 and bits(x, 16 + 185, 16) == p
    x = bits(C.csr_gunit(0x1AB, (1 << 255) | 7), 512, 1)
    assert bits(x, 7, 0) == 0x14 and bits(x, 17, 8) == 0x1AB and bits(x, 32 + 255, 32) == (1 << 255) | 7
    # ot_s81sl_xr CTL payload: [15:0] slice mask, [20:16] target, [25:21] leaf mask, [185:26] body
    body = C.vp_cmd(C.VP['NORM'], a0=0x3FF, a1=37, n=3, imm=(1 << 127) | 9)
    pl = C.ctl_payload(1 << 6, 1, 0x15, body)
    assert (bits(pl, 15, 0), bits(pl, 20, 16), bits(pl, 25, 21), bits(pl, 185, 26)) == (1 << 6, 1, 0x15, body)
    # ot_s81sl_vp c_d: [3:0] op, [13:4] a0, [23:14] a1, [31:24] n, [159:32] imm
    assert (bits(body, 3, 0), bits(body, 13, 4), bits(body, 23, 14), bits(body, 31, 24), bits(body, 159, 32)) == \
        (5, 0x3FF, 37, 3, (1 << 127) | 9)
    # line beat (tb_s81sl_slice_eng ctl(): [0] 1, [3:1] kind 0, [8:4] hops, [12:9] src, [21 +: 186] payload)
    b = C.ctl_line_beat(pl, src=4, hops=1)
    assert bits(b, 0, 0) == 1 and bits(b, 3, 1) == 0 and bits(b, 8, 4) == 1 and bits(b, 12, 9) == 4
    assert bits(b, 21 + 185, 21) == pl and bits(b, 37 + 4, 37) == 1 and bits(b, 42 + 4, 42) == 0x15
    # xfin go: [31:0] eps, [32] ENG, [95:64] Engram scale
    g = C.xfin_go(0x358637BD, True, 0x3F800000)
    assert bits(g, 31, 0) == 0x358637BD and bits(g, 32, 32) == 1 and bits(g, 95, 64) == 0x3F800000
    # ot_s81sl_xs is_d
    i = C.xs_issue(go=1, ph=1023, np_=5, prime=1, start=1, cal_base=0xABC, cal_len=0x1ABC, win=(1, 1), off=200)
    assert bits(i, 0, 0) == 1 and bits(i, 10, 1) == 1023 and bits(i, 13, 11) == 5 and bits(i, 93, 93) == 1
    assert bits(i, 94, 94) == 1 and bits(i, 106, 95) == 0xABC and bits(i, 119, 107) == 0x1ABC
    assert bits(i, 122, 120) == 0b111 and bits(i, 123, 123) == 1 and bits(i, 131, 124) == 200 and bits(i, 159, 132) == 0
    # ot_s81sl_cap cfg_d
    c = C.cap_cfg(obase=0xFFF, ops=0x123, np_=7, fmt=2, rbase=0xBEEF, rcnt=320, rsplit=0x1234, fp32_lo=1, fp32_hi=1)
    assert (bits(c, 11, 0), bits(c, 23, 12), bits(c, 26, 24), bits(c, 28, 27), bits(c, 44, 29), bits(c, 55, 45),
            bits(c, 71, 56), bits(c, 72, 72), bits(c, 73, 73)) == (0xFFF, 0x123, 7, 2, 0xBEEF, 320, 0x1234, 1, 1)


def test_compile_l0():
    tree = C.die_tree()
    out = Path(tempfile.mkdtemp(prefix='dvlc_'))
    r = C.compile_layer('L0', out, tree, 's_0S')
    cal = json.loads((out / 'prog/calendar.json').read_text())
    rows = cal['rows']
    assert 0 < len(rows) <= C.NOPS
    kit = [x for x in rows if x['engine'] == 14]
    end = [x for x in rows if x['engine'] == 15]
    cmds = [x for x in rows if x['engine'] < 14]
    assert len(kit) == 1 and len(end) == 1 and cmds
    assert all(x['done'] > x['issue'] for x in cmds)
    assert all(end[0]['issue'] >= x['done'] for x in cmds)
    assert len({(x['engine'], x['issue']) for x in cmds}) == len(cmds)
    assert all(x['engine'] in (0, 1, 2, 4) for x in cmds)            # ENG_PRESENT 5'b10111
    tm = json.loads((out / 'prog/ctl_templates.json').read_text())
    assert tm['n'] <= C.NOPS
    assert all((x['arg'] & 0x7F) < tm['n'] for x in cmds if x['engine'] in (0, 1))
    hs = (out / 'prog/host_boot.memh').read_text().split()
    assert len(hs) == 2 + 3 * len(rows) + 1 + tm['n']
    # every V command's CTL template targets the smoke slice's sid only
    sid = C.Die(tree).slices()['u_s_0S']['sid']
    for t in tm['templates']:
        assert int(t['payload186'], 16) & 0xFFFF == 1 << sid
    # op schedule = the committed p4l price
    sch = json.loads((out / 'schedule.json').read_text())
    lp = json.loads((ROOT / 'results/rtl/s81_layer_tput_1018/layer_price_p4l.json').read_text())['workloads']['ar']['layers']['L0']
    assert len(sch['ops']) == lp['nodes'] and abs(sch['price']['crit'] - lp['dv_crit']) < 0.5, (sch['price'], lp)
    assert all(e['inst'] in C.Die(tree).inst for e in sch['events'] if not e.get('plan_only'))
    man = json.loads((out / 'manifest.json').read_text())
    for f, h in man['files'].items():
        assert hashlib.sha256((out / f).read_bytes()).hexdigest() == h, f
    low = json.loads((out / 'lowering.json').read_text())
    assert sum(low['status_counts'].values()) == lp['nodes']
    return r


if __name__ == '__main__':
    test_encoders()
    r = test_compile_l0()
    print('TEST_DV_LAYER_COMPILE PASS', json.dumps(dict((k, v) for k, v in r.items() if k != 'smoke')))
