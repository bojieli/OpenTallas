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
    rc = run(['gen', '--die-v', str(die), '--prog', str(prog), '--cut', str(VT / 'cut3S_g1'), '--out', str(o)])
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
        ok(rc == 2 and st['verdict_kind'] == 'STALE' and len(st['stale']['link_age_diffs']) == 14,
           'L0 programme compiled on bind9 is STALE on bind_p4l3_g123 (14 lane ages)')


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


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for f in (real_die, witnesses, synthetic):
            d = tmp / f.__name__
            d.mkdir()
            f(d)
    print('test_dv_cut_replay:', 'ALL PASS' if all(OK) else f'{OK.count(False)} FAIL')
    return 0 if all(OK) else 1


if __name__ == '__main__':
    sys.exit(main())
