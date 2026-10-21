#!/usr/bin/env python3
"""S81-ROMOPT-B (10-20): EXACT per-stage ROM / cfg capacity check of the p4l(-MU) release die, by the ACTUAL allocator.

What a die of a stage holds (rank quarter, TP4): the dense ops of the layer(s) whose attention it serves (a_proj, wq_b,
idx.q, eng.wkv, wo_b, shared gu / down on the q pairs; wo_a, router, cmp.wk on the BF pairs) and N resident routed
experts (gate ++ up and down rows).  Every resident expert has its own ROM rows and its own cfg phases (the cfg words
carry the ROM base), so a frame programme = dense phases + N x (phases of one expert).

The check runs xs_place.compile_frame -- the real image writer (v41_die_images_w17w10.add_phase: PP even phase start,
segment_order words, ROM depth assert) under the release flags -- on EVERY one of the 122 physical frames with the N
experts of the stage really placed (FixN: N synthetic expert identities, each bound to the shapes / rows of a real
fixture expert; ROM fill does not depend on the values).  Phases are placed with the identity segment->pair
assignment (iters 0).  Where a phase's segments differ in length (wq_b, idx.q, shared down: one 8-word tail segment)
the legaliser's permutation can move the long segment, so the gate uses a legaliser-independent UPPER bound (every
used pair charged the phase's longest segment); routed-expert phases have equal segments (exact either way).

Physical limits (verified):
  q / BF pair ROM depth 8,192 paired addresses: ot_v41_rom_elem_w10 13-bit w_ptr, one ot_rom_8192x274_m8 a macro
    (PP: 2 x ot_rom_4096x274_m8), NB 2 macros a pair; I.Field(depth=8192)
  cfg7 programme 1,024 phases a frame: xs_place.write_images (7 banks x 4,096 rows, 4 rows a phase)
  spine phase ROM 4,096 words (2 a phase -> 2,048 phases), stream ROM 16,384 words after dedup (xs_calendar_pack)
  calendar ROM 4,096 rows (paired ot_rom_4096x72_m8): per-token schedule; measured L0 1,868 / L2-class 2,006 rows
    (results/rtl/s81_rom12_codex_1020, CAL_SEGMENT) -- independent of N; a stage touching two layers is charged both.

Gate: every q pair AND every BF pair of every frame < 100 % (fill < 8,192), cfg phases <= 1,024, calendar <= 4,096.

    xs_capacity.py run   --spec SPEC.json --fixtures-root D --die-src S --out DIR [--jobs 32] [--frames F ...]
    xs_capacity.py bound --out bound.json      # structural per-expert floor (no compile)
    xs_capacity.py verdict --map MAP.json      # compile-time refusal (CompileFault) used by xs_place
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent))
ROOT = HERE.parents[2]

DEPTH = 8192
CFG7_PHASES = 1024
PHASE_ROM_PHASES = 2048
STREAM_WORDS = 16384
CAL_ROWS = 4096
LAYER_CAL_ROWS = {'L0': 1868, 'L2': 2006}          # measured (CAL_SEGMENT, ROM12 b82da5c37); L2 class = idx layers
KV_SRC, IDX_SRC, ENGRAM = (2, 8, 14, 20), (2, 8, 14, 20, 24, 28, 32, 36), (1, 14)
RELEASE_ENV = dict(OT_XS_QPAIRS='12', OT_XS_GU_MERGE='1', OT_XS_TOPO='1', OT_XS_PROP='1', OT_XS_CAL_SEGMENT='1',
                   OT_XS_APROJ_TOPO='1')
# DRIVE-S81-IDX4 (10-20, LEAD10-S81 stage pick): the release map is the 140-stage pinned map on the 122-frame die
# (dv_plan --idxrd 4 keeps 122 frames / 1130 ROM slots; mu7i4b strict bind PASS); qualified with OT_XS_PAIR_ROTATE=0.
# The 97-stage map stays at stage_map.json (pass OT_XS_STAGE_MAP to use it).
MAP_DEFAULT = ROOT / 'results/arch/s81_romopt_1020/b/stage_map_f122_140.json'


class CompileFault(RuntimeError):
    """the stage map does not fit the die: the compile refuses (never a runtime stall)"""


def layer_ops(L):
    """xs_place op lists of real layer L (order as xs_place.XS_OPS / BF_OPS) and the fixture class with its shapes"""
    xs = (['eng.wkv'] if L in ENGRAM else []) + ['attn.wq_b'] + (['attn.idx.q'] if L in IDX_SRC else []) + \
         ['attn.wo_b', 'ffn.shared_gu', 'ffn.experts_gu', 'ffn.down']
    bf = (['attn.cmp.wk'] if L in KV_SRC else []) + ['attn.wo_a', 'ffn.router']
    fix = 'L14' if L in ENGRAM else 'L20' if L == 20 else 'L2' if L in IDX_SRC else 'L0'
    cal = LAYER_CAL_ROWS['L2' if L in IDX_SRC or L in ENGRAM else 'L0']
    return xs, bf, fix, cal


def spec_ops(spec):
    if spec.get('dense_layer') is None:
        return ['ffn.experts_gu', 'ffn.down'], [], 'L0'
    xs, bf, fix, _ = layer_ops(spec['dense_layer'])
    return xs, bf, fix


# ------------------------------------------------------------------------------------------------ actual allocator
def _fixn(XP, d, n):
    class FixN(XP.Fix):
        """the fixture with N synthetic routed experts (ids 100000 + k), each bound to real expert k mod 6's rows"""

        def __init__(self, d_):
            super().__init__(d_)
            real = [int(e) for e in self.meta['experts']]
            ids = [100000 + k for k in range(n)]
            self.map = {i: real[k % len(real)] for k, i in enumerate(ids)}
            self.meta = dict(self.meta, experts=ids)

        def _m(self, name):
            m = re.match(r'^exp(\d+)\.(.*)$', name)
            if m and int(m.group(1)) in self.map:
                return f'exp{self.map[int(m.group(1))]}.{m.group(2)}'
            m = re.match(r'^ffn\.experts\.(\d+)\.(.*)$', name)
            if m and int(m.group(1)) in self.map:
                return f'ffn.experts.{self.map[int(m.group(1))]}.{m.group(2)}'
            return name

        @functools.lru_cache(maxsize=None)
        def arr(self, rel):
            return super().arr(rel)

        def w(self, name):
            return super().w(self._m(name))

        def sc(self, name):
            return super().sc(self._m(name))

        def op(self, name):
            return super().op(self._m(name))
    return FixN


def virtual_depth(vd):
    """measurement mode (OT_XS_CAP_VDEPTH): the same image writer with the ROM depth bound raised to vd, so an overfull
    stage reports its real fill instead of stopping at the first ROM depth assert.  Allocation never reads the depth
    (LPT on fill), so every placement is the physical one; the gate still compares with DEPTH = 8,192.  The physical
    writer's own refusal is the control run without this mode."""
    import inspect
    import v41_die_images_w17w10 as I
    if getattr(I, '_xs_cap_vdepth', None) == vd:
        return
    src = inspect.getsource(I.add_phase)
    assert src.count('<= 8192') == 1, 'image writer PP depth bound moved'
    exec(compile(src.replace('<= 8192', '<= field.depth'), I.__file__, 'exec'), I.__dict__)
    init = I.Field.__init__

    def f_init(self, *a, **k):
        init(self, *a, **k)
        self.depth = vd
    I.Field.__init__ = f_init
    I._xs_cap_vdepth = vd


def frame_alloc(die, frame, fixd, spec):
    """the actual xs_place frame field of this stage on one frame: per-slot fill, cfg phases, layout facts"""
    import lower_xs as LX
    if os.environ.get('OT_XS_CAP_VDEPTH'):
        virtual_depth(int(os.environ['OT_XS_CAP_VDEPTH']))
    import v41_rom_ksplit_bankmap as S
    import xs_place as XP
    xs, bf, _ = spec_ops(spec)
    n = int(spec['experts'])
    orig = (XP.Fix, XP.op_groups, LX.placement)
    XP.Fix = _fixn(XP, fixd, n)
    shared = spec.get('dense_layer') is not None

    def og(fx, op):
        g = orig[1](fx, op)
        return g if shared or op != 'ffn.down' else [x for x in g if x.get('expert') != 'shared']

    def pl(die_, sl, fx=None):
        g, p = orig[2](die_, sl, fx)
        return g, ([dict(r, rows=[]) for r in p] if spec.get('dense_layer') is None else p)
    XP.op_groups, LX.placement = og, pl
    try:
        rec, field = XP.compile_frame(die, frame, fixd, xs + bf, iters=0, only=set())
    finally:
        XP.Fix, XP.op_groups, LX.placement = orig
    nq = len(rec['pairs'])
    nbf = len(rec['slots']) - nq
    ub = [0] * len(rec['slots'])
    layout = {}
    for ph in rec['phases']:
        if ph.get('fmt') == 'bf16' or ph['op'] == 'attn.a_proj':
            continue
        plan = ph['plan']
        lens = [len(S.segment_order(ph['fmt'], a0, el)) for a0, el in S.segments(ph['K'], ph['nseg'])]
        for slot, _R, _sg in plan['assign_slots']:
            ub[slot] += max(lens)
        if ph['op'] in ('ffn.experts_gu', 'ffn.down') and ph['mat'].startswith('exp'):
            e = ph['mat'].split('.')[0]
            layout.setdefault(e, []).append((ph['op'], ph['chunk'], tuple(sorted(s for s, _, _ in plan['assign_slots']))))
    act = [int(v) for v in field.fill]
    # a_proj / BF increments = actual fill minus the q-phase identity fill of the other phases
    idf = [0] * len(act)
    for ph in rec['phases']:
        if ph.get('fmt') == 'bf16' or ph['op'] == 'attn.a_proj':
            continue
        lens = [len(S.segment_order(ph['fmt'], a0, el)) for a0, el in S.segments(ph['K'], ph['nseg'])]
        for slot, _R, sg in ph['plan']['assign_slots']:
            idf[slot] += lens[sg]
    rest = [a - b for a, b in zip(act, idf)]
    assert all(r >= 0 for r in rest), ('fill accounting', frame, rest)
    ubf = [u + r for u, r in zip(ub, rest)]
    lay = list(layout.values())
    streams = {}
    for ph in field.phases:
        streams.setdefault(tuple(field.stream[ph['sbase']:ph['sbase'] + ph['nbeat']]), ph['nbeat'])
    return dict(frame=frame, master=rec['master'], slice=rec['slice'], slice_index=rec['slice_index'],
                frame_index=rec['frame_index'], q_slots=nq, bf_slots=nbf,
                q_fill=act[:nq], q_fill_ub=ubf[:nq], bf_fill=act[nq:], nphases=rec['nphases'],
                expert_phases=(len(lay[0]) if lay else 0), layout_identical=all(x == lay[0] for x in lay) if lay else None,
                layout_variants=len({tuple(x) for x in lay}), stream_dedup_words=sum(streams.values()))


def frame_signature(die, frame, fixd, spec):
    """everything the allocator reads that differs between frames: the frame master, its BF pair count, a_proj rows
    and the row count of every die-wide phase on this frame (op, group, chunk).  Frames with equal signatures get
    the same slot-space fill (checked: --dedup compiles a second member of every class and asserts equality)."""
    import frame_bench as FB
    import lower_xs as LX
    import xs_place as XP
    import xs_topo as TP
    xs, bf, _ = spec_ops(spec)
    FixN = _fixn(XP, fixd, int(spec['experts']))
    fx = FixN(fixd)
    sl, g, j = XP.frame_slot(die, frame)
    master = die.inst[frame]['master']
    q, bfp = FB.frame_pairs(LX.base_master(master))
    p0 = [] if spec.get('dense_layer') is None else LX.placement(die, sl, LX.load_fixture(fixd))[1][j]['rows']
    rows = []
    shared = spec.get('dense_layer') is not None
    for op, gi, c, nseg, R in XP.phase_list(fx, [o for o in xs]):
        grp = XP.op_groups(fx, op)[gi]
        if not shared and grp.get('expert') == 'shared':
            continue
        rows.append((op, gi, c, len(TP.chunk(grp, grp['groups'][g][j], c, R))))
    import xs_bf as XB
    for op, gi, c, s_, n, R, most in XP.bf_phase_list(fx, bf, XB.BF_PAIRS_DIE):
        rows.append((op, gi, c, s_, len(XB.bf_groups(fx, op)[gi]['groups'][g][j][c * R:(c + 1) * R])))
    return json.dumps([LX.base_master(master), die.strap(frame, 'lk'), len(q), len(bfp), len(p0), rows])


def _sig(args):
    die_src, fixroot, spec, frame, env = args
    os.environ.update(env)
    _, _, fix = spec_ops(spec)
    return frame, frame_signature(_die(die_src), frame, str(Path(fixroot) / fix), spec)


def _worker(args):
    die_src, fixroot, spec, frame, env = args
    os.environ.update(env)
    import dv_layer_compile as C
    die = _die(die_src)
    _, _, fix = spec_ops(spec)
    t0 = time.time()
    try:
        r = frame_alloc(die, frame, str(Path(fixroot) / fix), spec)
    except AssertionError as e:      # the image writer's own ROM depth / element capacity assert = an overfull frame
        r = dict(frame=frame, fault=repr(e)[:400])
    r['seconds'] = round(time.time() - t0, 1)
    return r


@functools.lru_cache(maxsize=None)
def _die(die_src):
    import dv_layer_compile as C
    return C.Die(C.die_tree(src=die_src))


def summarise(spec, rows):
    q = [max(r['q_fill_ub']) for r in rows if 'q_fill_ub' in r]
    qe = [max(r['q_fill']) for r in rows if 'q_fill' in r]
    bf = [max(r['bf_fill'] or [0]) for r in rows if 'bf_fill' in r]
    nph = [r['nphases'] for r in rows if 'nphases' in r]
    faults = [r for r in rows if 'fault' in r]
    worst = max((r for r in rows if 'q_fill_ub' in r), key=lambda r: max(r['q_fill_ub']), default=None)
    cal = spec.get('calendar_rows', 0)
    s = dict(id=spec['id'], vdepth=os.environ.get('OT_XS_CAP_VDEPTH'), experts=spec['experts'], dense_layer=spec.get('dense_layer'), frames=len(rows),
             faults=len(faults), first_fault=faults[0] if faults else None,
             q_max_fill=max(q) if q else None, q_max_fill_identity=max(qe) if qe else None,
             q_fill_pct=round(100 * max(q) / DEPTH, 2) if q else None,
             q_margin_words=DEPTH - max(q) if q else None, worst_frame=worst and worst['frame'],
             bf_max_fill=max(bf) if bf else None, bf_fill_pct=round(100 * max(bf) / DEPTH, 2) if bf else None,
             cfg7_phases=max(nph) if nph else None, cfg7_margin=CFG7_PHASES - max(nph) if nph else None,
             stream_dedup_words=max((r['stream_dedup_words'] for r in rows if 'stream_dedup_words' in r), default=None),
             calendar_rows=cal, calendar_margin=CAL_ROWS - cal,
             expert_phases=max((r['expert_phases'] for r in rows if 'expert_phases' in r), default=0),
             layout_identical_all=all(r.get('layout_identical') in (True, None) for r in rows))
    s['pass'] = (not faults and q and max(q) < DEPTH and (not bf or max(bf) < DEPTH) and max(nph) <= CFG7_PHASES
                 and cal <= CAL_ROWS and s['stream_dedup_words'] <= STREAM_WORDS)
    return s


def cmd_run(a):
    from multiprocessing import Pool
    specs = json.loads(Path(a.spec).read_text())
    specs = specs if isinstance(specs, list) else [specs]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    env = {k: os.environ[k] for k in os.environ if k.startswith('OT_XS_')}
    die = _die(a.die_src)
    frames = a.frames or [f for sl in sorted(die.slices()) for f in die.frames_of(sl)]
    srcs = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / 'tools/s81_dv/layer_prog').glob('xs_*.py')) + [ROOT / 'tools/s81_dv/layer_prog/lower_xs.py',
                                                                                  ROOT / 'tools/v41_die_images_w17w10.py']}
    allsum = []
    rc = 0
    with Pool(a.jobs) as pool:
        for spec in specs:
            t0 = time.time()
            if a.dedup:
                sig = dict(pool.map(_sig, [(a.die_src, a.fixtures_root, spec, f, env) for f in frames], chunksize=1))
                cls = {}
                for f in frames:
                    cls.setdefault(sig[f], []).append(f)
                reps = [m[0] for m in cls.values()] + [m[-1] for m in cls.values() if len(m) > 1]
                got = {r['frame']: r for r in pool.map(_worker, [(a.die_src, a.fixtures_root, spec, f, env) for f in reps],
                                                       chunksize=1)}
                key = ('q_fill', 'q_fill_ub', 'bf_fill', 'nphases', 'fault')
                for m in cls.values():      # the dedup claim, checked: first and last member of every class agree
                    assert all(got[m[0]].get(k) == got[m[-1]].get(k) for k in key), ('signature class differs', m[0], m[-1])
                rows = [dict(got[m[0]], frame=f, represented_by=m[0], class_size=len(m)) if f not in got else got[f]
                        for m in cls.values() for f in m]
                print('XS_CAP_DEDUP', spec['id'], 'frames', len(frames), 'classes', len(cls), 'compiled', len(reps), flush=True)
            else:
                rows = pool.map(_worker, [(a.die_src, a.fixtures_root, spec, f, env) for f in frames], chunksize=1)
            s = summarise(spec, rows)
            s['seconds'] = round(time.time() - t0, 1)
            (out / f'{spec["id"]}.frames.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
            allsum.append(s)
            rc |= 0 if s['pass'] else 1
            print('XS_CAP', json.dumps(s), flush=True)
    (out / 'summary.json').write_text(json.dumps(dict(schema='opentallas.s81_dv.xs_capacity.v1', env=env, depth=DEPTH,
                                                      cfg7=CFG7_PHASES, cal_rows=CAL_ROWS, sources=srcs, specs=allsum),
                                                 indent=1) + '\n')
    print('XS_CAP_DONE', 'PASS' if rc == 0 else 'FAIL', flush=True)
    return rc if a.expect is None else (0 if (rc == 0) == (a.expect == 'pass') else 3)


# ------------------------------------------------------------------------------------------------ structural floor
def expert_floor(q_pairs=1464):
    """per-expert paired addresses on a die and the smallest possible worst-pair share when every resident expert of a
    stage has ONE layout (static schedule: a routed slot's return calendar is fixed, so an expert's chunk c uses the
    same pairs whoever is routed)"""
    import v41_rom_ksplit_bankmap as S
    gu = 1152 // 2 * sum(len(S.segment_order('fp4', a0, el)) for a0, el in S.segments(5120, 5))
    dn = 1280 // 2 * sum(len(S.segment_order('fp4', a0, el)) for a0, el in S.segments(2304, 5))
    raw = (1152 * 5120 + 1280 * 2304) * 4 // 256 // 2
    gran = math.gcd(*[len(S.segment_order('fp4', a0, el)) for K in (5120, 2304) for a0, el in S.segments(K, 5)])
    avg = (gu + dn) / q_pairs
    hot = gran * math.ceil(avg / gran)
    return dict(gu_paired=gu, down_paired=dn, total_paired=gu + dn, raw_paired=raw, q_pairs=q_pairs,
                avg_per_pair=round(avg, 3), granularity=gran, worst_pair_floor=hot,
                max_experts_per_stage_no_dense=DEPTH // hot,
                rule='pair fills are multiples of the segment granularity; sum over pairs = total, so some pair >= '
                     'granularity x ceil(avg / granularity) per expert; identical layouts make it N x that')


def cmd_bound(a):
    r = expert_floor()
    Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    print(json.dumps(r))
    return 0


# ------------------------------------------------------------------------------------------------ compile-time check
def enabled():
    """release default: on whenever the release ROM layout (12 q pairs) is compiled; OT_XS_CAPCHECK=0 opts out
    (component benches of one token's 6 experts only, never a die/stage image)"""
    import xs_flags as XO   # S81-ROMOPT merge: the release default is 12 q pairs with the env unset (xs_flags)
    return os.environ.get('OT_XS_CAPCHECK', '1') == '1' and XO.get('OT_XS_QPAIRS') == '12'


def verdict(map_path=None, stage=None):
    """CompileFault unless the committed stage map's exact capacity check PASSES (for `stage`, or every stage)"""
    p = Path(map_path or os.environ.get('OT_XS_STAGE_MAP', MAP_DEFAULT))
    if not p.exists():
        raise CompileFault(f'no committed stage map / capacity verdict at {p}')
    m = json.loads(p.read_text())
    st = [s for s in m['stages'] if stage is None or s['stage'] == stage]
    if not st:
        raise CompileFault(f'stage {stage} not in {p}')
    unchecked = [s for s in st if 'capacity' not in s]
    if unchecked:
        raise CompileFault(f'stage map {p.name} ({m.get("plan")}): {len(unchecked)} of {len(st)} stages have no exact '
                           f'xs_capacity verdict (run it and xs_stage_map.py merge)')
    bad = [s for s in st if not s['capacity'].get('pass')]
    if bad:
        w = max(bad, key=lambda s: s.get('capacity', {}).get('q_fill_pct') or 1e9)
        raise CompileFault(f'stage map {p.name} ({m.get("plan")}) overfills {len(bad)} of {len(st)} stages; worst '
                           f'{w["stage"]}: q {w.get("capacity", {}).get("q_fill_pct")} % / cfg7 '
                           f'{w.get("capacity", {}).get("cfg7_phases")} phases (limits 100 %, {CFG7_PHASES})')
    return True


def cmd_verdict(a):
    try:
        verdict(a.map, a.stage)
    except CompileFault as e:
        print('XS_CAPCHECK FAULT', e)
        return 1
    print('XS_CAPCHECK PASS')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest='cmd', required=True)
    r = sp.add_parser('run')
    r.add_argument('--spec', required=True)
    r.add_argument('--fixtures-root', required=True)
    r.add_argument('--die-src', required=True)
    r.add_argument('--out', required=True)
    r.add_argument('--jobs', type=int, default=32)
    r.add_argument('--frames', nargs='*')
    r.add_argument('--expect', choices=['pass', 'fail'])
    r.add_argument('--dedup', action='store_true', help='compile one member (+ a check member) per frame signature class')
    b = sp.add_parser('bound')
    b.add_argument('--out', required=True)
    v = sp.add_parser('verdict')
    v.add_argument('--map')
    v.add_argument('--stage')
    a = p.parse_args(argv)
    return dict(run=cmd_run, bound=cmd_bound, verdict=cmd_verdict)[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
