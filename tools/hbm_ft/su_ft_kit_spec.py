#!/usr/bin/env python3
"""FT-HBM-SU: ref_tile spec of the SU pgslice ft kit, derived TOP-DOWN from the die slot and the light kit.

Base: physical/ref_tile/hbm_su_pgslice_lg_light_d4g/spec.json (claude/hbm-pglg-d4h-1021; landed-region parent
ot_hbm_su_static_pgslice_rgf_lp, 32 KIND0 leaves + 32 CLOSED bank6_clock banks, 5 regions R0|R1|S|R2|R3).
Changes (nothing else):
  outline   = the die slot of su_<q><g> (r18h5 insts.tsv: 1797.12 x 2825.28; the light kit's 1235.52 x 3045.6 does not fit)
  children  = re-laid for that outline: 3 pair columns (KIND0 + 21.6 + bank) at x0 = 43.2 / 626.4 / 1209.6 (21.6 lattice),
              3 pair rows per region at a 172.8 pitch (21.6 channels), regions R0 R1 | S band 1058.4-1728 | R2 R3;
              each pair keeps its KIND0-left / bank-right adjacency and region; the 9th slot of a region is left empty
              (glue).  x on a 21.6 lattice (child pins <= M5: site/row/M1-M5 tracks align), y on 43.2.  Repeater/register
              sites: the 41-45 um column gaps, the 21.6 row channels and the 670-um S band, max hard span
              over a bank 380 um (< 450 repeater pitch)
  pins      = the light kit's W/E functional ranges moved with the S band (-118.8 um); region clock pins to the region
              centres; ft ports added at the FT-TOOL die-aligned ranges (placed on M8/M9 by the pushdown pin hook)
  clocks    = + ck_ft (stream 833.333 ps = 3/4 of the 1111.111 ps serial kit period) domain "ft" with every ft port + rs_ft
  layers    = PG top M7 (pins, unchanged), signals M2-M7; ft nets M8/M9 in the corridors only (spec "ft" contract)
  top       = ot_hbm_su_static_pgslice_rgf_lp__<v> (su_ft_kit.py: base module + fenced ft ports/stations, check PASS)

    su_ft_kit_spec.py --base BASE/spec.json --ftspec PILOT.ftspec.json --variant-sv V.sv --kit-dir physical/ref_tile/<kit>
"""
import argparse, json, os

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--base', required=True); ap.add_argument('--ftspec', required=True)
ap.add_argument('--variant-sv', required=True); ap.add_argument('--kit-dir', required=True)
ap.add_argument('--name', default='hbm_su_pgslice_lg_ft_d4g')
a = ap.parse_args()
S = json.load(open(a.base)); F = json.load(open(a.ftspec))
W, H = F['outline']
assert (W, H) == (1797.12, 2825.28), (W, H)
d = os.path.dirname(a.ftspec); v = F['variant']
DY = -129.6                                           # S band 1404..1641.6 (light) -> 1058.4..1728: centre -129.6
XP = [43.2, 626.4, 1209.6]                            # pair column origins (KIND0); bank at +172.8
REG_ROWS = {'r0': [43.2, 216.0, 388.8], 'r1': [561.6, 734.4, 907.2],          # 172.8 pitch (21.6 channels, as the
            'r2': [1728.0, 1900.8, 2073.6], 'r3': [2246.4, 2419.2, 2592.0]}     # light kit), y on the 43.2 lattice
EMPTY = {'r0': (2, 2), 'r1': (2, 2), 'r2': (0, 2), 'r3': (0, 2)}   # (row, col) left for glue, towards the S band / E face

kids = {c['inst']: c for c in S['children']}
children = []
for r, ys in REG_ROWS.items():
    slots = [(i, j) for i in range(3) for j in range(3) if (i, j) != EMPTY[r]]
    # KIND0 u_ln_<r>_k pairs with bank u_bk_<r>_k (light kit: same row, KIND0 left of its bank)
    for k, (i, j) in enumerate(slots):
        ln, bk = kids[f'u_ln_{r}_{k}'], kids[f'u_bk_{r}_{k}']
        children.append(dict(ln, at=[XP[j], ys[i]], orient='R0'))
        children.append(dict(bk, at=[round(XP[j] + 172.8, 4), ys[i]], orient='R0'))
assert len(children) == 64 and sorted(c['inst'] for c in children) == sorted(kids)

s = json.loads(json.dumps(S))
s['name'] = a.name
s['top'] = v
s['sources'] = [a.variant_sv] + [x for x in S['sources'] if not x.endswith('ot_hbm_su_static_pgslice_rgf_lp.sv')] + \
               ['rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']
s['outline'] = dict(w=W, h=H, exact=True)
s['child_lattice_um'] = 21.6
s['children'] = children
s.pop('slot_change_request', None)
s['slot_basis'] = ('FT-HBM-SU 10-23: outline = r18h5 die slot su_<q><g> (1797.12 x 2825.28, insts.tsv), not grown: '
                   'children re-laid 3 pair columns x 12 pair rows + S band')
pr = {}
for p, (lo, hi) in S['pin_ranges'].items():
    if p in ('ck_r0', 'ck_r3'):
        pr[p] = [898.56, 898.76]
    elif p == 'ck_r1':
        pr[p] = [734.4, 734.6]
    elif p == 'ck_r2':
        pr[p] = [1987.2, 1987.4]
    else:
        pr[p] = [round(lo + DY, 3), round(hi + DY, 3)]
pins = {f: list(ps) for f, ps in S['pins'].items()}
fti, fto = ['ck_ft', 'rs_ft'], []
for q in F['ports']:
    pins.setdefault(q['face'], []).append(q['name'])
    pr[q['name']] = [round(max(q['lo'], 0.0), 3), round(q['hi'], 3)]
    (fti if q['dir'] == 'input' else fto).append(q['name'])
pins['W'] += ['ck_ft', 'rs_ft']
pr['ck_ft'] = [1760.0, 1760.2]; pr['rs_ft'] = [1760.6, 1760.8]
s['pins'] = pins; s['pin_ranges'] = pr
s['clock_ports'] = S['clock_ports'] + ['ck_ft']
s['clock_entry_domains'] = dict(S['clock_entry_domains'], ft=dict(ratio=[3, 4], ports=['ck_ft'], inputs=fti, outputs=fto))
s['reset_ports'] = S['reset_ports'] + ['rs_ft']
s['ft'] = dict(ftspec=a.ftspec, fastroute_tcl=f'{d}/{v}.fastroute.tcl', pins_tcl=f'{d}/{v}.pins.tcl',
               audit_tcl=f'{d}/{v}.ft_audit.tcl', base_top='ot_hbm_su_static_pgslice_rgf_lp',
               base_kit='rtl/hbm_accel/generic/adapters/static_su/top/lp/ot_hbm_su_static_pgslice_rgf_lp.sv')
s['ft_note'] = (f'FT-HBM-SU 10-23 pilot = su_SW3 gain lanes on the stream die clock: {len(F["paths"])} ft paths, '
                f'{F["ft_bits"]} b, {F["ft_bit_stages"]} station flops (ot_hbm_rly, the die relay function) on ck_ft; '
                'ft ports are the FT-TOOL plan_v2 die-aligned ranges (equal die offsets at the neighbours); '
                'base logic byte-identical (tools/hbm_ft/su_ft_kit.py check)')
j = s['job']
j.update(owner='Claude:FT-HBM-SU', branch='claude/ft-hbm-su-1023', tag='f1',
         purpose='HBM r18h5 SU pgslice FEEDTHROUGH pilot (FT-PLAN 10-23): light landed-region slice re-laid in the die slot '
                 '1797.12 x 2825.28 + su_SW3 gain/stream ft lanes on M8/M9 (in+out registered, <= 1.0 mm hops), '
                 'PG M7, signals M2-M7',
         record_to=f'results/rtl/ref_tile/{a.name}', views_to=f'physical/ref_tile/{a.name}/views')
j['extra_paths'] = sorted(set(j.get('extra_paths', [])) | {d, 'tools/hbm_ft', 'rtl/hbm_accel/die_glue/ot_hbm_rly.sv',
                                                           'rtl/lib/ot_rst_relay.sv', 'rtl/hbm_accel/generic/adapters/static_su/top/lp'})
os.makedirs(a.kit_dir, exist_ok=True)
json.dump(s, open(os.path.join(a.kit_dir, 'spec.json'), 'w'), indent=1)
print(os.path.join(a.kit_dir, 'spec.json'), len(children), 'children', len(F['ports']), 'ft ports')
