#!/usr/bin/env python3
"""S81 die contract v21 (GEN18 candidate), S-DIE r11 2026-10-15.

Base: results/arch/hier_contract_1011/s81_v20_hc_up.json (GEN17's contract, v20 HC
native geometry, south anchor). Changes, each recorded in `v21_gen18`:
  * sp_gather slot 1728 x 803.496 -> 1728 x 1045.44 (+241.92 N): S-GATHER v21
    transverse RE leaf (CLOSED, native 0 flags), pin file
    physical/s81_die_pins/v21_gather_transverse_candidate/dsfd_sp_gather_c.json.
    Die decision 2026-10-15 05:13: FLATTEN = YES (the die owns the 214 children);
    generator flatten support is not built yet, so GEN18 keeps the slot outline.
  * static seams (owner static-cycle rule): sp_vm <-> sp_collective uses the static
    masters' ports (generator --static-seams); recorded here as the seam contract.
Screen candidate only: no slot here is granted until the GEN18 build is legal.
"""
import argparse, copy, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATHER_H = 1045.44


def build(base):
    c = copy.deepcopy(base)
    slots = {s['name']: s for s in c['slots']}
    g = slots['sp_gather']
    old_h = g['outline']['h']
    g['outline']['h'] = GATHER_H
    g['version'] = 21
    c['version'] = 21
    c['v21_gen18'] = dict(
        status='CANDIDATE_SCREEN_NOT_GRANTED',
        base='results/arch/hier_contract_1011/s81_v20_hc_up.json',
        sp_gather=dict(old_h=old_h, new_h=GATHER_H, growth_n_um=round(GATHER_H - old_h, 3),
                       pin_file='physical/s81_die_pins/v21_gather_transverse_candidate/dsfd_sp_gather_c.json',
                       decision='el1011-s81die.log 2026-10-15 05:13:51 FLATTEN=YES; flatten generator support pending'),
        static_seams=dict(vm=dict(f_collective=2204, f_crq=15, t_crs=513, source='rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv'),
                          collective=dict(master='dsfd_sp_collective_static_c', t_vm=2204, t_crq=15, f_crs=513,
                                          t_hc_y=8192, t_hc_yv=1, t_hc_tag=32,
                                          source='origin/codex/s81-static-collective-1014 574f05810 (NOT on main yet)'),
                          dropped=['vm.t_collective[592]', 'vm.tcs[3] (room back-pressure)', 'hc_s.y_rdy -> collective.f_hc_yr'],
                          hc_consumer_slot='hc_s.y_tag[32] <- collective.t_hc_tag (static HC POST consumer, owner s_func)'))
    c.setdefault('changelog', []).append(
        'v21 GEN18 candidate (S-DIE r11 2026-10-15): sp_gather +241.92 N (v21 transverse RE), static VM/collective seam, HC y_tag slot; screen only.')
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='results/arch/hier_contract_1011/s81_v20_hc_up.json')
    ap.add_argument('--output', default='results/arch/hier_contract_1011/s81_v21_gen18.json')
    a = ap.parse_args()
    out = build(json.loads((ROOT / a.input).read_text()))
    (ROOT / a.output).write_text(json.dumps(out, indent=1) + '\n')
    print(a.output, out['version'])


if __name__ == '__main__':
    main()
