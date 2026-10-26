#!/usr/bin/env python3
"""Place each x34 serial input opposite its three actual bank destinations.

The r3 automatic assignment leaves corresponding bits up to 151.788 um
apart in a 43.2 um wide leaf. This changes only the assigned pin positions;
RTL, bank count, fixed clock phases, latency, and the slot are unchanged.
"""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = 'ot_s81_vm_x34_s_w542_1015_r3'
NAME = 'ot_s81_vm_x34_s_w542_1015_r4'


def main():
    spec = json.loads((ROOT / 'physical/ref_tile' / BASE / 'spec.json').read_text())
    pins = []
    for k in range(543):
        y = round(6.012 + .576 * k, 3)
        pins.append(dict(port=f's_d[{k}]' if k < 542 else 's_v', x=0., y=round(y + .192, 3), layer='M4'))
        for bank in range(3):
            pins.append(dict(port=f'b{bank}[{k}]', x=43.2, y=round(y + .192 * bank, 3), layer='M4'))
    for k in range(3):
        pins.append(dict(port=f'bpar[{k}]', x=43.2, y=round(330.012 + .576 * k, 3), layer='M4'))
    pins.append(dict(port='s_mark', x=43.2, y=332.316, layer='M4'))
    pins += [dict(port='s_ck', x=8.796, y=345.6, layer='M5'), dict(port='s_rst_n', x=34.428, y=345.6, layer='M5')]
    assert len(pins) == 2178 and len({p['port'] for p in pins}) == len(pins)
    path = ROOT / 'physical/s81_vm_cap_1015/x34_s_r4_local_banks.tcl'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('# Source-bit aligned input to three ICG bank destinations; slot 43.2 x 345.6 um.\n' + ''.join(
        'place_pin -pin_name {%s} -layer %s -location {%.3f %.3f} -pin_size {%s} -force_to_die_boundary\n' %
        (p['port'], p['layer'], p['x'], p['y'], '.192 .024' if p['layer'] == 'M4' else '.024 .192') for p in pins))
    spec['name'] = NAME
    spec['io_tcl'] = str(path.relative_to(ROOT))
    spec['structural_change'] = 'Corresponding s_d[k] and b0/b1/b2[k] pins occupy the same 0.384 um vertical band. Actual r3 LEF fanout legs max151.788um/mean77.824um become at most43.392um. Same actual NAT=1 RTL, three banks, clocks, 43.2x345.6 outline, zero cycles. Native r3 serial capture223.6ps on77pins fails190ps obligation; r4 qualification remains open.'
    spec['reroute_reason'] = dict(kind='pin_register', cell='ot_s81_vm_x34_s', capture_ps=223.6,
        source='results/physical/s81_vm_takeover_0802/native_audit.json',
        fix='Explicit source-bit aligned facing pins replace automatic bus ordering; same slot and source.')
    spec['job']['branch'] = 'codex/takeover-s81-vm-0802'
    spec['job']['tag'] = 'localbanks4'
    target = ROOT / 'tools/ref_tile/specs_s81vm_cap_local_banks_1015' / (NAME + '.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(spec, indent=1) + '\n')
    subprocess.run(['python3', str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(target)], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
