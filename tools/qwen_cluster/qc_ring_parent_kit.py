#!/usr/bin/env python3
"""QW-CB16REG 10-20 (main line a): kit spec for the CB16 parent with hardened ring crossings (qfd_c_b16_rgx).

Inputs: physical/ref_tile/qfd_c_b16_fulln/spec.json (base kit), rtl/physical/qcluster/qfd_c_b16_rgx.sv (qc_ring_parent.py),
        results/arch/qw_cb16reg_1020/ring_tile_place_r0.json (ring_tile_place.py, OT_RTP_MODE=r0).
Writes: physical/qcluster/qfd_c_b16_rgx_sites.tsv (fullm sites minus the 138 soft ring bays), and
        physical/ref_tile/<NAME>/spec.json (+ then run `ref_tile.py gen`).
Children: fulln's A0 stand-ins / stations / xstn unchanged + 69 qfd_c_ring516/514 at the solved 43.2 origins / orientation,
views physical/ref_tile/qfd_c_ring<W>/views/qfd_c_ring<W> (exist only after the ring tiles close).
Clock: same 16 region roots; pre_cts_extra tools/qwen_cluster/cb16_km/cb16_ckkm.tcl balances the region clock pins (now
hard ring / station / A0 / xstn pins + scalar control FFs) to one latest arrival.
    qc_ring_parent_kit.py NAME [PLACE_JSON]
"""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
name = sys.argv[1]
place = json.loads((ROOT / (sys.argv[2] if len(sys.argv) > 2 else 'results/arch/qw_cb16reg_1020/ring_tile_place_r0.json')).read_text())
assert place['status'] in ('OPTIMAL', 'FEASIBLE'), place['status']
table = {t['name']: t for t in json.loads((ROOT / 'results/arch/qw_cb16reg_1020/rgx_crossings.json').read_text())}
s = json.loads((ROOT / 'physical/ref_tile/qfd_c_b16_fulln/spec.json').read_text())
sites_in = (ROOT / 'physical/qcluster/qfd_c_b16_fullm_sites.tsv').read_text().splitlines()
sites_out = ['# QW-CB16REG qc_ring_parent_kit.py: qfd_c_b16_fullm_sites.tsv minus the soft ring-half bays (crossings are hard qfd_c_ring tiles)']
dropped = 0
for l in sites_in:
    f = l.split('\t')
    if not l.startswith('#') and len(f) == 7 and f[0].startswith('u_fab.u_land_'):
        dropped += 1; continue
    sites_out.append(l)
assert dropped == 138, dropped
(ROOT / 'physical/qcluster/qfd_c_b16_rgx_sites.tsv').write_text('\n'.join(sites_out) + '\n')
s['name'] = name; s['top'] = 'qfd_c_b16_rgx'
s['sources'] = [x for x in s['sources'] if not x.endswith('qfd_c_b16_fullm.sv') and not x.endswith('qfd_c_land_k.sv')] + \
    ['rtl/physical/qcluster/qfd_c_land_k.sv', 'rtl/physical/qcluster/qfd_c_ring_t.sv', 'rtl/physical/qcluster/qfd_c_b16_rgx.sv']
s['orfs_vars']['OT_QC_SITES'] = 'physical/qcluster/qfd_c_b16_rgx_sites.tsv'
s['pre_cts_extra'] = ['tools/qwen_cluster/cb16_km/cb16_ckkm.tcl']
for r, p in sorted(place['tiles'].items()):
    n = r.split('u_land_', 1)[1]; W = table[n]['W']
    s['children'].append({'view': f'physical/ref_tile/qfd_c_ring{W}/views/qfd_c_ring{W}', 'count': 1, 'inst': r,
                          'at': p['at'], 'orient': p['orient'], 'at_exact': True})
exc = place.get('reach_excess_um', {})
s['structural_change'] = (
    "QW-CB16REG 10-20 main line (a): CB16 parent with every region crossing HARDENED -- 69 qfd_c_ring516/514 tiles (writer ring on "
    "the source region clock + reader incl. output register on the destination clock, one tile per crossing, 2 masters hardened once) "
    "replace the 138 soft ring halves (161k flops) of qfd_c_b16_fulln; each region root now reaches only hard-child clock pins "
    "(A0, stations, xstn, ring tiles) + the scalar control / reset FFs, balanced by cb16_ckkm.tcl.  Ring tiles placed by "
    "tools/qwen_cluster/ring_tile_place.py (CP-SAT, 43.2 lattice, writer anchors -> tile in face and tile out face -> reader anchors "
    f"<= 405 um planned; {len(exc)} crossings planned above 405 with repeaters: {exc}).  RTL qfd_c_b16_rgx.sv "
    "(qc_ring_parent.py) = qfd_c_b16_fullm with the soft pairs replaced; same ports / stations / A0 / xstn / reset trees / edges.  "
    "Why: fulln/fullnb/fullm within-region TT spread 410-813 ps, WNS -1.4..-1.7 ns after 10-16 h.  Prior: " + s['structural_change'][:600])
s['job'].update({'owner': 'Claude:QW-CB16REG', 'branch': 'claude/qw-cb16reg-1020', 'tag': 'rgx',
                 'purpose': 'MAIN (a) of QW-CB16REG: CB16 parent with hardened ring crossings (critical prefix qfd_c_b16: gate + coordinator review only, no submit)'})
d = ROOT / 'physical/ref_tile' / name; d.mkdir(parents=True, exist_ok=True)
(d / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
print(f'QC_RING_PARENT_KIT {name}: {len(place["tiles"])} ring tiles, {dropped} bays dropped, reach excess {exc}')
