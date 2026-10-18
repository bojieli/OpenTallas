#!/usr/bin/env python3
"""S81-LAND2 10-17: ref_tile specs of the HALF-CYCLE lane relay successors dsfd_dvrlyh_<W>_<dir>
(RTL rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv: ot_dvrly_st #(W, HC=1) = the dsfd_dvrly_* body with ck_o = ~ck
through ONE kept ot_dvrly_ckinv; LANDING-CONTRACT H3 hold fix (a)).
Each spec is the closed s81dv_rly_<W>_<dir> spec with: top / sources / benches renamed, the inverted generated clock
(physical/s81_die_pins/dvrlyh/fwd_ck_o_inv.tcl), and the half-cycle chain bench + its mutant (bench_rlyh.sh).  Same
outline, same pin plan (io_tcl unchanged: identical ports).  Built for the closed (width, direction) views the die uses
(owner 10-15: no unused variants; the 68-b kits are retired since p4j).
Usage: gen_dvrlyh_kits.py [--owner O --branch B]   (writes tools/ref_tile/specs/s81dv_rlyh_<W>_<dir>.json)
"""
import argparse, copy, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
USED = {276: ('ew', 'we', 'ns', 'sn'), 512: ('ew', 'we'), 562: ('ew', 'we', 'sn'), 682: ('ew', 'we', 'ns'), 70: ('ns', 'sn')}
DVH = 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv'
FWD = 'physical/s81_die_pins/dvrlyh/fwd_ck_o_inv.tcl'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--owner', default='Claude:S81-LAND2')
    ap.add_argument('--branch', default='claude/s81land2-rly-1017')
    ap.add_argument('--tag', default='h1')
    a = ap.parse_args()
    for W, dirs in USED.items():
        for d in dirs:
            D = d.upper()
            s = json.loads((ROOT / f'tools/ref_tile/specs/s81dv_rly_{W}_{d}.json').read_text())
            old, top, name = f'dsfd_dvrly_{W}_{D}', f'dsfd_dvrlyh_{W}_{D}', f's81dv_rlyh_{W}_{d}'
            s = copy.deepcopy(s)
            s['name'], s['top'] = name, top
            s['sources'] = [x for x in s['sources']] + [DVH]
            s['sdc_extra'] = [FWD if 'fwd_ck_o' in x else x for x in s.get('sdc_extra', [])]
            s['boundary_tcl'] = [FWD if 'fwd_ck_o' in x else x for x in s.get('boundary_tcl', [])]
            s['structural_change'] = (
                f'S81-LAND2 10-17 (LANDING-CONTRACT H3, hold fix (a)): half-cycle successor of the closed s81dv_rly_{W}_{d} '
                f'({old}): ot_dvrly_st W={W} HC=1, the same one-stage ot_s81_rly RSREG=1 body, ck_o = ~ck through ONE kept '
                'ot_dvrly_ckinv (inverted generated clock ck_o_fwd), so station k+1 captures half a period after station k: '
                'the p4j pilot relay->relay hold (-120..-195 ps, clock leg > data leg) gains ~T/2 and the lane is two stations '
                'per root cycle (half the lane latency). Same outline / pins / recipe 4 flop-first / hold_budget die / M5 cap. '
                '| base: ' + s.get('structural_change', ''))
            j = s['job']
            j.update(owner=a.owner, branch=a.branch, tag=a.tag,
                     purpose=f'S81-DV {W}-b HALF-CYCLE lane relay station {top} (successor of {old}; ck_o = ~ck)',
                     views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}')
            j['extra_paths'] = sorted(set(j.get('extra_paths', []) + ['rtl/dsrom_sys/s81_glue', 'physical/s81_die_pins/dvrlyh']))
            for b in j['benches']:
                b['cmd'] = b['cmd'].replace(old, top)
                if b['name'] == 'lint':
                    b['cmd'] = b['cmd'].replace('&& echo lint-ok', f'{DVH} && echo lint-ok')
                    if 'dsfd_rly_masters_dv276.sv' not in b['cmd']:
                        b['cmd'] = b['cmd'].replace(DVH, 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv ' + DVH)
            j['benches'] = [b for b in j['benches'] if not b['name'].startswith('half_')] + [
                dict(name='half_cycle_chain', cmd=f'bash rtl/dsrom_sys/s81_glue/test/bench_rlyh.sh pass {top} {W} {{RUN}}/bench_h 3',
                     expect='pass', pass_regex='RLYH_BENCH PASS 0 errors in 60000 checks', threads=2, peak_ram_gb=4),
                dict(name='full_cycle_ck_o_mutant', cmd=f'bash rtl/dsrom_sys/s81_glue/test/bench_rlyh.sh mut {top} {W} {{RUN}}/bench_hm 3',
                     expect='fail', fail_regex='RLYH_BENCH FAIL', threads=2, peak_ram_gb=4)]
            (ROOT / f'tools/ref_tile/specs/{name}.json').write_text(json.dumps(s, indent=1) + '\n')
            print(name, s['outline'], s['io_tcl'])


if __name__ == '__main__':
    main()
