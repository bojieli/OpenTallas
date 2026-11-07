#!/usr/bin/env python3
"""DIE-HEAD-77-LEP2: attach the SIGNED LEP pair vE views (clk moved to the S face) to hd_lep0N, plus 4 early core taps.

Why: hd_lep0N fails because CTS reaches the four pair clk pins, which sat in the pair interior at (388.92, 246.24), only
through long leads: tap insertion 1251 ps against a 450 ps target, hold -850. vE (COORD 15:0x RE-FORM) has the same
netlist and CTS tree with clk on the S face M5 (397.464, 0.24), which faces the hd_lep0N middle street in all 4 placements.

Changes, hd_lep0N only:
  1. hard_cores[ot_s81hd_lep_pair].lef / lib -> VIEW (detailed LEF: the plain abstract fails DRT-0073);
  2. clock.core_taps = 'early' and clock.taps = one core tap per pair beside the transformed vE clk pin (schema.tap_clear
     picks the nearest channel off the TX banks, 6-43 um from the pin), insertion = SIGNED TT pin-register mean from
     VIEW/clock_contract.json (early_core_taps.add_from_means).
  3. The clk pin on a face is an exception to METHODOLOGY 12.8a (COORD 15:0x), recorded in each pair's note.

Not changed: pin tables, outlines, origins, RTL cycles, sidecar, clock.insertion_ps.  The vE pair TT mean 529.22 is above the
common latency 450: the spine delivers each tap 79.22 ps early (FF 434.56 vs 380: 54.56 ps, schema.core_tap_early_ps), so the
pair's registers still land at the common latency.

usage: head_lep_pair_ve_delta.py PLAN OUT --root REPO_ROOT
       head_lep_pair_ve_delta.py --prepared SRC_DIR OUT_DIR --root REPO_ROOT [--event l48uk]
"""
import argparse
import copy
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'die_plan'))
import early_core_taps as E  # noqa: E402

TYPE = 'hd_lep0N'
MODULE = 'ot_s81hd_lep_pair'
VIEW = 'results/head_lep_pair_views_vE_1106/' + MODULE
EXPECT = {'u_core.u.g_pp[0].u_pair': (1278.744, 509.52), 'u_core.u.g_pp[1].u_pair': (466.584, 665.52),
          'u_core.u.g_pp[2].u_pair': (466.584, 509.52), 'u_core.u.g_pp[3].u_pair': (1261.416, 665.52)}
NOTE = ('DIE-HEAD-77-LEP2: SIGNED vE view, clk on the S face M5 (397.464,0.24); exception to METHODOLOGY 12.8a '
        '(COORD 15:0x RE-FORM). Parent must use this detailed LEF.')


def apply(plan, root):
    out = copy.deepcopy(plan)
    if out.get('die', {}).get('name') != 's81_head':
        raise ValueError('HEAD plan required')
    t = out['partition_types'][TYPE]
    cores = [c for c in t.get('hard_cores', []) if c.get('module') == MODULE]
    if len(cores) != 4:
        raise ValueError('expected exactly four LEP pair children')
    if t['clock'].get('taps') or t['clock'].get('core_taps'):
        raise ValueError(TYPE + ' already declares core taps: review explicitly')
    for c in cores:
        if c.get('outline_um') != [777.6, 492.48]:
            raise ValueError('vE is for the exact 777.6 x 492.48 child')
        c['lef'] = VIEW + '.lef'
        c['lib'] = VIEW + '_tt.lib'
        c['note'] = (c.get('note', '') + ' | ' + NOTE).lstrip(' |')
    taps = E.add_from_means(t, modules={MODULE}, root=root)
    ff = json.loads((Path(root) / (VIEW.rsplit('/', 1)[0] + '/clock_contract.json')).read_text())['pins']['clk']['ff']['mean_ps']
    for x in taps:
        x['insertion_ff_ps'] = ff
    got = {x['name'].rsplit('.', 1)[0]: tuple(x['xy']) for x in taps}
    if len(taps) != 4 or set(got) != set(EXPECT):
        raise ValueError(f'expected 4 pair taps, got {sorted(got)}')
    for k, xy in EXPECT.items():
        if max(abs(a - b) for a, b in zip(got[k], xy)) > 50.0:  # tap_clear steps off TX banks into the nearest channel (6-43 um)
            raise ValueError(f'{k}: tap {got[k]} is far from the vE clk pin {xy}')
    return out


def prepared(a):
    """prepared dir: source_plan.json + the hd_lep0N wrapper + wave_prepare.json + SHA256SUMS, as head_spn_fstart_delta."""
    root = a.root.resolve()
    sys.path[:0] = [str(root / 'tools/s81_head')]
    import head_cland_stage_delta as C
    plan = apply(json.loads((a.plan / 'source_plan.json').read_text()), root)
    old = json.loads((a.plan / 'wave_prepare.json').read_text())
    shutil.copytree(a.plan, a.out, symlinks=True)
    C.writable(a.out)
    (a.out / 'source_plan.json').write_text(json.dumps(plan, indent=1) + '\n')
    C.republish(a.out, root, [TYPE], a.out / 'source_sidecar.json')
    rec = json.loads((a.out / 'wave_prepare.json').read_text())
    assert rec['sidecar_sha256'] == old['sidecar_sha256'], 'sidecar must not change'
    changed = [t for t, w in old['published_wrappers'].items() if rec['published_wrappers'][t] != w]
    if set(changed) - {TYPE}:
        raise SystemExit(f'wrappers changed outside {TYPE}: {changed}')
    rec[a.event] = dict(event=a.event, tool='tools/s81_head/head_lep_pair_ve_delta.py', types=[TYPE], base_prepared=str(a.plan),
                        base_prepared_plan_sha256=old['prepared_plan_sha256'], view=VIEW, wrapper_changed=changed,
                        data_cycles_added=0)
    (a.out / 'wave_prepare.json').write_text(json.dumps(rec, indent=1) + '\n')
    sums = a.out / 'SHA256SUMS'
    if sums.exists():
        lines = []
        for ln in sums.read_text().splitlines():
            _h, _, name = ln.partition('  ')
            f = a.out / name
            lines.append(f'{C.digest(f)}  {name}' if f.is_file() and not f.is_symlink() else ln)
        sums.write_text('\n'.join(lines) + '\n')
    print(json.dumps(rec[a.event], indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--prepared', action='store_true', help='PLAN and OUT are prepared dirs: wrapper republished, record kept')
    ap.add_argument('--event', default='l48uk')
    a = ap.parse_args()
    if a.out.exists():
        ap.error('fresh output required')
    if a.prepared:
        return prepared(a)
    out = apply(json.loads(a.plan.read_text()), a.root)
    for typ in out['partition_types'].values():  # pin tables stay those of the supplied plan
        for c in typ.get('hard_cores', []):
            if c.get('pins_file'):
                f = (a.plan.parent / c['pins_file']).resolve()
                if f.is_file():
                    c['pins_file'] = os.path.relpath(f, a.out.parent.resolve())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    for x in out['partition_types'][TYPE]['clock']['taps']:
        print('TAP', x['name'], x['xy'], x['insertion_ps'])
    print('HEAD_LEP_PAIR_VE_DELTA 4 views, 4 early taps; 0 geometry/RTL/cycle changes')


if __name__ == '__main__':
    main()
