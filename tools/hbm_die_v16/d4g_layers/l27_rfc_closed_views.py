#!/usr/bin/env python3
"""HBM-DIE15 10-21 (next GEN after r14): select the CLOSED H.RST.FB station-hosted reset-carrier relay views.

Runs on the S8 contract produced by reset_forest_layer.py --host-hops prefer --host-form rfc (instances remastered to
hbfd_rly_<W>_<FLOW>_rfc / _rrfc).  Each such instance gets physical_view = the CLOSED record view of its exact master.
Two station forms exist and are kept apart (no alias between them):
  * f32 : ot_hbm_rly_f32 / ot_hbm_rly_rr_f32 stage reset fanned out <= 32 loads (HBM-RSTFB10, -rfc-01675cbaa kits);
  * base: ot_hbm_rly / ot_hbm_rly_rr (the other masters).
The form is read from the master body in this tree's hbfd_rly_rfc_masters.sv (source of the closed jobs, verified equal
module text per job at bind time) and recorded per instance.  Masters without a CLOSED view stay SYNTH (listed).
This selection does not qualify the parent die.
"""
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'rtl/hbm_accel/die_glue/hbfd_rly_rfc_masters.sv'
MAN = ROOT / 'results/arch/hbm_release_r15_1021/rfc_closed_views.json'
PAT = re.compile(r'^hbfd_rly_(\d+)_([A-Z]{2})_(r?rfc)$')


def station_forms():
    txt = SRC.read_text()
    out = {}
    for m in re.finditer(r'(?ms)^\s*module\s+(hbfd_rly_\w+)\b.*?^\s*endmodule', txt):
        out[m.group(1)] = 'f32' if re.search(r'\bot_hbm_rly(_rr)?_f32\b', m.group(0)) else 'base'
    return out


def apply(c, manifest):
    forms = station_forms()
    rec = {r['master']: r for r in manifest['views']}
    sel, unbound = [], {}
    for n, i in c['instances'].items():
        m = i['master']
        if not PAT.match(m):
            continue
        r = rec.get(m)
        if not r:
            unbound[m] = unbound.get(m, 0) + 1
            continue
        if forms.get(m) != r['station']:
            raise SystemExit(f'L27_STATION_FORM_MISMATCH {m}: source {forms.get(m)} vs closed {r["station"]}')
        i['physical_view'] = r['view']
        i['closed_record'] = f"H.RST.FB {r['job']} CLOSED ({r['verdict']}); station {r['station']}; record {r['record_commit'][:9]}"
        sel.append(n)
    return sel, unbound


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--manifest', type=Path, default=MAN); p.add_argument('--report', type=Path)
    a = p.parse_args()
    c = json.loads(a.input.read_text())
    sel, unbound = apply(c, json.loads(a.manifest.read_text()))
    a.output.write_text(json.dumps(c, indent=1) + '\n')
    r = dict(selected_instances=len(sel), unbound_masters=unbound,
             qualification='CLOSED_CHILD_VIEW_SELECTION; parent physical implementation outstanding')
    if a.report:
        a.report.write_text(json.dumps(r, indent=1) + '\n')
    print('L27_RFC_CLOSED_VIEWS', len(sel), 'unbound', sorted(unbound))
