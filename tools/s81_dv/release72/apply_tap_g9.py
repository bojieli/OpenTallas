#!/usr/bin/env python3
"""Bind exact CLOSED TAP MAIN bodies and module-specific frozen source closure."""
import argparse, hashlib, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'results/arch/s81_die72_1021/g9_assembly/tap_first_closed'

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', required=True, type=Path)
    ap.add_argument('--table', required=True, type=Path)
    a = ap.parse_args()
    packet = json.loads((BASE / 'binding.json').read_text())
    plan = json.loads(a.plan.read_text()); table = json.loads(a.table.read_text())
    assert not plan['facts'].get('tap_closed_binding'), 'TAP overlay already present'
    for master, hashes in packet['view_sha256'].items():
        for name, h in hashes.items():
            assert hashlib.sha256((ROOT / 'physical/ref_tile' / master / 'views' / master / name).read_bytes()).hexdigest() == h
        row = table['masters'][master]
        assert row['module'] == master and not row.get('view') and not row.get('params')
        row.update(ref='27ffa71c6', view='physical/ref_tile/'+master+'/views/'+master,
                   view_ref=packet['records'][master], params={},
                   view_note='Exact CLOSED MAIN172.8x108; frozen16 TAP-module closure only, RR source independent')
    # Keep the existing selected RR body explicit, then select only TAP modules
    # from the owner's literal extraction. No full successor RR file overrides it.
    sources = [
        ('8a495768f02316a7a8ad2e2bafef2f4d3741b741', 'rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr.sv', packet['preserved_RR_file_sha256']),
        ('869be1b5a', 'results/rtl/s81_eng_release_1021/selected_main_binding/frozen_tap_modules.sv', packet['frozen_source_sha256']),
        ('27ffa71c6', 'rtl/dsrom_sys/s81_dv/eng/ot_s81eng_reset3n32.sv', '89119ff17eb33ce5cea680f1c574e1d4ea12905f6e1cd47db6865c38a8142de8'),
        ('27ffa71c6', 'rtl/lib/ot_rst_relay_bounded32.sv', 'd3ba9c38d47d5868efdec0e81dbba096732613299aba3a2b4f2e4d4498204785')]
    for ref, path, h in sources:
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', ref+':'+path])
        if h: assert hashlib.sha256(raw).hexdigest() == h
        table.setdefault('rtl_refs', {}).setdefault(ref, []).append(path)
        table.setdefault('prefer', []).append(ref+'/'+path)
    for d in packet['defines']:
        if d not in table.setdefault('defines', []): table['defines'].append(d)
    placements = {r['instance']: r for r in packet['placements']}
    for b in plan['blocks']:
        if b['name'] not in placements: continue
        r = placements[b['name']]
        assert [b[k] for k in ('x','y','w','h')] == r['old_rect_um']
        assert all(v['offtrack'] == 0 for v in r['fullpincheck']['layers'].values())
        for k,v in zip(('x','y','w','h'), r['new_rect_um']): b[k] = v
    for link in plan['links']:
        for ep in link['e']:
            name = plan['blocks'][ep[0]]['name']
            if name not in placements: continue
            old = placements[name]['old_rect_um']; new = placements[name]['new_rect_um']
            ep[2] = round(new[0] + (ep[2]-old[0])/old[2]*new[2], 4)
            ep[3] = round(new[1] + (ep[3]-old[1])/old[3]*new[3], 4)
        for f in ('h','sp','s','L','station_dirs'): link.pop(f, None)
    plan['facts']['tap_closed_binding'] = packet
    plan['facts']['physical72']['routing'] = 'INVALIDATED_BY_EXACT_TAP_MAIN_GEOMETRY; fresh paths/actual pin projection required'
    a.plan.write_text(json.dumps(plan, indent=1)+'\n'); a.table.write_text(json.dumps(table, indent=1)+'\n')
    print('G9_TAP_BOUND16 exactMAIN source-module/pin/body contract; fresh paths/STA owed')

if __name__ == '__main__': main()
