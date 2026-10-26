#!/usr/bin/env python3
"""A wider reader slot with facing source-bit groups, after r4 GPL divergence."""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
NAME = 'ot_s81_vm_x34_t_w542_1015_r5'


def main():
    spec = json.loads((ROOT / 'physical/ref_tile/ot_s81_vm_x34_t_w542_1015_r4/spec.json').read_text())
    pins = []
    for k in range(543):
        y = round(6.012 + .576 * k, 3)
        for bank in range(3):
            pins.append((f'b{bank}[{k}]', 0., round(y + .192 * bank, 3), 'M4'))
        pins.append((f'o_d[{k}]' if k < 542 else 'o_v', 86.4, round(y + .192, 3), 'M4'))
    for k in range(3):
        pins.append((f'bpar[{k}]', 0., round(330.012 + .576 * k, 3), 'M4'))
    pins += [('s_mark', 0., 332.316, 'M4'), ('fault', 86.4, 332.316, 'M4'),
             ('t_ck', 20.748, 345.6, 'M5'), ('t_rst_n', 64.812, 345.6, 'M5')]
    assert len(pins) == 2179 and len({p[0] for p in pins}) == len(pins)
    path = ROOT / 'physical/s81_vm_cap_1015/x34_t_r5_local_banks.tcl'
    path.write_text('# Three corresponding captured bank bits face each output bit; explicit wider physical slot.\n' + ''.join(
        'place_pin -pin_name {%s} -layer %s -location {%.3f %.3f} -pin_size {%s} -force_to_die_boundary\n' %
        (n, layer, x, y, '.192 .024' if layer == 'M4' else '.024 .192') for n, x, y, layer in pins))
    spec.update(name=NAME, io_tcl=str(path.relative_to(ROOT)), outline=dict(w=86.4, h=345.6, exact=True))
    spec['structural_change'] = 'r4 43.2x345.6 failed placement GPL-0305 before CTS. r5 doubles physical width to86.4um and aligns each west three-bank-bit group opposite its east output bit, supplying additional legal anchor/hold-cell rows and placement room. Same actual RTL, three banks, full count, fixed phases and latency. HB1 output/HB2 input sender/receiver pads and stricter0.55T output budget retained. Area-slot cost+0.01492992mm2 per leaf,+0.23887872mm2 for16 capture leaves. Native routing/timing and die adoption remain open.'
    spec['slot_change_request'] = dict(contract='S81 capture stream CDC reader local bit groups',
        version='r5-local-reader', old_outline_um=[43.2, 345.6], new_outline_um=[86.4, 345.6],
        extra_slot_area_um2_per_leaf=14929.92, replicas=16, extra_slot_area_mm2_total=.23887872,
        why='r4 narrow slot GPL-0305, r3 actual sender launch233.7ps; structural placement/hold-stage room and facing bit groups')
    spec['reroute_reason'] = dict(kind='slot_change', source='physical/ref_tile/ot_s81_vm_x34_t_w542_1015_r4/gate_result.json',
        why='Measured narrow-slot placement divergence; double width and explicit facing bank-bit/output pin groups, not unchanged retry')
    spec['job']['tag'] = 'localreader5'
    target = ROOT / 'tools/ref_tile/specs_s81vm_cap_local_banks_1015' / (NAME + '.json')
    target.write_text(json.dumps(spec, indent=1) + '\n')
    subprocess.run(['python3', str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(target)], check=True)


if __name__ == '__main__':
    main()
