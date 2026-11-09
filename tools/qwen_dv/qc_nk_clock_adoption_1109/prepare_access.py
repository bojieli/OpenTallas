#!/usr/bin/env python3
"""DIE-QC-97 11-09: NK clock-pin access LEF + per-instance clock_entry_access + plan event patch.

Same form as the NL event (tools/qwen_dv/qc_nl_clock_adoption_1551/prepare_access.py, commit b1bd879f675), with the
NK stack MEASURED on the signed NK routed DB (native_roi.json: every net incl. PG/fill/inst/blockage shapes on V4..M9
around the ck pin, tools/qwen_dv/qc_nk_clock_adoption_1109/native_roi.py).  Never edits the signed view, its pins or
its DB: it reads the abstract LEF + the plan pin table and writes a NEW output directory.

Entry stack (child frame, chosen on the PARENT tracks for both R0 and MY at track_offset (0, 0.012)):
  VIA56 (228.984, 578.772) on the real M5 pin, M6 bar y 578.772, VIA67 + M7 utility pin x 229.024.
  The pin centre x 228.972 is not a parent M5 track and the parent M7 track over it (228.960) is taken by the
  foreign NK M7 net15753 (228.928..228.960); the parent M6 tracks through the pin centre (578.836 / 578.900) are
  within 32 nm of / on the foreign NK M6 net48959 (578.880..578.912).  578.772 / 229.024 is the nearest clear pair.
OBS windows = footprint + 64 nm per side, pulled back so every foreign shape keeps >= 32 nm from the window where
the footprint-to-foreign gap allows it (gap >= 64), and never below the 32 nm footprint guard."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('lef_clock_entry', ROOT / 'tools/die_plan/lef_clock_entry.py')
G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)

MASTER = 'qfd_tile_nk_a0c'
SIZE = (457.92, 1157.76)
PIN_RECT = (228.948, 578.640, 228.996, 579.120)
PIN_CENTRE = (228.972, 578.880)
OLD_PIN = ('M4', 457.824, 668.076)
VIA56 = (228.984, 578.772)
VIA67 = (229.024, 578.772)
# via enclosures (um) as measured on the native NK VIA56 / VIA67 instances (asserted against native_roi.json)
ENC = {'VIA56': {'M5': (0.024, 0.054), 'M6': (0.046, 0.032)}, 'VIA67': {'M6': (0.054, 0.032), 'M7': (0.032, 0.054)}}
M7_PIN_LEN = 0.768        # gen_phys 4 * PIN_LEN_UM: the emitted utility pin height (validate_access entry_box)
GUARD, SPACE = 0.064, 0.032
# parent (type-frame) tracks, tools/die_plan/schema.ASAP7_LAYERS
TRACK = {'M5': (0.024, 0.048), 'M6': (0.032, 0.064), 'M7': (0.032, 0.064)}
SIGNOFF = dict(tt=733.25, ff=586.0, n=2584,
               source='epyc6:/srv/opentallas-scratch2/claude/dq97/nk_eco2_resign_fc/signoff/signoff.json '
                      'corners.{tt,ff}.insertion_pinflops.mean (n 2584, ff_vclk_reference pin_flop_mean 733.249323 / '
                      '585.995565; identical in the original i1/signoff/signoff.json)')
NEW_PINS = 'cores/a0_nk_pins_ck1109.json'
r6 = lambda v: round(v + 0.0, 6)


def box(c, wh):
    return (r6(c[0] - wh[0] / 2), r6(c[1] - wh[1] / 2), r6(c[0] + wh[0] / 2), r6(c[1] + wh[1] / 2))


def union(*bs):
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


M5_VIA = box(VIA56, ENC['VIA56']['M5'])
# M5: VIA56 bottom enclosure plus an M5 patch on the same parent M5 track up to the pin centre (inside the real pin
# metal): check.py proves the pin-layer track by a footprint that contains the pin centre.
FP_CHILD = {5: [(M5_VIA[0], M5_VIA[1], M5_VIA[2], r6(PIN_CENTRE[1] + 0.024))],
            6: [union(box(VIA56, ENC['VIA56']['M6']), box(VIA67, ENC['VIA67']['M6']))],
            7: [(r6(VIA67[0] - 0.016), r6(PIN_CENTRE[1] - M7_PIN_LEN / 2), r6(VIA67[0] + 0.016),
                 r6(PIN_CENTRE[1] + M7_PIN_LEN / 2))]}


def gap(a, b):
    """separation of two boxes per axis (dx, dy), 0 on an overlapping axis; negative never."""
    return (max(a[0] - b[2], b[0] - a[2], 0.0), max(a[1] - b[3], b[1] - a[3], 0.0))


def overlaps(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) >= -1e-9 and min(a[3], b[3]) - max(a[1], b[1]) >= -1e-9


def derive_windows(roi):
    """per layer: window, foreign/native shapes within 0.5 um, tight sides."""
    s = roi['shapes']
    um = lambda b: tuple(v / 1000 for v in b)
    # measured via enclosures must equal the constants
    for v, layers in ENC.items():
        seen = {(sh['layer'], tuple(round(x, 3) for x in (um(sh['bbox'])[2] - um(sh['bbox'])[0],
                                                          um(sh['bbox'])[3] - um(sh['bbox'])[1])))
                for sh in s if sh.get('via') == v and sh.get('net') == 'ck'}
        for ln, wh in layers.items():
            if (ln, tuple(round(x, 3) for x in wh)) not in seen:
                raise ValueError(f'native {v} {ln} enclosure differs from {wh}: {sorted(seen)}')
    out, report = {}, {}
    for L in (6, 7):
        fp = FP_CHILD[L][0]
        foreign = [(um(sh['bbox']), sh) for sh in s if sh['layer'] == f'M{L}' and sh.get('net') != 'ck']
        native_ck = [(um(sh['bbox']), sh) for sh in s if sh['layer'] == f'M{L}' and sh.get('net') == 'ck'
                     and sh['kind'] != 'bterm']
        w = [fp[0] - GUARD, fp[1] - GUARD, fp[2] + GUARD, fp[3] + GUARD]
        tight = []
        for b, sh in foreign + native_ck:
            if overlaps(b, fp):
                raise ValueError(f'M{L} footprint overlaps native {sh}')
            dx, dy = gap(b, fp)
            # the side that faces the shape is the separating axis with the larger gap
            if dx >= dy:
                side, g = (0, fp[0] - b[2]) if b[2] <= fp[0] + 1e-9 else (2, b[0] - fp[2])
            else:
                side, g = (1, fp[1] - b[3]) if b[3] <= fp[1] + 1e-9 else (3, b[1] - fp[3])
            # only shapes that would be inside / within SPACE of the 64-nm window matter
            lim = [w[0] - SPACE, w[1] - SPACE, w[2] + SPACE, w[3] + SPACE]
            if not overlaps(b, lim):
                continue
            pull = max(SPACE, min(GUARD, g - SPACE))
            new = fp[side] - pull if side < 2 else fp[side] + pull
            w[side] = max(w[side], new) if side < 2 else min(w[side], new)
        w = tuple(r6(v) for v in w)
        near = []
        for b, sh in foreign + native_ck:
            if overlaps(b, w):
                raise ValueError(f'M{L} window {w} exposes native shape {sh}')
            dx, dy = gap(b, w)
            fx, fy = gap(b, fp)
            if max(fx, fy) <= 0.5:
                near.append(dict(net=sh.get('net'), kind=sh['kind'], bbox_um=list(b), gap_to_window_nm=round(max(dx, dy) * 1000),
                                 gap_to_footprint_nm=round(max(fx, fy) * 1000)))
            if max(dx, dy) < SPACE - 1e-9 and sh.get('net') != 'ck':
                tight.append(dict(net=sh.get('net'), bbox_um=list(b), gap_to_window_nm=round(max(dx, dy) * 1000),
                                  gap_to_footprint_nm=round(max(fx, fy) * 1000)))
        out[L] = w
        report[f'M{L}'] = dict(footprint_child_um=list(fp), window_child_um=list(w),
                               guard_nm=[round((fp[0] - w[0]) * 1000), round((fp[1] - w[1]) * 1000),
                                         round((w[2] - fp[2]) * 1000), round((w[3] - fp[3]) * 1000)],
                               native_within_500nm=sorted(near, key=lambda r: r['gap_to_footprint_nm']),
                               foreign_under_32nm_of_window=tight)
    # lower / upper layers: the footprint and its vias against every foreign shape
    for ln, fps in (('M5', FP_CHILD[5]), ('V5', [box(VIA56, (0.024, 0.032))]), ('V6', [box(VIA67, (0.032, 0.032))])):
        near = []
        for sh in s:
            if sh['layer'] == ln and sh.get('net') != 'ck':
                b = um(sh['bbox']); g_ = max(gap(b, fps[0]))
                if overlaps(b, fps[0]):
                    raise ValueError(f'{ln} footprint overlaps foreign {sh}')
                if g_ <= 0.5:
                    near.append(dict(net=sh.get('net'), kind=sh['kind'], bbox_um=list(b), gap_nm=round(g_ * 1000)))
        report[ln] = dict(footprint_child_um=list(fps[0]), foreign_within_500nm=sorted(near, key=lambda r: r['gap_nm']))
    report['M8'] = dict(native_shapes_in_roi=sum(1 for sh in s if sh['layer'] in ('M8', 'V7')))
    if not (PIN_RECT[0] <= FP_CHILD[5][0][0] and FP_CHILD[5][0][2] <= PIN_RECT[2]
            and PIN_RECT[1] <= FP_CHILD[5][0][1] and FP_CHILD[5][0][3] <= PIN_RECT[3]):
        raise ValueError('M5 footprint leaves the real pin')
    return out, report


def subtract(a, b):
    x0, y0, x1, y1 = a; u0, v0, u1, v1 = b
    u0, v0, u1, v1 = max(x0, u0), max(y0, v0), min(x1, u1), min(y1, v1)
    if u0 >= u1 or v0 >= v1:
        return [a]
    return [r for r in [(x0, y0, u0, y1), (u1, y0, x1, y1), (u0, y0, u1, v0), (u0, v1, u1, y1)]
            if r[0] < r[2] and r[1] < r[3]]


def abstract(text, windows):
    out = []; inobs = False; layer = None; cuts = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == 'OBS': inobs = True
        elif inobs and stripped.startswith('END'): inobs = False
        if inobs:
            lm = re.fullmatch(r'LAYER M(\d+)\s*;', stripped)
            if lm: layer = int(lm.group(1))
            elif stripped.startswith('LAYER '): layer = None
            if layer in windows and stripped.startswith('RECT '):
                vals = stripped.split()[1:-1]
                if len(vals) != 4: raise ValueError('unsupported OBS RECT')
                a = tuple(map(float, vals)); pieces = subtract(a, windows[layer])
                if pieces != [a]: cuts += 1
                out.extend('      RECT ' + ' '.join(f'{x:.6f}' for x in r) + ' ;' for r in pieces)
                continue
        out.append(line)
    if cuts != 2: raise ValueError(f'expected exactly two blanket OBS cuts, got {cuts}')
    result = '\n'.join(out) + '\n'
    pins = lambda s: re.findall(r'^  PIN .*?^  END [^\n]+', s, re.M | re.S)
    if pins(text) != pins(result) or len(pins(text)) < 2586: raise ValueError('PIN mutation forbidden')
    if text.split('  OBS')[0] != result.split('  OBS')[0]: raise ValueError('pre-OBS bytes changed')
    return result


def on_track(v, ln):
    o, p = TRACK[ln]; k = (v - o) / p
    return abs(k - round(k)) < 1e-6


def nk_cores(plan):
    for tn, t in plan['partition_types'].items():
        for ci, c in enumerate(t.get('hard_cores', [])):
            if c.get('module') == MASTER:
                yield tn, ci, c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lef', type=Path, required=True); ap.add_argument('--pins', type=Path, required=True)
    ap.add_argument('--plan', type=Path, required=True); ap.add_argument('--roi', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists(): raise ValueError('new output directory required')
    roi = json.loads(a.roi.read_text())
    windows, wreport = derive_windows(roi)
    original = a.lef.read_text(); candidate = abstract(original, windows)
    plan = json.loads(a.plan.read_text())
    access_by, ops, rows, types = {}, [], [], []
    for tn, ci, c in nk_cores(plan):
        if tn not in types: types.append(tn)
        if c.get('clock_entry_access') or c.get('params') or c.get('lef'):
            raise ValueError(f'{tn}.{c["inst"]}: unexpected existing access/params/lef')
        if c['pins_file'] != 'cores/a0_nk_pins.json' or c['outline_um'] != list(SIZE):
            raise ValueError(f'{tn}.{c["inst"]}: unexpected pins_file/outline')
        o = c.get('orient', 'R0'); dx, dy = c.get('track_offset_um', [0.0, 0.0])
        site = (r6(c['origin_um'][0] + dx), r6(c['origin_um'][1] + dy), o)
        T = lambda r: tuple(r6(v) for v in G.transform(r, SIZE, site))
        fps = {L: [T(r) for r in FP_CHILD[L]] for L in (5, 6, 7)}
        pin_t = T(PIN_RECT + ())
        tap = (r6((fps[7][0][0] + fps[7][0][2]) / 2), r6((pin_t[1] + pin_t[3]) / 2))
        old_pin = T((OLD_PIN[1], OLD_PIN[2], OLD_PIN[1], OLD_PIN[2]))[:2]
        tdx, tdy = c['origin_um'][0] + dx, c['origin_um'][1] + dy
        if not on_track(tap[0], 'M7'): raise ValueError(f'{tn}.{c["inst"]}: tap off M7 track {tap}')
        if not on_track((fps[5][0][0] + fps[5][0][2]) / 2, 'M5'): raise ValueError('M5 footprint off track')
        if not on_track((fps[6][0][1] + fps[6][0][3]) / 2, 'M6'): raise ValueError('M6 footprint off track')
        if not (fps[5][0][1] <= tap[1] <= fps[5][0][3]) or abs(tap[1] - r6(tdy + PIN_CENTRE[1])) > 1e-6:
            raise ValueError('M5 footprint does not contain the pin centre')
        blocks, target, _ = G.geometry(candidate, MASTER, 'ck', 7, site)
        if not G.entry_clear(fps, blocks, target, 7): raise ValueError(f'{tn}.{c["inst"]}: access witness blocked')
        ob, ot, _ = G.geometry(original, MASTER, 'ck', 7, site)
        if G.entry_clear(fps, ob, ot, 7): raise ValueError('uncut blanket unexpectedly clear')
        access = {'pin': 'ck', 'footprints_um': {f'M{k}': [list(r) for r in v] for k, v in fps.items()}}
        entry_box = (tap[0] - 0.016, tap[1] - M7_PIN_LEN / 2, tap[0] + 0.016, tap[1] + M7_PIN_LEN / 2)
        G.validate_access(candidate, MASTER, access, 7, site, entry_box)
        t = plan['partition_types'][tn]
        ti = [i for i, x in enumerate(t['clock']['taps']) if x.get('name') == c['inst'] + '.ck' and x.get('kind') == 'core']
        if len(ti) != 1: raise ValueError(f'{tn}.{c["inst"]}: expected one core tap')
        ti = ti[0]; tp = t['clock']['taps'][ti]
        if any(abs(u - v) > 1e-6 for u, v in zip(tp['xy'], old_pin)):
            raise ValueError(f'{tn}.{c["inst"]}: old tap {tp["xy"]} != origin+offset+old pin {old_pin}')
        pre = f'/partition_types/{tn}'
        ops += [{'op': 'test', 'path': f'{pre}/hard_cores/{ci}/pins_file', 'value': c['pins_file']},
                {'op': 'replace', 'path': f'{pre}/hard_cores/{ci}/pins_file', 'value': NEW_PINS},
                {'op': 'add', 'path': f'{pre}/hard_cores/{ci}/clock_entry_access', 'value': access},
                {'op': 'test', 'path': f'{pre}/clock/taps/{ti}/xy', 'value': tp['xy']},
                {'op': 'replace', 'path': f'{pre}/clock/taps/{ti}/xy', 'value': list(tap)},
                {'op': 'test', 'path': f'{pre}/clock/taps/{ti}/insertion_ps', 'value': tp['insertion_ps']},
                {'op': 'replace', 'path': f'{pre}/clock/taps/{ti}/insertion_ps', 'value': SIGNOFF['tt']},
                {'op': 'test', 'path': f'{pre}/clock/taps/{ti}/insertion_ff_ps', 'value': tp['insertion_ff_ps']},
                {'op': 'replace', 'path': f'{pre}/clock/taps/{ti}/insertion_ff_ps', 'value': SIGNOFF['ff']},
                {'op': 'replace', 'path': f'{pre}/clock/taps/{ti}/budget_owner',
                 'value': 'DIE-QC-97 11-09 NK clock-pin event: signed NK vR7 eco2 re-sign pin-flop mean '
                          f'TT {SIGNOFF["tt"]} / FF {SIGNOFF["ff"]} (n 2584) at the real M5 ck pin via '
                          'clock_entry_access; parent STA unqualified'}]
        rows.append(dict(type=tn, inst=c['inst'], orient=o, site=list(site), tap=c['inst'] + '.ck',
                         old_xy=tp['xy'], new_xy=list(tap), pin_centre_xy=[r6((pin_t[0] + pin_t[2]) / 2), tap[1]],
                         old_insertion=[tp['insertion_ps'], tp['insertion_ff_ps']],
                         new_insertion=[SIGNOFF['tt'], SIGNOFF['ff']], footprints_um=access['footprints_um']))
    if len(rows) != 62 or len(types) != 16: raise ValueError(f'expected 62 NK cores in 16 types, got {len(rows)}/{len(types)}')
    pins_text = a.pins.read_text(); pins = json.loads(pins_text)
    if json.dumps(pins, indent=0) != pins_text: raise ValueError('pin table does not round-trip')
    ck = [r for r in pins['pins'] if r['name'] == 'ck']
    if len(ck) != 1 or (ck[0]['layer'], ck[0]['x'], ck[0]['y']) != OLD_PIN: raise ValueError('unexpected old ck row')
    new_pins = copy.deepcopy(pins)
    next(r for r in new_pins['pins'] if r['name'] == 'ck').update(layer='M5', x=PIN_CENTRE[0], y=PIN_CENTRE[1])
    new_text = json.dumps(new_pins, indent=0)
    diff = [(x, y) for x, y in zip(pins['pins'], new_pins['pins']) if x != y]
    if len(pins['pins']) != 2584 or len(diff) != 1: raise ValueError('pin table diff not exactly the ck row')
    sha = lambda s: hashlib.sha256(s.encode() if isinstance(s, str) else s).hexdigest()
    record = dict(schema='opentallas.clock_access.nk_adoption.v1', lane='DIE-QC-97', date='2026-11-09',
                  status='PLAN_EVENT_SOURCE (COORD-approved form); parent route/STA/DRC not yet qualified',
                  module=MASTER, signed_view='epyc6:/srv/opentallas-scratch2/claude/dq96/nk_vr7n_eco2/i1 (read only)',
                  routed_db_sha256='bfa23d1f3970648140f3965ea90a5e66bf21a652a1baa7d6842e063ca845d145',
                  original_lef_sha256=sha(original), access_lef_sha256=sha(candidate),
                  pin_blocks='byte-identical (checked); only the M6 and M7 blanket OBS rectangles are split',
                  clock_pin=dict(name='ck', layer='M5', native_rect=list(PIN_RECT)),
                  native_route_ck='VIA56 (228.972,579.088); M6 228.736..229.152 @579.072..579.104; VIA67 x228.752/229.136; '
                                  'M7 x228.752 (575.168..579.104), x229.136 (579.072..589.216)',
                  entry_stack_child=dict(via56=list(VIA56), via67=list(VIA67), m7_x=VIA67[0], m7_len_um=M7_PIN_LEN,
                                         why=__doc__.split('Entry stack')[1].split('OBS windows')[0].strip()),
                  footprints_child_um={f'M{k}': [list(r) for r in v] for k, v in FP_CHILD.items()},
                  native_obs_windows_child_um={f'M{k}': list(v) for k, v in windows.items()},
                  window_rule='footprint + 64 nm, pulled back to keep >= 32 nm to foreign shapes when the gap allows '
                              '(gap >= 64), never below the 32 nm footprint guard',
                  native_measurement=wreport, insertion=SIGNOFF, pin_cycles=0, data_cycles=0,
                  pins_file_old='cores/a0_nk_pins.json', pins_file_old_sha256=sha(pins_text),
                  pins_file_new=NEW_PINS, pins_file_new_sha256=sha(new_text),
                  types=types, cores=len(rows), instances=rows,
                  obligations=['parent VIA56/M6/VIA67/M7 entry emitted and DRC/connectivity clean in a parent pilot',
                               'parent PG clearance via the existing clock_entry_pg_cuts / pg_island_cuts hooks',
                               'access LEF paired with the unchanged signed Liberty by an honest derived-view receipt',
                               'parent clock STA with the new insertion (TT +67.45 / FF +9.5 ps vs the old 665.8/576.5)'])
    a.out.mkdir(parents=True)
    (a.out / 'a0_nk_pins.json').write_text(new_text)
    (a.out / 'proposed_event.patch.json').write_text(json.dumps(ops, indent=1) + '\n')
    (a.out / f'{MASTER}.access.lef').write_text(candidate)
    (a.out / 'adoption.json').write_text(json.dumps(record, indent=1) + '\n')
    print(json.dumps(dict(witness='PASS', types=len(types), cores=len(rows), windows=record['native_obs_windows_child_um'],
                          access_lef_sha256=record['access_lef_sha256'])))


if __name__ == '__main__':
    main()
