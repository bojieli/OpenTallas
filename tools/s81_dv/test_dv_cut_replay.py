#!/usr/bin/env python3
"""test_dv_cut_replay.py -- self-test of tools/s81_dv/dv_cut_replay.py (LB2-S81/REPLAY, 10-18).  No simulation.

  1 real die build: the G1 cut_3S vehicle (bind9_g1 die.v + slice_bench/prog_L0_s3S) gives the SAME replay as the
    proven dv_slice_replay.py (input timelines equal, out.txt byte-identical); lane ages come from the build's stations
    and .k straps (bind_p4l3_g123: xrW_0S_l0 = ceil(7/2) + 4 + 1 = 9) and the L0 programme compiled on bind9 is STALE
    there (gen refuses, exit 2)
  2 the committed fleet witnesses (Verilator 5.050, G1 build): lane-age diagnostic PASSES the trace check; the shifted
    and the corrupted boundary word FAIL; the schedule run FAILS on the G8 bundle tear
  3 synthetic two-cut die: schedule-fed input == trace-fed input (compose); compose PASSES on the producer's real
    output and FAILS on a shifted one; shift / corrupt mutants change the replayed word; an unscheduled extra word on a
    strict replay FAILS the check
  4 event words (LB2-S81/EVENTS): out-event streams (valid bit, masked data) checked at edge + age, consumer cuts driven
    with the full words, in-event words, producer gaps -> unencoded, offdie / internal events apart, class mutants
  6 entry lowering (TOKj 10-23): line CTL rows derive the column-4 V rung beat; KS job start forwarded to u_eng.f_ks;
    S81-P10 10-24: f_ks producer model (start pulse + held payload, bundle launch)
"""
import json
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import dv_cut_replay as R  # noqa: E402

SB = ROOT / 'results/rtl/s81_layer_tput_1018/slice_bench'
VT = SB / 'replay_tool'
OK = []


def ok(cond, what):
    print(('PASS ' if cond else 'FAIL ') + what)
    OK.append(bool(cond))


def timeline(p):
    d = defaultdict(dict)
    for ln in Path(p).read_text().splitlines():
        c, i, v = ln.split()
        d[int(i)][float(c)] = int(v, 16)       # the bench applies events in file order: the last one of a cycle wins
    out = {}
    for i, ch in d.items():
        cur, r = 0, []
        for c in sorted(ch):
            if ch[c] != cur:
                r.append((c, ch[c]))
                cur = ch[c]
        if r:
            out[i] = r
    return out


def run(args):
    return R.main(args)


def real_die(tmp):
    die = ROOT / 'results/arch/s81_dv_1016/bind9_g1/die.v.gz'
    prog = SB / 'prog_L0_s3S'
    if not die.exists():
        print('SKIP real-die tests (bind9_g1 not checked out)')
        return
    o = tmp / 'new'
    # TOK-S81-GAPS/INT 10-19: prog_L0_s3S predates the frame-internal landing model (x_frame lanes land in the receiver
    # frame, lk strap; dv_layer_compile + DieBuild agree): its 8 cut-internal frame lanes read STALE, none is a cut boundary
    rc = run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(VT / 'cut3S_g1'), '--out', str(o), '--allow-stale'])
    ok(rc == 0, 'gen on the G1 cut_3S vehicle')
    old = tmp / 'old'
    dv = tmp / 'die.v'
    dv.write_text(R.read_text(die))
    subprocess.run([sys.executable, str(HERE / 'dv_slice_replay.py'), '--prog', str(prog), '--ports',
                    str(VT / 'cut3S_g1/tb_ports.json'), '--die-v', str(dv), '--slice', 'u_s_3S', '--out', str(old)],
                   check=True, capture_output=True)
    ok(timeline(o / 'in.txt') == timeline(old / 'in.txt'), 'input timelines == dv_slice_replay (proven on cut_3S)')
    ok((o / 'out.txt').read_text() == (old / 'out.txt').read_text(), 'out.txt byte-identical to dv_slice_replay')
    rp = json.loads((o / 'replay.json').read_text())
    ok(rp['in_words'][0]['src_sid'] == 8 and rp['in_words'][0]['hops'] == 4, 'beat src = injector u_s_4S sid 8, hops 4')
    die3 = ROOT / 'results/arch/s81_dv_1016/bind_p4l3_g123/die.v.gz'
    if die3.exists():
        D = R.DieBuild(die3)
        L = D.links['xrW_0S_l0']
        ok(L['age'] == 9 and L['K'] == 4 and L['stations'] == 7, 'bind_p4l3_g123 xrW_0S_l0 age 9 from 7 stations + k 4')
        ok(D.links['xrW_2S_l3']['age'] == 10 and D.links['xrW_2S_l0']['age'] == 9, 'G8 bundle: xrW_2S l3 age 10, l0 age 9')
        rc = run(['gen', '--die-v', str(die3), '--prog', str(ROOT / 'results/rtl/s81_layer_tput_1018/compiler/prog_L0_s0S'),
                  '--cut', str(VT / 'cut3S_g1'), '--out', str(tmp / 'stale')])
        st = json.loads((tmp / 'stale/replay.json').read_text())
        # 14 relay/landing lane ages + 8 x_frame lanes that land inside the receiving frame (lk strap; INT 10-19)
        nfr = sum(1 for d in st['stale']['link_age_diffs'] if D.links[d['link']].get('internal_landing'))
        ok(rc == 2 and st['verdict_kind'] == 'STALE' and len(st['stale']['link_age_diffs']) == 22 and nfr == 8,
           'L0 programme compiled on bind9 is STALE on bind_p4l3_g123 (14 lane ages + 8 frame-internal landings)')


def witnesses(tmp):
    for m, want in (('w_lane', 0), ('w_mshift', 1), ('w_mcorrupt', 1), ('w_sched', 1)):
        rd, rn = VT / 'replay' / m, VT / 'runs' / m
        if not rn.exists():
            print(f'SKIP witness {m}')
            continue
        c = tmp / f'check_{m}.json'
        rc = run(['check', '--replay', str(rd), '--run', str(rn), '--out', str(c)])
        ok(rc == want, f'fleet witness {m}: check {"PASS" if want == 0 else "FAIL"} as expected')


# ------------------------------------------------------------------------------------------------ synthetic two-cut die
DIE = """module dv_die (ck, rst_n);
  input wire ck;
  input wire rst_n;
  wire [39:0] w_jb_src, w_jb_dst;
  wire [39:0] w_jb_lnd;
  wire [39:0] r_jb_0;
  unit_a u_a (.ck(ck), .rst_n(rst_n), .s_j({w_jb_src[32:0]}));
  dsfd_dvrlyh_40_NS st_jb_0 (.i(w_jb_src), .o(r_jb_0), .ck(ck), .ck_o(ck), .rs(rst_n));
  dsfd_dvrlyh_40_NS st_jb_1 (.i(r_jb_0), .o(w_jb_dst), .ck(ck), .ck_o(ck), .rs(rst_n));
  dsfd_dvland_40 ld_jb (.ck_f(ck), .i(w_jb_dst), .ck(ck), .rs(rst_n), .k(3'd2), .o(w_jb_lnd), .fault());
  unit_b u_b (.ck(ck), .rst_n(rst_n), .j({w_jb_lnd[32:0]}));
endmodule
"""


def mkcut(d, insts, ports):
    d.mkdir(parents=True)
    tb = [dict(index=i, port=n, dir=p['dir'], kind='boundary', width=40, lo=0, bits=[[39, 0]])
          for i, (n, p) in enumerate(ports.items())]
    (d / 'tb_ports.json').write_text(json.dumps(tb))
    (d / 'slice_ports.json').write_text(json.dumps(dict(ports={n: dict(p, width=40, lo=0) for n, p in ports.items()})))
    (d / 'slice_insts.json').write_text(json.dumps(dict(how={i: 'set' for i in insts})))


def synthetic(tmp):
    die = tmp / 'die.v'
    die.write_text(DIE)
    D = R.DieBuild(die)
    ok(D.links['jb']['age'] == 4 and D.links['jb']['src'] == [('u_a', 's_j')], 'synthetic lane age ceil(2/2) + 2 + 1 = 4')
    prog = tmp / 'prog'
    (prog / 'prog').mkdir(parents=True)
    ev = [dict(cycle=50, inst='u_b', port='j', dir='in', kind='SVCJ', tag='job0', payload='100040100'),
          dict(cycle=53, inst='u_b', port='j', dir='in', kind='SVCJ', tag='job1', payload='000000123')]
    (prog / 'schedule.json').write_text(json.dumps(dict(layer='T', events=ev, links={'jb': dict(age_edges=4)})))
    (prog / 'prog/ctl_templates.json').write_text(json.dumps(dict(templates=[])))
    A, B = tmp / 'cutA', tmp / 'cutB'
    mkcut(A, ['u_a', 'st_jb_0', 'st_jb_1', 'ld_jb'], {'o__w_jb_lnd': dict(dir='output', net='w_jb_lnd', peers=['u_b'])})
    mkcut(B, ['u_b', 'st_jb_0', 'st_jb_1', 'ld_jb'], {'i__w_jb_src': dict(dir='input', net='w_jb_src', peers=['u_a'])})
    # cut B is the consumer with the lane relays (the cutter grows fan-in): drive the producer register
    rB = tmp / 'rB'
    ok(run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(B), '--out', str(rB), '--t0', '10']) == 0,
       'synthetic gen (consumer cut)')
    ok(timeline(rB / 'in.txt') == {0: [(57.0, 0x100040100), (58.0, 0), (60.0, 0x123), (61.0, 0)]},
       'consumer input: word at landed - age + 1 + t0, 1-cycle pulse')
    # cut A is the producer: check the landed word at the scheduled cycle (A must not hold the relays for this)
    shutil.rmtree(A)
    mkcut(A, ['u_a'], {'o__w_jb_lnd': dict(dir='output', net='w_jb_lnd', peers=['u_b'])})
    rA = tmp / 'rA'
    ok(run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(A), '--out', str(rA), '--t0', '10']) == 0,
       'synthetic gen (producer cut)')
    ok((rA / 'out.txt').read_text() == '60 0 1ffffffff 100040100\n63 0 1ffffffff 123\n',
       'producer checks: landed word at event cycle + t0, j bits only')
    runA = tmp / 'runA'
    runA.mkdir()
    (runA / 'trace.txt').write_text('60 0 100040100\n61 0 0\n63 0 123\n64 0 0\n')
    (runA / 'status').write_text('TB_DV_SLICE PASS\n')
    ok(run(['check', '--replay', str(rA), '--run', str(runA)]) == 0, 'trace check PASS on the scheduled words')
    rp = json.loads((rA / 'replay.json').read_text())
    ok(rp['partial'] is False, 'synthetic replay is not partial (every boundary event encoded)')
    runX = tmp / 'runX'
    runX.mkdir()
    (runX / 'trace.txt').write_text('60 0 100040100\n61 0 0\n63 0 123\n64 0 0\n70 0 5\n71 0 0\n')
    (runX / 'status').write_text('TB_DV_SLICE PASS\n')
    ok(run(['check', '--replay', str(rA), '--run', str(runX)]) == 1, 'an unscheduled extra word FAILS the strict check')
    # compose: B fed from A's trace == B fed from the schedule; compose PASS / FAIL
    rBt = tmp / 'rBt'
    ok(run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(B), '--out', str(rBt), '--t0', '10',
            '--trace', f'{rA}={runA}']) == 0, 'gen with a trace-fed lane')
    ok(timeline(rBt / 'in.txt') == timeline(rB / 'in.txt'), 'trace-fed input == schedule-fed input')
    ok(json.loads((rBt / 'replay.json').read_text())['boundary'][0]['source'] == 'trace', 'boundary source = trace')
    runB = tmp / 'runB'
    runB.mkdir()
    (runB / 'trace.txt').write_text('')
    ok(run(['compose', '--cut', f'A={rA}:{runA}', '--cut', f'B={rB}:{runB}', '--out', str(tmp / 'c.json')]) == 0,
       'compose PASS: producer trace == consumer replay')
    runS = tmp / 'runS'
    runS.mkdir()
    (runS / 'trace.txt').write_text('61 0 100040100\n62 0 0\n63 0 123\n64 0 0\n')
    ok(run(['compose', '--cut', f'A={rA}:{runS}', '--cut', f'B={rB}:{runB}', '--out', str(tmp / 'c2.json')]) == 1,
       'compose FAILS when the producer word is one cycle late')
    for mu, want in (('shift:jb:1', {0: [(58.0, 0x100040100), (59.0, 0), (61.0, 0x123), (62.0, 0)]}),
                     ('corrupt:jb:0', {0: [(57.0, 0x100040101), (58.0, 0), (60.0, 0x123), (61.0, 0)]})):
        rm = tmp / ('m_' + mu.replace(':', '_'))
        run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(B), '--out', str(rm), '--t0', '10',
             '--mutant', mu])
        ok(timeline(rm / 'in.txt') == want and json.loads((rm / 'replay.json').read_text())['verdict_kind'] == 'MUTANT',
           f'mutant {mu} changes exactly the targeted word')


# ------------------------------------------------------------------------------------------------ event words (EVENTS)
DIE2 = """module dv_die2 (ck, rst_n);
  input wire ck;
  input wire rst_n;
  wire [9:0] w_pq_src, w_pq_dst;
  wire [9:0] w_pq_lnd;
  wire [9:0] r_pq_0;
  wire [9:0] w_qq_src, w_qq_dst;
  wire [9:0] w_qq_lnd;
  unit_p u_p (.ck(ck), .rst_n(rst_n), .o_v({w_pq_src[0:0]}), .o_d({w_pq_src[8:1]}), .so({w_qq_src[7:0]}));
  dsfd_dvrlyh_10_NS st_pq_0 (.i(w_pq_src), .o(r_pq_0), .ck(ck), .ck_o(ck), .rs(rst_n));
  dsfd_dvrlyh_10_NS st_pq_1 (.i(r_pq_0), .o(w_pq_dst), .ck(ck), .ck_o(ck), .rs(rst_n));
  dsfd_dvland_10 ld_pq (.ck_f(ck), .i(w_pq_dst), .ck(ck), .rs(rst_n), .k(3'd1), .o(w_pq_lnd), .fault());
  dsfd_dvrlyh_10_NS st_qq_0 (.i(w_qq_src), .o(w_qq_dst), .ck(ck), .ck_o(ck), .rs(rst_n));
  dsfd_dvland_10 ld_qq (.ck_f(ck), .i(w_qq_dst), .ck(ck), .rs(rst_n), .k(3'd2), .o(w_qq_lnd), .fault());
  unit_c u_c (.ck(ck), .rst_n(rst_n), .bi({w_pq_lnd[8:0]}), .q({1'b0, w_qq_lnd[7:0]}));
endmodule
"""


def mkcut2(d, insts, ports):
    d.mkdir(parents=True)
    tb = [dict(index=i, port=n, dir=p['dir'], kind='boundary', width=10, lo=0, bits=[[9, 0]])
          for i, (n, p) in enumerate(ports.items())]
    (d / 'tb_ports.json').write_text(json.dumps(tb))
    (d / 'slice_ports.json').write_text(json.dumps(dict(ports={n: dict(p, width=10, lo=0) for n, p in ports.items()})))
    (d / 'slice_insts.json').write_text(json.dumps(dict(how={i: 'set' for i in insts})))


def events(tmp):
    """LB2-S81/EVENTS: words-carrying events (out PV-like stream with a valid bit and masked data, in QF-like words, a
    pulse), offdie / internal events, producer gaps, the class mutants"""
    die = tmp / 'die.v'
    die.write_text(DIE2)
    D = R.DieBuild(die)
    ok(D.links['pq']['age'] == 3 and D.links['qq']['age'] == 4, 'event die: pq age 1 + 1 + 1 = 3, qq age 1 + 2 + 1 = 4')
    prog = tmp / 'prog'
    (prog / 'prog').mkdir(parents=True)
    # PV-like: producer u_p {o_d 8, o_v}: two valid words at producer edges 40, 41 (data nibble masked), then v low
    pv = dict(cycle=41, inst='u_p', port='o_v / o_d', ports=['o_v', 'o_d'], dir='out', kind='PV', tag='pv',
              payload='2 words', valid_bit=0, words=[[40, f'{(0x5A << 1) | 1:x}', '1f'], [41, f'{(0xA5 << 1) | 1:x}', '1f'],
                                                     [42, '0', '1']])
    qf = dict(cycle=60, inst='u_c', port='q', ports=['q'], dir='in', kind='QF', tag='qf', payload='2 words',
              words=[[60, '3c', 'ff'], [61, 'c3', 'ff']], producer_gap='producer send programme not compiled')
    rd = dict(cycle=70, inst='u_p', port='(outward)', dir='out', kind='RD', tag='rd', payload='x', boundary='offdie',
              words=[[70, '9', 'f']])
    vs = dict(cycle=20, inst='u_c.leaf0.vs', port='s_d', dir='internal', kind='VS', tag='vs', payload='x', issue=20,
              carried_by='template 0', ctl_at=29)
    vs2 = dict(vs, tag='vs2', ctl_at=None)
    S = dict(layer='T', events=[pv, qf, rd, vs], links={'pq': dict(age_edges=3), 'qq': dict(age_edges=4)})
    (prog / 'schedule.json').write_text(json.dumps(S))
    (prog / 'prog/ctl_templates.json').write_text(json.dumps(dict(templates=[])))
    P, Cc = tmp / 'cutP', tmp / 'cutC'
    mkcut2(P, ['u_p'], {'o__w_pq_lnd': dict(dir='output', net='w_pq_lnd', peers=['u_c']),
                        'o__w_qq_lnd': dict(dir='output', net='w_qq_lnd', peers=['u_c'])})
    mkcut2(Cc, ['u_c'], {'i__w_pq_src': dict(dir='input', net='w_pq_src', peers=['u_p']),
                         'i__w_qq_src': dict(dir='input', net='w_qq_src', peers=['u_p'])})
    rP = tmp / 'rP'
    ok(run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(P), '--out', str(rP), '--t0', '10']) == 0,
       'event gen (producer cut)')
    rp = json.loads((rP / 'replay.json').read_text())
    # out words land at producer edge + age 3 + t0 10; mask 1f = v + low nibble of o_d (lane bits 1..4)
    ok((rP / 'out.txt').read_text() == '53 0 1f 15\n54 0 1f b\n55 0 1 0\n',
       'out-event words checked at edge + bundle age + t0 under the mask')
    ok(rp['by_kind'].get('QF', {}).get('unencoded') == 1 and rp['partial'] is True,
       'producer cut: QF with a producer gap is UNENCODED (partial), never checked')
    ok(rp['by_kind']['RD'] == {'offdie': 1} and rp['by_kind']['VS'] == {'internal': 1},
       'offdie RD and internal VS are listed apart')
    ok(next(b for b in rp['boundary'] if b['port'] == 'o__w_pq_lnd')['valid_ref'] == dict(port='o__w_pq_lnd', bit=0),
       'valid bit of the PV-like bundle recorded for the strict check')
    run_ = tmp / 'runP'
    run_.mkdir()
    (run_ / 'status').write_text('TB_DV_SLICE PASS\n')
    # trace: the words (+ data bits the mask leaves out), stale data while v = 0 (not an extra), then a valid extra
    (run_ / 'trace.txt').write_text('53 0 1f5\n54 0 14b\n55 0 140\n60 0 1e0\n')
    ok(run(['check', '--replay', str(rP), '--run', str(run_), '--out', str(tmp / 'cP.json')]) == 0 and
       json.loads((tmp / 'cP.json').read_text())['ports'][0]['missed'] == [] and
       json.loads((tmp / 'cP.json').read_text())['ports'][0]['n_unscheduled'] == 0,
       'masked data + stale bits while v = 0 pass; the producer-gap QF lane is unchecked')
    (run_ / 'trace.txt').write_text('53 0 1f5\n54 0 14b\n55 0 140\n60 0 141\n61 0 0\n')
    ok(run(['check', '--replay', str(rP), '--run', str(run_), '--out', str(tmp / 'cP2.json')]) == 1 and
       json.loads((tmp / 'cP2.json').read_text())['ports'][0]['n_unscheduled'] == 1,
       'a valid word at an unscheduled cycle is an extra (the PV lane stays strict in a partial replay)')
    ok([b['strict'] for b in rp['boundary']] == [True, False], 'the producer-gap lane is not strict, the PV lane is')
    # consumer cut: the out-event words drive the producer register at edge + 1 + t0 with the FULL value
    rC = tmp / 'rC'
    ok(run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(Cc), '--out', str(rC), '--t0', '10']) == 0,
       'event gen (consumer cut)')
    tl = timeline(rC / 'in.txt')
    ok(tl.get(0) == [(51.0, 0xB5), (52.0, 0x14B), (53.0, 0)], 'consumer cut driven with the full PV-like words at edge + 1 + t0')
    ok(tl.get(1) == [(67.0, 0x3C), (68.0, 0xC3), (69.0, 0)], 'in-event QF words driven at landed - age + 1 + t0')
    rc = json.loads((rC / 'replay.json').read_text())
    ok(rc['partial'] is False and rc['by_kind']['QF'] == {'in_words': 2}, 'consumer cut: every event encoded (not partial)')
    # internal VS without its CTL arrival -> unencoded
    S2 = dict(S, events=[pv, vs2])
    (prog / 'schedule.json').write_text(json.dumps(S2))
    r2 = tmp / 'r2'
    run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(Cc), '--out', str(r2), '--t0', '10'])
    ok(json.loads((r2 / 'replay.json').read_text())['by_kind']['VS'] == {'unencoded': 1},
       'an internal VS event with no CTL arrival (ctl_at) is UNENCODED')
    (prog / 'schedule.json').write_text(json.dumps(S))
    # class mutants
    rm = tmp / 'mq'
    run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(Cc), '--out', str(rm), '--t0', '10',
         '--mutant', 'shift-kind:QF:2'])
    ok(timeline(rm / 'in.txt').get(1) == [(69.0, 0x3C), (70.0, 0xC3), (71.0, 0)] and
       timeline(rm / 'in.txt').get(0) == tl.get(0), 'mutant shift-kind:QF:2 moves only the QF words')
    re_ = tmp / 'mpv'
    run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(P), '--out', str(re_), '--t0', '10',
         '--mutant', 'expect-shift:PV:1'])
    (run_ / 'trace.txt').write_text('53 0 1f5\n54 0 14b\n55 0 140\n')
    ok((re_ / 'out.txt').read_text() == '54 0 1f 15\n55 0 1f b\n56 0 1 0\n' and
       run(['check', '--replay', str(re_), '--run', str(run_), '--out', str(tmp / 'cm.json')]) == 1,
       'mutant expect-shift:PV:1 moves the PV checks one cycle: the real trace FAILS it')


def seqhost_reset(tmp):
    """5 (TOK-S81-GAPS/CTL): u_seqhost live = idle t_host alive landed cycle - lane age - 1; --host-boot before it is refused"""
    class D:
        links = {'ht_7N': dict(age=59, out_net='w_ht_7N_lnd', src_bits=[('w_ht_7N_src', i) for i in range(131)])}
        def port_bits(self, inst, port):
            return [('w_ht_7N_src', i) for i in range(77)]
    class C:
        out_by_net = {'w_ht_7N_lnd': dict(index=210, port='o__w_ht_7N_lnd', lo=0)}
    (tmp / 'trace.txt').write_text('12 17 0\n140 210 %x\n224 210 %x\n' % (1 << 76, 0x185 << 68))
    (tmp / 'prog').mkdir()
    (tmp / 'prog/host_boot.memh').write_text('23\n')
    lv = R.seqhost_live(D(), C(), tmp)
    ok(lv['live'] == 80 and lv['alive_landed'] == 140, 'seqhost_live: alive landed 140 on age 59 -> live 80')
    class A:
        idle_run = str(tmp); host_boot = 64; ks = None; ks_word = '1'; t0 = 0
    try:
        R.host_boot_words(A(), D(), tmp, {}, [], C())
        ok(False, '--host-boot 64 before live 80 must be refused')
    except SystemExit as e:
        ok('lands before u_seqhost leaves reset' in str(e), '--host-boot 64 before live 80 is refused')
    # TOKd-S81 10-23: the forward host landing goes live after the t_host alive edge lands (c14: words landing < ~139 dropped)
    A.host_boot = 120
    try:
        R.host_boot_words(A(), D(), tmp, {}, [], C())
        ok(False, '--host-boot 120 before alive landed 140 + 4 must be refused')
    except SystemExit as e:
        ok('host lane landing is live' in str(e), '--host-boot 120 before alive landed 140 + 4 is refused')
    hdr = lambda sp, seal=0: ((0x10 | (((3 << 26) | (seal << 25) | (104 << 9) | (sp << 7)) << 32)) << 1) | 1
    ok(R.calendar_start_phase([0x23, hdr(2, 1), hdr(2)]) == 2 and R.calendar_start_phase([0x23]) is None,
       'calendar_start_phase reads the begin header (not the seal word)')


def entry_lowering(tmp):
    """6 (TOKj-S81 10-23, fc30 entry): (a) a CTL row compiled at a line stop (u_s_3N.ri_e) also derives the seq_host V
    rung beat on u_s_4N.vi (w_tvN_seqhost: job17's 51 rung words were unscheduled on a strict lane); a vi row is not
    duplicated; (b) the KS job start is forwarded whole to u_eng.f_ks (HOSTB_ENABLE 0 mux) at f_ks landed + the eks
    lane age; another seqhost master encodes no forward"""
    class D:
        links = {f'xrW_{c}N': dict(age=3, src=[(f'u_s_{c + 1}N', 'ro_w')], dst=[(f'u_s_{c}N', 'ri_e')]) for c in range(7)} | \
            {f'xrE_{c}N': dict(age=3, src=[(f'u_s_{c}N', 'ro_e')], dst=[(f'u_s_{c + 1}N', 'ri_w')]) for c in range(7)}
    S = dict(events=[dict(kind='CTL', dir='in', inst='u_s_3N', port='ri_e', cycle=100, payload='template 7', tag='r0')])
    ev = R.derive_line_events(S, D())
    vi = [e for e in ev if e['port'] == 'vi']
    # line out at col 4 = 100 - (3 + RSTOP_HOP) = 95; rung beat at vi = 95 + RSTOP_HOP - inject (6, no contract) = 91
    ok(len(vi) == 1 and vi[0]['inst'] == 'u_s_4N' and vi[0]['cycle'] == 91, 'line CTL row derives the column-4 vi rung beat')
    S2 = dict(events=S['events'] + [dict(vi[0], derived_from=None)])
    ok(not [e for e in R.derive_line_events(S2, D()) if e['port'] == 'vi'], 'a compiled vi rung beat is not derived twice')
    class E:
        inst = {'u_seqhost': dict(master='dsdv_hostb_seqhost_mux', params='.HOSTB_ENABLE(0), .STATIC_KS6(0)'),
                'u_eng': dict(master='dsdv_eng_rr', params='')}
        links = {'eks_7N': dict(age=11, out_net='w_eks_7N_lnd')}
        def port_bits(self, inst, port):
            if (inst, port) == ('u_seqhost', 'engram_f_ks'):
                return [('w_eks_7N_src', i) for i in range(53)]
            if (inst, port) == ('u_eng', 'f_ks'):
                return [('w_eks_7N_lnd', i) for i in range(53)]
            return []
    w = R.ks_engram_words(E(), 0x1000082e4fffff, -5)
    ok(len(w) == 1 and w[0]['inst'] == 'u_eng' and w[0]['cycle_land'] == 6
       and sum(v << b for (n, b), v in w[0]['bits'].items()) == 0x1000082e4fffff,
       'KS job start forwarded whole to u_eng.f_ks at landed -5 + eks age 11 = 6')
    E.inst = dict(E.inst, u_seqhost=dict(master='dsdv_hostb_seqhost_mux', params='.HOSTB_ENABLE(1)'))
    ok(R.ks_engram_words(E(), 1, -5) == [], 'hostb-enabled seqhost: no KS forward encoded')
    # (c) S81-P10 10-24: f_ks producer = start pulse + HELD payload, both launched with the whole bundle (lanes 38 / 39)
    class F:
        links = {'hf_l1': dict(age=38, out_net='w_hf_l1_lnd'), 'hf_l2': dict(age=39, out_net='w_hf_l2_lnd')}
        def port_bits(self, inst, port):
            if (inst, port) == ('u_seqhost', 'f_ks'):
                return [('w_hf_l1_src', 243 + i) for i in range(33)] + [('w_hf_l2_src', i) for i in range(20)]
            return []
    keep = R.lane_of_net
    R.lane_of_net = lambda die, n: n[2:-4] if n.startswith('w_hf_') else None
    try:
        ws = R.ks_source_words(F(), 0x1000082e4fffff, 100, 104)
    finally:
        R.lane_of_net = keep
    st, pay = ws[0], ws[1:]
    ok(list(st['bits']) == [('w_hf_l2_src', 19)] and st['bits'][('w_hf_l2_src', 19)] == 1 and st['cycle_land'] == 100
       and st['bundle_age'] == 39, 'KS start: one-edge pulse of bit 52 only (lane l2), launched with the bundle age 39')
    ok([w['cycle_land'] for w in pay] == [100, 101, 102, 103] and all(w['hold'] == 100 and w['bundle_age'] == 39
       and ('w_hf_l2_src', 19) not in w['bits'] for w in pay), 'KS payload held from the start landing to the end, no start bit')
    l1 = sum(v << (b - 243) for (n, b), v in pay[0]['bits'].items() if n == 'w_hf_l1_src')
    l2 = sum(v << b for (n, b), v in pay[0]['bits'].items() if n == 'w_hf_l2_src')
    ok(l1 | (l2 << 33) == 0x1000082e4fffff & ((1 << 52) - 1), 'held payload = f_ks[51:0] (l1[275:243] + l2[18:0])')


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for f in (real_die, witnesses, synthetic, events, seqhost_reset, entry_lowering):
            d = tmp / f.__name__
            d.mkdir()
            f(d)
    print('test_dv_cut_replay:', 'ALL PASS' if all(OK) else f'{OK.count(False)} FAIL')
    return 0 if all(OK) else 1


if __name__ == '__main__':
    sys.exit(main())
