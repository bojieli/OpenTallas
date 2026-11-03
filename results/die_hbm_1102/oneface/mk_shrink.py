#!/usr/bin/env python3
"""DIE-HBM-59/CORES 11-03: outline-shrink class on top of d44w (COORD GEOM 11-02 'outline shrinks').

    python3 mk_shrink.py PLAN_DIR OUT_DIR TOOLS_DIE_PLAN_DIR

PLAN_DIR = an unpacked plan dir (die_plan.json + sidecars).  The shrink itself is the shared MASTER-PLAN-R6
hub_repack.run (centre kept, origin on the 4.32 lattice, edge pins keep their edge and scale along it, stations with
an endpoint on a shrunk core regenerated).  This wrapper adds what the HBM plan dir also carries:
  core_macros.json  KNOWN macro rects shift by the centre offset (dW/2, dH/2) and are re-checked with the
                    core_macros_fix 10.8-um channel arithmetic;
  clock_entries.json  the plan centre entry moves to the new centre (die position unchanged: dW, dH are multiples of
                    8.64, so the new centre = the old centre); the type clock taps are asserted unchanged;
  lef/lib           a hard core whose plan row points at a fixed abstract view at the old outline drops it (the
                    kit re-cut gives the new abstract).
Only HEIGHT shrinks: these cores are pin-perimeter bound, so every new height is the smallest multiple of 8.64 step
that keeps each W/E face <= 5 pins/um (remap_pins 0.192-um spacing) and the macros inside their channels; N/S faces keep
their density.  q3_vm_core is NOT shrunk (W face already 6.04 pins/um).
"""
import json, math, sys
from pathlib import Path

plan, out, tools = map(Path, sys.argv[1:4])
sys.path.insert(0, str(tools))
sys.path.insert(0, str(tools.parent.parent / 'physical' / 'die_plan' / 'hbm'))
import hub_repack as HR  # noqa: E402
import core_macros_fix as CMF  # noqa: E402

BUDGET = 5.0          # hub_repack.remap_pins keeps >= 0.192 um between scaled pins (5.2/um max)
STEP = 8.64
P = json.loads((plan / 'die_plan.json').read_text())
CM = json.loads((plan / 'core_macros.json').read_text())
# q3_body_core (1054.08 -> 941.76 by the pin rule) is left out: its regenerated inj_idx/inj_d stations to u_cij_Q
# needed 10 -> 14 registers (latency change -> TOK source event, types held).  q2n2_vm_core: W 2677 pins need 535 um.
CAND = ['ot_hbm_su_static_pgslice_lg__lanes8_11', 'ot_hbm_su_static_cxport_ij_q', 'ot_hfd_coll_q2n2_vm_core']
FILL = {'ot_hbm_su_static_pgslice_lg__lanes8_11': 0.0641, 'ot_hbm_su_static_cxport_ij_q': 0.0612,
        'ot_hfd_coll_q2n2_vm_core': 0.0328, 'ot_hfd_coll_q3_body_core': 0.0723}   # AUTO-GEOM d44o attempts
TARGET_FILL = 0.15


def first_hc(m):
    return next(h for t in P['partition_types'].values() for h in t.get('hard_cores') or [] if h['module'] == m)


spec, plan_rows = [], {}
for m in CAND:
    h = first_hc(m)
    W, H = h['outline_um']
    pins = json.loads((plan / h['pins_file']).read_text())
    we = max(sum(1 for q in pins if q['x'] <= 0.5), sum(1 for q in pins if q['x'] >= W - 0.5))
    rows = (CM['cores'].get(m) or {}).get('macros') or []
    h_pins = we / BUDGET
    h_mac = 0.0
    if rows:
        y0, y1 = min(r['rect_um'][1] for r in rows), max(r['rect_um'][3] for r in rows)
        c = H / 2
        h_mac = 2 * max(c - y0, y1 - c) + 2 * (CMF.CH + CMF.INSET)      # centred macro band + edge channels
    h_fill = H * FILL[m] / TARGET_FILL                                    # no smaller than the fill target needs
    need = max(h_pins, h_mac, h_fill)
    k = math.floor(round((H - need) / STEP, 6))
    if k <= 0:
        continue
    H2 = round(H - k * STEP, 3)
    plan_rows[m] = dict(old=[W, H], new=[W, H2], we_pins=we, we_density=round(we / H2, 2), need=dict(
        pins=round(h_pins, 1), macros=round(h_mac, 1), fill=round(h_fill, 1)), est_fill=round(FILL[m] * H / H2, 4))
    spec.append(dict(module=m, outline_um=[W, H2], est_fill=round(FILL[m] * H / H2, 4), macro_fit=True,
                     source='DIE-HBM-59 ONEFACE shrink class (height only, W/E <= 5 pins/um)'))

def taps_of(PP):
    return {tn: sorted((tp['name'], round(tp['xy'][0], 3), round(tp['xy'][1], 3)) for tp in (t.get('clock') or {}).get('taps', []))
            for tn, t in PP['partition_types'].items()}


old_taps = taps_of(P)
rep = HR.run(plan, out, [], spec, log=print)
# post: core_macros + clock_entries + lef/lib
P2 = json.loads((out / 'die_plan.json').read_text())
# hub_repack resets every tap of a touched type from entries.json (origin + entry); the HBM taps come from
# clock_entries.json, so the plan taps are restored (centre-kept shrink: same die position) and entries.json too.
for tn, t in P2['partition_types'].items():
    if (t.get('clock') or {}).get('taps'):
        t['clock']['taps'] = P['partition_types'][tn]['clock']['taps']
assert taps_of(P2) == old_taps
if (plan / 'entries.json').exists():
    (out / 'entries.json').unlink()
    (out / 'entries.json').write_bytes((plan / 'entries.json').read_bytes())
dropped = []
for tn, t in P2['partition_types'].items():
    for h in t.get('hard_cores') or []:
        if h['module'] in plan_rows and (h.get('lef') or h.get('lib')):
            dropped.append(dict(type=tn, inst=h['inst'], lef=h.pop('lef', None), lib=h.pop('lib', None)))
            h['note'] += ' | DIE-HBM-59: fixed abstract lef/lib at the old outline dropped (kit re-cut gives the new one)'
(out / 'die_plan.json').unlink()
(out / 'die_plan.json').write_text(json.dumps(P2, indent=1) + '\n')
for m, r in plan_rows.items():
    e = CM['cores'].get(m)
    if not e:
        continue
    dx, dy = (r['old'][0] - r['new'][0]) / 2, (r['old'][1] - r['new'][1]) / 2
    e['outline_um'] = r['new']
    for row in e.get('macros') or []:
        x0, y0, x1, y1 = row['rect_um']
        row['rect_um'] = [round(x0 - dx, 4), round(y0 - dy, 4), round(x1 - dx, 4), round(y1 - dy, 4)]
    if e.get('macros'):
        err, _ = CMF.channel_errors(e['macros'], r['new'])
        assert not err, (m, err[:3])
    e['note'] = (e.get('note') or '') + ' | DIE-HBM-59 shrink %gx%g -> %gx%g (rects shifted by the centre offset)' % (
        *r['old'], *r['new'])
for name in ('core_macros.json', 'clock_entries.json'):
    if (out / name).exists() or (out / name).is_symlink():
        (out / name).unlink()
(out / 'core_macros.json').write_text(json.dumps(CM, indent=1))
CE = json.loads((plan / 'clock_entries.json').read_text())
moved = 0
for tn, d in CE.items():
    for inst, e in d.items():
        m = e.get('module')
        if m in plan_rows:
            W2, H2 = plan_rows[m]['new']
            cx, cy = HR.sn(W2 / 2), HR.sn(H2 / 2)
            e['xy_um'] = [cx, cy]
            e['island_um'] = [round(cx - 4.32, 3), round(cy - 4.32, 3), round(cx + 4.32, 3), round(cy + 4.32, 3)]
            e['source'] = e.get('source', '') + ' | DIE-HBM-59 shrink: new centre (same die position)'
            moved += 1
(out / 'clock_entries.json').write_text(json.dumps(CE, indent=1))
summary = dict(schema='opentallas.hbm_plan_event.v1', event='d44w-shrink', shrinks=plan_rows, clock_entries_moved=moved,
               lef_dropped=dropped, hub_repack=dict(shrinks=rep['shrinks'], stations=rep['stations'],
                                                    new_pin_files=rep['new_pin_files'], plan_sha256=rep['plan_sha256']))
(out / 'shrink_event.json').write_text(json.dumps(summary, indent=1))
print(json.dumps(dict(shrinks=plan_rows, moved=moved, dropped=len(dropped)), indent=1))
