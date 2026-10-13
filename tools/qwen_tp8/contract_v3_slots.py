#!/usr/bin/env python3
"""Contract v3 slot revision 2026-10-13: assemble the TP8 die case that carries the tree delay tiles and check the plan.

Generator-native (tools/qwen_rom_fulldie_b3r2.py, recipe tp8b): the KV hub outline (f2 'ahub') and the reserved
regions (f2 'reserve': the 4 x 2 vector-memory envelope).  This tool is the deterministic POST-PASS on a generated
case:
  die.v         <- the tree-pad die.v (tools/qwen_tp8/frozen_tree_delay_pads.py: ot_qwen_tree_delay{N}_t added)
  place.tcl     <- + one ot_mts::place line per delay tile (origins from the pad model, existing lines untouched)
  elements.lef  <- + the delay masters: the closed view LEF where physical/ref_tile/qfd_tree_delay{N}_t/views has one,
                   else the delay2 view pin plan stretched to the kit outline (d W face, q E face, clk S; PLAN ONLY)
and the plan checks (written to --checks and printed):
  overlaps      hard slots (every non-relay instance, delay tiles included) pairwise, hard slot vs reserved region,
                any instance pair (relays included); relay objects inside a reserved region are COUNTED (their chains
                cross the VM envelope and are regenerated with the VM leaves)
  reach         pin-centroid Manhattan length of every two-pin die bus stage, per class, against --reach (500 um)
  slot share    hard-slot area / die area; reserved area reported separately
usage: contract_v3_slots.py --case GEN_CASE --pads PAD_DIR --out CASE [--baseline MODEL.json] [--checks OUT.json]
"""
import argparse
import collections
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELAY = re.compile(r'^q[fk]d_rly')   # as tools/hier_contract/derive_tp8.py: everything else is a contract slot
DELAY = re.compile(r'^ot_qwen_tree_delay(\d+)_t$')
ABUT = {'stack_local', 'phy_dfi', 'd2d_fdi', 'hbm_cdc', 'cdc_core', 'tap', 'constant'}   # abutted / band buses (kv_die.ABUT)
NONDATA = {'clock_trunk', 'reset'}


def macro_text(lef, name):
    m = re.search(r'^MACRO %s\b.*?^END %s\s*$' % (re.escape(name), re.escape(name)), lef, re.S | re.M)
    return m.group(0) if m else None


def stretch(text, src, dst, w0, w1, h):
    """the delay2 view pin plan on another outline: shapes right of the middle move by w1 - w0, spanning shapes stretch"""
    dw = w1 - w0

    def rect(m):
        x0, y0, x1, y1 = (float(q) for q in m.groups())
        if x0 > w0 / 2:
            x0 += dw
        if x1 > w0 / 2:
            x1 += dw
        return 'RECT %.4f %.4f %.4f %.4f' % (x0, y0, x1, y1)
    t = text.replace(src, dst)
    t = re.sub(r'SIZE [\d.]+ BY [\d.]+', 'SIZE %.4f BY %.4f' % (w1, h), t)
    return re.sub(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)', rect, t)


def overlaps(rects, eps=1e-3):
    """sweep: [(name, x0, y0, x1, y1, tag)] -> overlapping pairs"""
    rs = sorted(rects, key=lambda r: r[1])
    out = []
    active = []
    for r in rs:
        active = [q for q in active if q[3] > r[1] + eps]
        for q in active:
            if q[2] < r[4] - eps and r[2] < q[4] - eps:
                out.append((q, r))
        active.append(r)
    return out


def reach(model, lim):
    P = model['endpoint_pos']
    cls = collections.defaultdict(lambda: dict(stages=0, over=0, over_bits=0, max_um=0.0))
    over = []
    for b, cl, w, eps in model['buses']:
        if len(eps) != 2:
            continue
        pts = [P.get(e[0] + '.' + e[1]) for e in eps]
        if None in pts:
            cls[cl].setdefault('no_position', 0)
            cls[cl]['no_position'] += 1
            continue
        d = abs(pts[0][0] - pts[1][0]) + abs(pts[0][1] - pts[1][1])
        c = cls[cl]
        c['stages'] += 1
        c['max_um'] = round(max(c['max_um'], d), 1)
        if d > lim + 1e-6:
            c['over'] += 1
            c['over_bits'] += w
            over.append([round(d, 1), b, cl, w])
    return dict(cls), sorted(over, reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True)
    ap.add_argument('--pads', required=True, help='frozen_tree_delay_pads.py output dir (die.v, physical_model.json)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--views', default=str(ROOT / 'physical/ref_tile'))
    ap.add_argument('--recipe', default='tp8b')
    ap.add_argument('--reach', type=float, default=500.0)
    ap.add_argument('--baseline', help='physical model of the previous plan: its over-reach stages are listed as pre-existing')
    ap.add_argument('--checks')
    a = ap.parse_args()
    case, pads, out, views = Path(a.case), Path(a.pads), Path(a.out), Path(a.views)
    sys.path.insert(0, str(ROOT / 'tools'))
    import die_top_lint as D
    f2 = D.QWEN_RECIPES[a.recipe]['tp8']['f2']
    reserve = [dict(r) for r in f2.get('reserve', [])]
    if out.resolve() != case.resolve():
        out.mkdir(parents=True, exist_ok=True)
        for f in case.iterdir():
            if f.is_file():
                shutil.copy2(f, out / f.name)
    model = json.load(open(pads / 'physical_model.json'))
    insts = model['insts']
    placed = dict(re.findall(r'findInst (\w+)\] ([\d.]+ [\d.]+ \w+)', (case / 'place.tcl').read_text()))
    delay = [i for i in insts if DELAY.match(i['m'])]
    moved = [i['n'] for i in insts if i['n'] in placed and
             max(abs(i['x'] - float(placed[i['n']].split()[0])), abs(i['y'] - float(placed[i['n']].split()[1]))) > 1e-3]
    assert not moved, ('pad model moved generated instances', moved[:5])
    assert all(i['n'] not in placed and i['orient'] == 'R0' for i in delay)
    assert {i['n'] for i in insts} - set(placed) == {i['n'] for i in delay}
    # die.v / place.tcl
    shutil.copy2(pads / 'die.v', out / 'die.v')
    pl = (case / 'place.tcl').read_text().rstrip('\n') + '\n'
    pl += ''.join('ot_mts::place [$_blk findInst %s] %.3f %.3f R0\n' % (i['n'], i['x'], i['y']) for i in delay)
    (out / 'place.tcl').write_text(pl)
    # elements.lef: the delay masters
    lef = (case / 'elements.lef').read_text()
    ref = (views / 'qfd_tree_delay2_t/views/ot_qwen_tree_delay2_t/ot_qwen_tree_delay2_t.lef').read_text()
    ref_m = macro_text(ref, 'ot_qwen_tree_delay2_t')
    masters = {}
    add = []
    for mname in sorted({i['m'] for i in delay}, key=lambda q: int(DELAY.match(q).group(1))):
        n = DELAY.match(mname).group(1)
        kit = views / f'qfd_tree_delay{n}_t'
        spec = json.load(open(kit / 'spec.json'))
        w, h = spec['outline']['w'], spec['outline']['h']
        vl = kit / 'views' / mname / f'{mname}.lef'
        if vl.exists():
            txt = macro_text(vl.read_text(), mname)
            src = str(vl.relative_to(ROOT)) if ROOT in vl.parents else str(vl)
            status = 'closed view'
        else:
            txt = stretch(ref_m, 'ot_qwen_tree_delay2_t', mname, 17.28, w, h)
            src = f'kit outline {kit.name}/spec.json + delay2 view pin plan stretched (no closed view: PLAN ONLY)'
            status = 'kit outline (in the closure loop)'
        z = re.search(r'SIZE ([\d.]+) BY ([\d.]+)', txt)
        lw, lh = float(z.group(1)), float(z.group(2))
        assert abs(lw - w) < 1e-3 and abs(lh - h) < 1e-3, (mname, lw, lh, w, h)
        bad = [i['n'] for i in delay if i['m'] == mname and (abs(i['w'] - w) > 1e-3 or abs(i['h'] - h) > 1e-3)]
        assert not bad, ('pad model outline differs from the kit', mname, bad[:3])
        assert macro_text(lef, mname) is None, mname
        add.append(txt)
        masters[mname] = dict(outline_um=[w, h], lef=src, status=status, kit=f'physical/ref_tile/{kit.name}',
                              instances=sum(1 for i in delay if i['m'] == mname))
    body = lef.rstrip()
    tail = ''
    if body.endswith('END LIBRARY'):
        body, tail = body[:-len('END LIBRARY')].rstrip(), '\nEND LIBRARY'
    (out / 'elements.lef').write_text(body + '\n\n' + '\n\n'.join(add) + tail + '\n')
    # ---- checks
    dz = re.search(r'-die_area \{0 0 ([\d.]+) ([\d.]+)\}', (case / 'run.tcl').read_text())
    dw, dh = float(dz.group(1)), float(dz.group(2))
    R = [(i['n'], i['x'], i['y'], i['x'] + i['w'], i['y'] + i['h'], 'relay' if RELAY.match(i['m']) else 'slot') for i in insts]
    hard = [r for r in R if r[5] == 'slot']
    res = [(r['name'], *r['rect'], 'reserved') for r in reserve]
    ov_hard = overlaps(hard)
    ov_res = [(q, r) for q, r in overlaps(hard + res) if 'reserved' in (q[5], r[5])]
    ov_all = overlaps(R)
    outside = [r[0] for r in R + res if r[1] < -1e-3 or r[2] < -1e-3 or r[3] > dw + 1e-3 or r[4] > dh + 1e-3]
    rly_in = {r['name']: sum(1 for q in R if q[5] == 'relay' and q[1] < r['rect'][2] and r['rect'][0] < q[3]
                             and q[2] < r['rect'][3] and r['rect'][1] < q[4]) for r in reserve}
    cls, over = reach(model, a.reach)
    base_over = None
    if a.baseline:
        _, bo = reach(json.load(open(a.baseline)), a.reach)
        base_over = {o[1] for o in bo}
    data = {c: v for c, v in cls.items() if c not in NONDATA}
    relayed = {c: v for c, v in data.items() if c.split('@')[0] not in ABUT}
    slot_mm2 = sum((r[3] - r[1]) * (r[4] - r[2]) for r in hard) / 1e6
    res_mm2 = sum((r['rect'][2] - r['rect'][0]) * (r['rect'][3] - r['rect'][1]) for r in reserve) / 1e6
    rec = dict(
        case=str(out), recipe=a.recipe, die_um=[dw, dh], die_mm2=round(dw * dh / 1e6, 3),
        generator_native=['qkd_ahub outline (f2 ahub)', 'reserved regions (f2 reserve)'],
        post_pass=['tree delay tiles: die.v, place.tcl, elements.lef masters'],
        delay_masters=masters, delay_tiles=len(delay), delay_mm2=round(sum(i['w'] * i['h'] for i in delay) / 1e6, 4),
        reserved=[dict(r, mm2=round((r['rect'][2] - r['rect'][0]) * (r['rect'][3] - r['rect'][1]) / 1e6, 4),
                       relay_objects_inside=rly_in[r['name']]) for r in reserve],
        instances=len(insts), hard_slots=len(hard), relays=len(R) - len(hard),
        overlaps=dict(hard_slot_pairs=len(ov_hard), hard_slot_vs_reserved=len(ov_res), any_instance_pairs=len(ov_all),
                      outside_die=len(outside),
                      examples=[[q[0], r[0]] for q, r in (ov_hard + ov_res + ov_all)[:8]]),
        reach=dict(limit_um=a.reach, by_class=cls,
                   data_stages_over=sum(v['over'] for v in data.values()),
                   relayed_data_stages_over=sum(v['over'] for v in relayed.values()),
                   max_relayed_data_um=max((v['max_um'] for v in relayed.values()), default=0.0),
                   over_new_vs_baseline=(sorted(o for o in over if o[1] not in base_over and o[2] not in NONDATA)[:40]
                                         if base_over is not None else None),
                   over_count_baseline=(len(base_over) if base_over is not None else None),
                   worst=over[:12],
                   note='pin-centroid Manhattan length per two-pin stage; clock_trunk / reset are tree nets (CTS / reset '
                        'tree), abutted classes (%s) compare bus-pin centroids of abutted faces' % ', '.join(sorted(ABUT))),
        slot_share=round(slot_mm2 / (dw * dh / 1e6), 4), slot_mm2=round(slot_mm2, 3), reserved_mm2=round(res_mm2, 3),
        slot_plus_reserved_share=round((slot_mm2 + res_mm2) / (dw * dh / 1e6), 4))
    rec['pass'] = dict(overlaps=not (ov_hard or ov_res or ov_all or outside),
                       reach=rec['reach']['relayed_data_stages_over'] == 0)
    if a.checks:
        Path(a.checks).write_text(json.dumps(rec, indent=1) + '\n')
    (out / 'SLOT_REV.json').write_text(json.dumps(dict(reserved=rec['reserved'], delay_masters=masters), indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('die_um', 'hard_slots', 'relays', 'delay_tiles', 'overlaps', 'slot_share',
                                         'slot_plus_reserved_share', 'pass')}))
    print(json.dumps({c: [v['stages'], v['over'], v['max_um']] for c, v in sorted(cls.items())}))


if __name__ == '__main__':
    main()
