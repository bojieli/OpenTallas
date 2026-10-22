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


def test_send_cfg_b_width():
    # ot_s81sl_xr send config: dir B with <= 2 pairs encodes; > 2 pairs is refused (xr would fault: 513-b band word)
    w = C.send_cfg('B', pairs=2, dst_row=5)
    assert bits(w, 3, 0) == 8 and bits(w, 42, 41) == 1 and bits(w, 40, 31) == 5
    assert bits(C.send_cfg('EW', pairs=4), 42, 41) == 3
    for bad in (3, 4):
        try:
            C.send_cfg('BE', pairs=bad)
        except AssertionError:
            continue
        raise AssertionError(f'B send with {bad} pairs accepted')


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


def test_previous_pre_source():
    """Current HC is deliberately late and different: it must never gate/use NORMR."""
    tree = C.die_tree()
    die = C.Die(tree)
    sl = 'u_s_0S'
    p = C.Prog(die)
    p.events = [dict(cycle=1481, tag='attn.hc.coef_row0', port='vo_s'),
                dict(cycle=9000, tag='ffn.hc.coef_row0', port='vo_s')]
    a = C.lower_norm_smoke(die, p, sl, 3, which='attn')
    assert a['hc_pre_row'] == 1008 and a['dep_shift'] == 0
    assert not a['hc_pre_source_bound'] and a['hc_pre_row_land'] is None
    assert a['hc_pre_source'] == 'entry.previous_ffn.hc.coef_row0'
    p = C.Prog(die)
    p.events = [dict(cycle=1481, tag='attn.hc.coef_row0', port='vo_s'),
                dict(cycle=9000, tag='ffn.hc.coef_row0', port='vo_s')]
    f = C.lower_norm_smoke(die, p, sl, 3, which='ffn')
    assert f['hc_pre_row'] == 1000 and f['hc_pre_source_event_present'] and not f['hc_pre_source_bound']
    assert f['hc_pre_row_land'] < 2000 and f['dep_shift'] < 2000
    assert f['hc_pre_source'] == 'attn.hc.coef_row0'
    # The op status must not inherit full-layer qualification from the vp bench.
    m = dict(C.family_lowerings())['vpx']
    for op in ('attn.hc_pre', 'ffn.hc_pre'):
        r = m.lower(die, {'op': op}, {'slice': sl})
        assert r['status'] == 'PARTIAL' and 'binding is absent' in r['gap']['missing']
    return {'attn': a, 'ffn': f}


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
    j0 = cal['job'][0]
    hs = (out / ('prog/host_boot.memh' if cal['jobs'] == 1 else 'prog/job0/host_boot.memh')).read_text().split()
    ngu = len(json.loads((out / 'prog/gunit_rows.json').read_text())['rows'])
    assert len(hs) == j0['host_words'] == 2 + 3 * j0['nops'] + 1 + len(j0.get('templates') or range(tm['n'])) + ngu
    # every V command's CTL template targets ONE slice: the smoke slice, or (vpx collective legs) its end slice
    sl = C.Die(tree).slices()
    sid = sl['u_s_0S']['sid']
    for t in tm['templates']:
        m = int(t['payload186'], 16) & 0xFFFF
        if t['name'].startswith('gu.'):          # gunit job words (engine 2 cw), not CTL beats
            continue
        if t['name'].startswith('vpx.'):
            assert m == 1 << sl[t['name'].split('.')[1]]['sid'], t['name']
        else:
            assert m == 1 << sid, t['name']
    # op schedule = the committed p4l price
    sch = json.loads((out / 'schedule.json').read_text())
    lp = json.loads((ROOT / 'results/rtl/s81_layer_tput_1018/layer_price_p4l.json').read_text())['workloads']['ar']['layers']['L0']
    assert len(sch['ops']) == lp['nodes'] and abs(sch['price']['crit'] - lp['dv_crit']) < 0.5, (sch['price'], lp)
    assert all(e['inst'] in C.Die(tree).inst for e in sch['events'] if not e.get('plan_only') and e['dir'] != 'internal')
    man = json.loads((out / 'manifest.json').read_text())
    for f, h in man['files'].items():
        assert hashlib.sha256((out / f).read_bytes()).hexdigest() == h, f
    low = json.loads((out / 'lowering.json').read_text())
    assert sum(low['status_counts'].values()) == lp['nodes']
    return r


def test_events_g8():
    """LB2-S81/EVENTS on the G8 die (bind_p4l3_g8 + land plan p4l3) with the L0 fixtures: every V calendar row has its
    CTL arrival at each slice of its mask (row issue + ctl_path), family CTL events agree with it and name their template
    in the shared table, every vs command rides one (ctl_at), QF / PV / SVCDONE / RD carry bit-exact words"""
    import gzip, os, re, shutil
    fx = Path(os.environ.get('DV_L0_FIXTURES', str(Path.home() / 'scratch/layerbench-s81/fixtures/L0')))
    g8 = ROOT / 'results/arch/s81_dv_1016/bind_p4l3_g8/die.v.gz'
    if not fx.exists() or not g8.exists():
        print('SKIP test_events_g8 (no L0 fixtures / G8 bind)')
        return None
    tree = Path(tempfile.mkdtemp(prefix='dvlc_g8_'))
    for d, src in (('results/arch/s81_dv_1016/bind9/die.v.gz', g8),
                   ('results/arch/s81_dv_1016/p4l/plan.json', ROOT / 'results/arch/s81_dv_1016/p4l/plan.json'),
                   ('results/arch/s81_dv_1016/landing/p4l/land_plan.json',
                    ROOT / 'results/arch/s81_dv_1016/landing/p4l3/land_plan.json')):
        (tree / d).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, tree / d)
    out = tree / 'prog'
    C.compile_layer('L0', out, tree, 's_0S', fixtures=fx)
    die = C.Die(tree)
    sch = json.loads((out / 'schedule.json').read_text())
    T = json.loads((out / 'prog/ctl_templates.json').read_text())['templates']
    # rows: per job; arg[6:0] is the JOB-local template index (job 'templates' = global indices), issue job-relative
    rows = []
    for j in json.loads((out / 'prog/calendar.json').read_text())['job']:
        tm = j.get('templates') or list(range(len(T)))
        for r in j['rows']:
            rows.append(dict(r, issue=r['issue'] + j['layer_issue0'], ti=tm[r['arg'] & 0x7F] if r['engine'] in (0, 1, 2) else None))
    ev = sch['events']
    # slice-bound CTL beats only (the G-unit's own CTL row beats out of vo_n / vo_s are dir out, payload 'row R ...')
    ev_ctl = [e for e in ev if e['kind'] == 'CTL' and e['dir'] == 'in']
    ctl = {(e['inst'], int(e['payload'].split()[1].rstrip(';')), e['cycle']) for e in ev_ctl}
    sid_of = {v['sid']: k for k, v in die.slices().items()}
    n = 0
    for r in rows:
        if r['engine'] not in (0, 1):
            continue
        ti = r['ti']
        m = int(T[ti]['payload186'], 16) & 0xFFFF
        for sid in range(16):
            sl = sid_of.get(sid)
            if (m >> sid) & 1 and sl and sl.endswith('N' if r['engine'] == 0 else 'S'):
                assert (sl, ti, r['issue'] + C.ctl_path(die, sl)['edges']) in ctl, (r, sl)
                n += 1
    assert n == len(ev_ctl) and sch['row_ctl_events'] > 0
    for e in ev:
        if e['kind'] == 'CTL' and e['dir'] == 'in':
            tn = T[int(e['payload'].split()[1].rstrip(';'))]['name']
            assert tn.endswith(e['tag']), (e, tn)
        if e['kind'] == 'VS':
            assert e['dir'] == 'internal' and e['ctl_at'] is not None, e
    job = json.loads((out / 'prog/svc_jobs.json').read_text())['jobs'][0]
    qf = [e for e in ev if e['kind'] == 'QF']
    assert sum(len(e['words']) for e in qf) == 2 * job['q_words']
    q = [ln.split() for ln in (out / 'prog/svc/L0/qwd.hex').read_text().splitlines()]
    w5 = sorted((c, int(v, 16)) for e in qf if e['inst'] == 'u_rsv_05' for c, v, _ in e['words'])
    assert w5 == [(int(c), (int(x, 16) << 1) | 1) for c, x in q], 'QF words = the svc bench q image {d, v}'
    pv = next(e for e in ev if e['kind'] == 'PV')
    assert len(pv['words']) == 161 and pv['words'][0][0] == job['pv_first'] - 1
    assert all(int(v, 16) & 1 for _, v, _ in pv['words'][:160]) and int(pv['words'][0][1], 16) >> 513 & 1
    dn = [e for e in ev if e['kind'] == 'SVCDONE']
    assert sorted((e['inst'], e['words'][0][0] + 1) for e in dn) == sorted(job['done_pin'].items())
    for e in ev:
        if e['kind'] == 'RD':
            h = int(e['words'][0][1], 16)
            assert e['boundary'] == 'offdie' and (h >> 1) & 7 == 4 and (h >> 4) & 0x1F == 1 and h & 1
    return dict(ctl=n, row_ctl=sch['row_ctl_events'], qf_words=sum(len(e['words']) for e in qf))


def test_bk_shard():
    """S81-L20SPLIT: lower_bk shards a rank's keys over SHARD_K dies (L20 k = 6 after 0li; option D k = 3 = 87,382 a
    die), the static rank tree, and the lane-3 append words (own dense quarter + children's sparse candidates)"""
    sys.path.insert(0, str(HERE / 'layer_prog'))
    import lower_bk as B
    assert B.shard_k('L20') == 6 and B.shard_k('L2') == 3 and B.SHARD_K_RECORD_D['L20'] == 3
    assert [B.shard_range(262144, 3, j)[1] for j in range(3)] == [87382, 87382, 87380]
    assert [B.shard_range(262144, 6, j)[1] for j in range(6)] == [43691] * 5 + [43689]
    assert B.shard_tree(6) == {0: [1, 3], 1: [2], 2: [], 3: [4, 5], 4: [], 5: []}
    assert B.shard_tree(3) == {0: [1, 2], 1: [], 2: []}
    import numpy as np
    own = np.arange(100, 120) % 7 + 0x3F80          # 20 own keys at positions [1000, 1020): 2 BEAT words
    ext = [(np.array([0x4000, 0x4100]), np.array([1021, 1100]))]
    ws = B.lane3_append(own, 1000, 20, ext, 512, 0x30)
    kinds = [w >> 508 for w in ws]
    assert kinds == [B.T_HDR, B.T_BEAT, B.T_BEAT, B.T_REBASE, B.T_BEAT], kinds
    assert bits(ws[2], 256 + 15, 256) == 0b101111 and not bits(ws[2], 272, 272)   # 4 own + pos 1021 folded, not last
    assert bits(ws[2], 16 * 5 + 15, 16 * 5) == 0x4000
    assert bits(ws[3], 19, 0) == 1088 and bits(ws[4], 256 + 15, 256) == 1 << 12 and bits(ws[4], 272, 272) == 1


if __name__ == '__main__':
    test_bk_shard()
    print('test_bk_shard PASS')
    test_encoders()
    test_previous_pre_source()
    print('test_previous_pre_source PASS')
    print('test_events_g8', test_events_g8())
    test_send_cfg_b_width()
    r = test_compile_l0()
    print('TEST_DV_LAYER_COMPILE PASS', json.dumps(dict((k, v) for k, v in r.items() if k != 'smoke')))
