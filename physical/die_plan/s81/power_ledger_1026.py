#!/usr/bin/env python3
"""Reconcile 72-frame S81 PHY inventory with the historical die/rack power.

Read committed inputs only. Separate the known double count from the unknown
current core power. The sensitivity rows are MODEL, never a measured power
report or an automatic replacement of the released rack headline.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path


def build(repo, ref):
    sha = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', ref], text=True).strip()
    def read(path):
        return json.loads(subprocess.check_output(['git', '-C', str(repo), 'show', f'{sha}:{path}']))
    plan = read('physical/die_plan/s81/die_plan.json')
    assumptions = read('physical/die_plan/s81/phy_assumptions.json')
    old = read('results/rtl/dsrom_s81_fulldie_20261004/floorplan.json')['scan_die_power']
    rack = read('results/arch/release_rack_1021/rack.json')
    stage_input = read('results/arch/release_rack_1021/s81_stage_map_input.json')
    s81 = next(s for s in rack['systems'] if s['name'] == 'S81')
    entries = {e['id']: e for e in assumptions['entries']}
    macros = [io for io in plan['die']['io'] if io.get('iface') == 'serdes']
    phy_w = entries['SER.MACRO6_POWER']['value']
    match = re.search(r'([0-9.]+) W of it SerDes', old['basis'])
    if not match:
        raise ValueError('historical die record does not identify included SerDes power')
    included = float(match[1])
    legacy = old['total_saturated_w']
    core_proxy = round(legacy - included, 6)
    counts = s81['counts']
    layer_copies = counts['layer_dies'] + counts['copy_b_dies']
    assert counts['total_dies'] == layer_copies + counts['head_dies']
    assert stage_input['die_frames'] == 72
    assert counts['layer_dies'] == stage_input['stages'] * stage_input['tp']
    rows = s81['trays']['rows']
    old_ser = sum(t['serdes_w'] for t in rows)
    old_it = sum(t['it_w'] for t in rows)
    correction = included * layer_copies
    # Keep the rack's existing head PHY charge; its historical core/PHY split is unknown.
    head_macros = counts['head_dies'] * s81['die_links']['head']['value']
    all_physical_ser = (len(macros) * layer_copies + head_macros) * phy_w
    v = lambda key: rack['constants'][key]['value']
    scenarios = []
    for name, it, explanation in (
        ('remove_known_legacy_PHY_double_count', old_it - correction,
         'Same historical core and active-circuit PHY inventory; subtract only the proven included 30.6 W per layer/copy-B die.'),
        ('all_14_layer_PHYs_powered', old_it - correction - old_ser + all_physical_ser,
         'Historical non-PHY core proxy retained; all 14 physical SerDes macros per layer/copy-B die powered at the published assumption. Head charge stays historical; no new idle-gating claim.')
    ):
        dc = it / v('vr_efficiency')
        scenarios.append(dict(name=name, grade='MODEL sensitivity', it_kw=round(it/1000, 3),
                              dc_kw=round(dc/1000, 3),
                              wall_D_kw=round((dc+s81['power']['D_link_w'])/v('psu_efficiency')/1000, 3),
                              explanation=explanation))
    return dict(schema='opentallas.s81.power_reconciliation.v1', source_commit=sha,
        status='PHY accounting reconciled; current 72-frame core power NOT MEASURED',
        inventory=dict(frames_per_layer_die=stage_input['die_frames'], stages=counts['stages'],
            rank_layer_dies=counts['layer_dies'], copy_b_dies=counts['copy_b_dies'],
            physical_layer_die_copies=layer_copies, head_dies=counts['head_dies'],
            total_dies=counts['total_dies'], physical_layer_frames=72*layer_copies,
            serdes_macros_per_layer_die=len(macros), serdes_instance_names=[io['part'] for io in macros],
            grade=counts['grade'], note='72 is frames per die, not the count of stages, dies or copy-B groups.'),
        historical_die=dict(total_saturated_w=legacy, included_serdes_w=included,
            non_serdes_proxy_w=core_proxy, basis=old['basis'],
            source='results/rtl/dsrom_s81_fulldie_20261004/floorplan.json#scan_die_power',
            limitation='The old die is not the current 72-frame implementation. Do not scale it by 72/81; its stages=81 is the old array stage count.'),
        current_PHY=dict(grade='published ASSUMPTION', per_macro_w=phy_w,
            plan_all_macros_w=round(len(macros)*phy_w, 3),
            die_total_with_historical_core_proxy_w=round(core_proxy+len(macros)*phy_w, 3),
            all_layer_die_PHY_w=round(len(macros)*phy_w*layer_copies, 3),
            prior_rack_macros_per_rank=s81['die_links']['rank']['value'],
            prior_rack_macros_per_copy_ab=s81['die_links']['copy_ab']['value'],
            limitation='Physical plan inventory is 14. Rack active-circuit counts 10/12 do not establish that the remaining PHYs are power-gated.'),
        rack_known_double_count=dict(layer_die_copies=layer_copies, per_die_w=included,
            total_w=round(correction, 3), old_it_kw=round(old_it/1000, 3),
            head_PHY_double_count='UNKNOWN; head ledger needs an independent component split'),
        scenarios=scenarios,
        remaining=['Current 72-frame core static/dynamic power and activity at the priced token calendar.',
                   'Released PHY idle/power-gating contract and active macro counts by die role.',
                   'Head-die power split after 4-die/no-HBM composition.',
                   'Re-run infra-first PG/IR at per-region current power and published PHY 4.37 W/macro.'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument('--ref', default='HEAD')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = build(args.repo, args.ref)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
