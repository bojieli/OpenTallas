#!/usr/bin/env python3
"""L2H-RSTFB 10-19 (H.RST.FB): ref_tile specs for the station-hosted reset carrier masters hbfd_rly_<W>_<flow>_rfc / _rrfc
(rtl/hbm_accel/die_glue/hbfd_rly_rfc_masters.sv), one per relay station master GEN2d instantiates (16 base masters:
48 / 624 x WE EW SN NS, 136 x WE EW SN NS, 304 / 1136 x WE EW), each as _rfc (over the closed base kit) and _rrfc (over the
HBM-RSTROW _rr kit).  Kit = the station kit (same outline, recipe, pin faces, hold/pin-reg settings) + rfi on the i face
and rfo on the o face; the carrier stage is 3 flops (2 landing flops async-cleared by rfi + 1 sync carrier flop).

    python3 results/arch/hbm_die_d4g/rstfb/gen_kits.py        writes tools/ref_tile/specs_hbmrly_rfc/<kit>.json
"""
import copy, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE, RR, OUT = (ROOT / 'tools/ref_tile' / d for d in ('specs_hbmrly', 'specs_hbmrly_rr', 'specs_hbmrly_rfc'))
USED = ['48_we', '48_ew', '48_sn', '48_ns', '624_we', '624_ew', '624_sn', '624_ns',
        '136_we', '136_ew', '136_sn', '136_ns', '304_we', '304_ew', '1136_we', '1136_ew']
WIT = 'results/rtl/hbm_rly_rfc_1019'
BENCH = 'rtl/hbm_accel/die_glue/test/bench_rly_rfc.sh'
SOURCES = ['rtl/lib/ot_rst_relay.sv', 'rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv',
           'rtl/hbm_accel/die_glue/ot_hbm_rly_rfc.sv', 'rtl/hbm_accel/die_glue/hbfd_rly_rfc_masters.sv']
MUTANTS = [  # mode, fail regex
    ('land1mut', r'RLY_RFC_BENCH FAIL \d+ errors \d+ rso_errors [1-9]\d* rfc_errors \d+ assert_errors [1-9]\d* age_errors'),
    ('combmut', r'RLY_RFC_BENCH FAIL \d+ errors \d+ rso_errors [1-9]\d* rfc_errors \d+ assert_errors [1-9]\d* age_errors'),
    ('nogatemut', r'RLY_RFC_BENCH FAIL \d+ errors \d+ rso_errors \d+ rfc_errors [1-9]\d* assert_errors'),
    ('datamut', r'RLY_RFC_BENCH FAIL [1-9]\d* errors'),
]
CHECKLIST = [
    ('1 pins', 'PASS: station pins unchanged (i captured / o launched by the ONE stage register, as the closed kit); rfi '
               'lands in 2 registered stages at the face (async clear of exactly the 2 landing flops, textbook '
               'reset_landing <= 2 sinks on rfi); rfo = land[1] & carrier flop q (flop-driven; AND for immediate assert)'),
    ('2 reach', 'PASS: no new wire inside the tile beyond the station outline (<= 114.5 um); forest edges into rfi / out of '
                'rfo are reach-checked by reset_forest_layer (hop budget) and re-checked on real LEF pins by die_case'),
    ('3 fanout', 'PASS: rfi drives 2 flops, land[1] drives q + the AND, rfo drives one forest stage or leaf'),
    ('4 depth', 'PASS: rfi -> async clear; flop -> AND -> rfo; no combinational data in->out path'),
    ('5 storage', 'PASS: 3 flops; no delay line >= 3 (the 3-edge age is 2 landing + 1 carrier flop, not a shift chain)'),
    ('6 floorplan', 'PASS: same outline as the closed station kit (+3 flops on a >= 21.6 x 21.6 um strip: util rise < 1%); '
                    'rfi on the i face, rfo on the o face (1136 _rrfc: both on the ck/rs face, the o face is pin-full)'),
    ('7 clock', 'PASS: the station clock ck (planner hosts only on stations of the forest domain); hold_margin / '
                'io_hold_margin 0.03; pin-flop spread judged by the gate --cts'),
    ('8 schedule', 'PASS: static; data stage unchanged (0 data cycles); reset release age 3 edges per hosted stage, charged '
                   'by reset_forest_layer --host-form rfc in every leaf / pad age (equal-age leaves)'),
]


def flow_faces(pins):
    fi = next(f for f, ps in pins.items() if 'i' in ps)
    fo = next(f for f, ps in pins.items() if 'o' in ps)
    return fi, fo


def make(stem, rr):
    b = json.loads((BASE / f'hbfd_rly_{stem}.json').read_text())
    r = json.loads((RR / f'hbfd_rly_{stem}_rr.json').read_text())
    s = copy.deepcopy(r)
    w = int(stem.split('_')[0])
    rel = 3 if (w > 256 or w == 136) else 0
    if rr:
        name, top = r['name'] + 'fc', r['top'] + 'fc'
        pins = copy.deepcopy(r['pins'])
        land_max = r['reset_landing']['max_sinks']
        base_kit = r['name']
    else:
        name, top = b['name'] + '_rfc', b['top'] + '_rfc'
        pins = copy.deepcopy(b['pins'])
        land_max = r['reset_landing']['max_sinks'] - 1   # no row-reset flop rq
        s['outline'] = copy.deepcopy(b['outline'])
        base_kit = b['name']
    s['outline'] = dict(s['outline'], exact=True)   # the placed station footprint, never re-sized
    fi, fo = flow_faces(pins)
    if rr and w == 1136:
        # the 114.48 um o face holds o + rso = 1137 pins (96 % of its M4 slots): rfi / rfo go on the clock face beside
        # ck / rs (<= 114.5 um from the i/o face middles; die_case re-checks the real LEF pins)
        fi = fo = next(f for f, ps in pins.items() if 'ck' in ps)
    pins[fi] = pins[fi] + ['rfi']
    pins[fo] = pins[fo] + ['rfo']
    s.update(name=name, top=top, sources=list(SOURCES), pins=pins, reset_ports=['rs', 'rfi'])
    s['route'] = dict(s.get('route') or {}, hold_margin_ns=0.03, io_hold_margin_ns=0.03)
    s['reset_landing'] = dict(enable=False, max_sinks=land_max, reason=(
        f'rfi (the new reset-forest carrier input) lands in exactly 2 registered stages in the RTL (ot_hbm_rly_rfc: '
        f'2 sinks); rs is the UNCHANGED station reset of {base_kit} ({land_max} sinks: '
        + ('stage async clear + row-reset flop rq, ' if rr else 'stage async clear, ')
        + 'as the closed kit) -- a kit landing on rs would add release edges the relay-row / stage schedule does not price'))
    s['pin_regs'] = dict(enable=False, reason=(
        'relay = ONE register stage at the pins by definition (as the closed station kits); rfo is launched by the '
        'carrier stage (land[1] & q) and rfi is its 2-flop landing: a pin register would add an unpriced edge'))
    benches = [dict(name='rfc_exact', cmd=f'bash {BENCH} pass {top} {w} {{RUN}}/bench_p {rel} {int(rr)}', expect='pass',
                    pass_regex=(r'RLY_RFC_BENCH PASS 0 errors 0 rso_errors 0 rfc_errors 0 assert_errors 0 age_errors '
                                r'trials=401 ages_checked=\d+ \(' + top + r' W=' + str(w) + r'\) rfc_age=3'),
                    min_count_regex=r'ages_checked=(\d+)', threads=2, peak_ram_gb=4 if w < 600 else 8,
                    needs=['verilator'], pass_witness=f'{WIT}/{name}_pass.log')]
    for mode, rx in MUTANTS:
        benches.append(dict(name=f'neg_{mode}', cmd=f'bash {BENCH} {mode} {top} {w} {{RUN}}/bench_{mode} {rel} {int(rr)}',
                            expect='fail', fail_regex=rx, threads=2, peak_ram_gb=4 if w < 600 else 8,
                            needs=['verilator'], fail_witness=f'{WIT}/{name}_{mode}.log'))
    s['job'] = dict(owner='Claude:LEAD3-HBM/L2H-RSTFB', branch='claude/hd4g-rstfb-1019', tag='rfc',
                    purpose=(f'HBM d4g H.RST.FB station-hosted reset carrier {top}: {base_kit} unchanged + carrier stage '
                             'rfi -> 2-stage landing -> rfo (assert immediate, release 3 edges)'),
                    benches=benches, views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}',
                    extra_paths=[BENCH])
    s['structural_change'] = (
        f'L2H-RSTFB 2026-10-19 (H.RST.FB): NEW master {top} = {base_kit} (station instantiated unchanged) + ONE '
        'reset-forest carrier stage ot_hbm_rly_rfc (rfi async-clears 2 landing flops, sync carrier flop q, rfo = land[1] '
        '& q: assert immediate, release exactly 3 edges); rfi on the i face, rfo on the o face; outline / recipe / pin '
        'faces of the closed kit; 0 data cycles.  SAFE-DESIGN checklist: ' + '; '.join(f'{k} {v.split(":")[0]}' for k, v in CHECKLIST))
    s['reroute_reason'] = dict(kind='rtl_change', cell=top, base_kit=base_kit,
                               fix='new master: station-hosted reset carrier stage (2-stage landing + carrier flop) added',
                               why_route=f'new master {top}: no closed view exists; the {base_kit} stage is instantiated '
                                         'unchanged; rfi/rfo and 3 reset flops are new')
    return s


def readme(s):
    return '\n'.join([f'# {s["name"]} (L2H-RSTFB 10-19, HBM d4g H.RST.FB)', '', s['structural_change'].split('  SAFE')[0], '',
                      'Bench: rtl/hbm_accel/die_glue/test/bench_rly_rfc.sh (Verilator 5.050): 6 instances chained rfi->rfo, '
                      'release age 3k at station k, immediate assertion, data / rso unchanged and independent of rfi; '
                      'mutants land1mut / combmut / nogatemut / datamut FAIL (witnesses in ' + WIT + ').', '',
                      '## SAFE-DESIGN checklist (owner 10-19)'] + [f'- {k}: {v}' for k, v in CHECKLIST]) + '\n'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = []
    for stem in USED:
        for rr in (False, True):
            s = make(stem, rr)
            (OUT / f'{s["name"]}.json').write_text(json.dumps(s, indent=1) + '\n')
            names.append(s['name'])
    (OUT / 'README.md').write_text(readme(make('48_we', False)).replace('hbfd_rly_48_we_rfc', 'hbfd_rly_<W>_<flow>_rfc / _rrfc'))
    print(' '.join(names))


if __name__ == '__main__':
    main()
