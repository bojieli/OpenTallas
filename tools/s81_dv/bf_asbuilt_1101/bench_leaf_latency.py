#!/usr/bin/env python3
"""bench_leaf_latency.py -- S81-FRAME-FIX-1 11-11: a prepared as-built BF bench must return every leaf (BF and q) at
the date its frame schedule composes (frame_return_plan.leaf_path), else every measured BF record is off by the seam
stages the bench lacks (11-11: plain s81b_fint seams under a --bound-plan schedule, u_s01 -9 / u_s12 -4).

Two independent checks:
 1. structural, every leaf: the bench's frame wrapper (the exact file its static.f compiles) is elaborated with Yosys
    (band partitions as port-only black boxes from the bench's plan kit) and each seam is walked flop by flop from the
    partition output that drives it to the partition input it lands on: the bench seam depth.  The extractor's own
    tracer (frame_schedule_asb.measure + schedule, on the schedule's elaborated as-built frame and validation
    measurements in --work) is rerun at THOSE depths, and every leaf's leaf_path must equal the schedule's.
 2. run, BF leaves: in each `xs_bf.py measure` record of the bench (--measure JSON), the leaf's measured return
    latency (its row's ret edge - its partial edge) must equal leaf_path on the schedule's topology.

  bench_leaf_latency.py --bench RUN --schedule SCHED.json --work FSA_WORK --source-root ROOT [--measure M.json ...]
      [--out OUT.json]    -> exit 0 PASS / 1 FAIL
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools/s81_dv'), str(ROOT / 'tools/s81_dv/layer_prog'), str(ROOT / 'tools/die_plan')]
YOSYS = os.environ.get('OT_YOSYS') or str(Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys')


def module_text(text, name):
    m = re.search(r'^\s*(?:\(\*[^\n]*\*\)\s*)?module\s+' + re.escape(name) + r'\b.*?^\s*endmodule\b', text, re.M | re.S)
    return m and m[0]


def bench_files(bench):
    return [ln for ln in (Path(bench) / 'static.f').read_text().splitlines() if ln and not ln.startswith('+')]


def bench_seam_depths(bench, master, variant, yosys=YOSYS):
    """{u_s<ij>: flops from the driving partition output to the landing partition input} in the bench's own wrapper"""
    top = f'{master}_l4_lp_{variant}'
    files = bench_files(bench)
    wrap = [f for f in files if module_text(Path(f).read_text(), top)]
    if len(wrap) != 1:
        raise ValueError(f'bench compiles {len(wrap)} definitions of {top}')
    wtext = Path(wrap[0]).read_text()
    parts = sorted(set(re.findall(r'\b(' + master + r'_l4_lp_r\d\w*)\s+#', module_text(wtext, top))))
    kit = [f for f in files if all(module_text(Path(f).read_text(), p) for p in parts)]
    if len(kit) != 1:
        raise ValueError('bench plan kit defining the band partitions not unique: ' + str(kit))
    ktext = Path(kit[0]).read_text()
    stubs = []
    for p in parts:
        body = module_text(ktext, p)
        head = body[:body.index(');') + 2]
        stubs.append('(* blackbox *)\n' + head.strip() + '\nendmodule\n')
    need = ['s81b_fint', 'ot_dp_st']
    defs = []
    for n in need:
        src = [f for f in files if module_text(Path(f).read_text(), n)]
        if n == 's81b_fint' and not src:
            raise ValueError('bench has no s81b_fint')
        if src:
            defs.append(module_text(Path(src[-1]).read_text(), n))
    with tempfile.TemporaryDirectory() as td:
        sv = Path(td) / 'w.sv'
        sv.write_text('\n'.join(stubs + defs + [module_text(wtext, top)]) + '\n')
        js = Path(td) / 'w.json'
        subprocess.run([yosys, '-q', '-p', f'read_verilog -sv {sv}; hierarchy -top {top}; setattr -mod -unset keep_hierarchy; proc; flatten; opt_clean; '
                        f'write_json {js}'], check=True, capture_output=True)
        mod = json.loads(js.read_text())['modules'][top]
    dff = {}
    part_in, part_out = {}, {}
    for cn, c in mod['cells'].items():
        if c['type'] in ('$dff', '$adff', '$sdff'):
            for d, q in zip(c['connections']['D'], c['connections']['Q']):
                dff[d] = q
        elif c['type'].lstrip('\\') in parts or module_of(c['type']) in parts:
            for port, bits in c['connections'].items():
                tgt = part_in if c['port_directions'][port] == 'input' else part_out
                for b in bits:
                    if isinstance(b, int):
                        tgt[b] = (cn, port)
    depths = {}
    for seam in sorted(set(re.findall(r'\bs81b_fint\s*#\([^)]*\)\)\s*(u_s\d\d)\b', module_text(wtext, top)))):
        d = mod['netnames'].get(f'{seam}.d')
        if d is None:
            raise ValueError(f'{seam}.d net missing after flatten')
        per = set()
        for b in d['bits']:
            if not isinstance(b, int) or b not in part_out:
                continue
            n, x = 0, b
            while x in dff:
                x, n = dff[x], n + 1
            if x not in part_in:
                continue          # a seam bit no partition reads (unused frame_int spare)
            per.add(n)
        if len(per) != 1:
            raise ValueError(f'{seam}: bench depth not uniform over the bus {sorted(per)}')
        depths[seam] = per.pop()
    return depths


def module_of(t):
    t = t.lstrip('\\')
    if t.startswith('$paramod'):
        t = t.split('\\')[1] if '\\' in t else t
    return t


def traced_topology(sched, work, master, variant, source_root, seam_depths):
    """the extractor's topology of the as-built frame at these seam depths (its own measure + schedule)"""
    import frame_schedule_asb as F
    F.SROOT[0] = Path(source_root).resolve()
    F.SRC[0] = F.SROOT[0]
    top, lp_top = f'{master}_l4_lp_asb_{variant}', f'{master}_l4_lp'
    extra = {k: d - 2 for k, d in seam_depths.items() if d > 2}
    if any(d < 2 for d in seam_depths.values()):
        raise ValueError(f'bench seam shallower than the as-built 2 flops {seam_depths}')
    F.BOUND_EXTRA.clear()
    F.BOUND_EXTRA.update({k: d - 2 for k, d in (sched.get('bound_plan') or {}).get('seam_depths', {}).items() if d > 2})
    work = Path(work)
    meas_ab = F.measure(json.loads((work / f'{top}.selected.json').read_text()), top, extra or None)
    meas_v = json.loads((work / f'validate_{lp_top}.meas.json').read_text())
    meas_t = json.loads((work / f'{lp_top}.meas.json').read_text())
    lp_sched = json.loads((F.sroot() / F.LP_SCHED.format(m=master)).read_text())
    plan_map = json.loads((F.sroot() / F.PLAN_MAP.format(m=master)).read_text())
    s, _, _, _ = F.schedule(meas_v, meas_t, meas_ab, lp_sched, plan_map, master, variant, sched['source_sha256'])
    return s['topology']


def leaves(topo):
    return sorted({d[s] for d in topo['nodes'].values() for s in 'ab'} - set(topo['nodes'])
                  - {d[s] for d in topo['nodes'].values() for s in 'ab' if d[s].startswith('zero.')})


def run_leaf_check(stopo, records, name=''):
    """xs_bf measure records -> (rows, fails): each measured leaf return latency vs leaf_path on the schedule topology"""
    import frame_return_plan as P
    rows, fails = [], []
    for key, rec in sorted(records.items()):
        for lf, v in sorted(rec.get('ret_lat', {}).items()):
            want = P.leaf_path(stopo, lf)[0]
            rows.append(dict(record=key, file=name, leaf=lf, run=v, schedule=want))
            if v != want:
                fails.append(f'run {key} leaf {lf}: measured return {v} != schedule leaf_path {want}')
    return rows, fails


def check(bench, schedule, work, source_root, measures=(), yosys=YOSYS):
    import frame_return_plan as P
    man = json.loads((Path(bench) / 'manifest.json').read_text())
    sched = json.loads(Path(schedule).read_text())
    master, variant = man['master'], man['variant']
    if sched['source_sha256'] != man['source_sha256']:
        raise ValueError('bench was prepared from another schedule')
    want_seams = (sched.get('bound_plan') or {}).get('seam_depths')
    seams = bench_seam_depths(bench, master, variant, yosys)
    stopo = sched['topology']
    btopo = traced_topology(sched, work, master, variant.split('_')[-1], source_root, seams)
    rows, fails = [], []
    for lf in leaves(stopo):
        s_, b_ = P.leaf_path(stopo, lf), P.leaf_path(btopo, lf)
        row = dict(leaf=lf, kind='bf' if lf.endswith('.r') else 'q', schedule=s_[0], bench=b_[0],
                   path=s_[1])
        rows.append(row)
        if s_ != b_:
            fails.append(f'leaf {lf}: bench return {b_[0]} != schedule leaf_path {s_[0]}')
    seam_fail = [] if want_seams is None else [f'seam {k}: bench {seams.get(k)} != schedule bound plan {d}'
                                               for k, d in want_seams.items() if seams.get(k, 2) != d]
    run_rows = []
    for mp in measures:
        rr, rf = run_leaf_check(stopo, json.loads(Path(mp).read_text()), str(mp))
        run_rows += rr
        fails += rf
    fails = seam_fail + fails
    return dict(schema='opentallas.s81.bf_bench_leaf_latency.v1', bench=str(bench), schedule=str(schedule),
                master=master, variant=variant, bench_seam_depths=seams, schedule_seam_depths=want_seams,
                leaves=rows, leaves_checked=len(rows), run_leaves=run_rows, verdict='FAIL' if fails else 'PASS',
                fails=fails)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bench', required=True)
    ap.add_argument('--schedule', required=True)
    ap.add_argument('--work', required=True, help='frame_schedule_asb.py work dir of that schedule (selected.json, meas)')
    ap.add_argument('--source-root', required=True)
    ap.add_argument('--measure', action='append', default=[])
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    r = check(a.bench, a.schedule, a.work, a.source_root, a.measure)
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    print('BF_BENCH_LEAF_LATENCY', r['verdict'], r['master'], r['variant'], 'seams', r['bench_seam_depths'],
          'leaves', r['leaves_checked'], 'run_leaves', len(r['run_leaves']))
    for f in r['fails']:
        print('  FAIL', f)
    return 0 if r['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
