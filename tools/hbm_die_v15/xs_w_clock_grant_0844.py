"""Derive the real XS W-clock repin grant from exported LEF and source-pinned parent pins."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from case_reach import lef, xf

ROOT = Path(__file__).resolve().parents[2]
LF = ROOT / 'physical/ref_tile/smh_xs_ref_p45m/views/ot_hbm_accel_smh_xs/ot_hbm_accel_smh_xs.lef'
PP = 'physical/ref_tile_specs/smh/smh_tile_rp4c_pins.tcl'


def main():
    view = lef(LF)['ot_hbm_accel_smh_xs']
    assert (view['w'], view['h']) == (302.4, 157.68), 'Use exported LEF, not stale spec height155.544'
    parent = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'e15f1ee76:' + PP])
    west = [(n, float(y)) for n, layer, x, y in re.findall(
        r'place_pin -pin_name \{([^}]+)\} -layer (\w+) -location \{([\d.]+) ([\d.]+)\}', parent.decode())
        if layer == 'M4' and float(x) == 0]
    # Read layers separately: the common LEF reader supplies exact pin centres and USE.
    layers = {n: re.search(r'LAYER\s+(\w+)', body).group(1) for n, body in re.findall(
        r'\n\s*PIN (\S+)(.*?)\n\s*END \1', LF.read_text(), re.S)}
    children = []
    for i, (y, orient, port, old) in enumerate([(1071.36, 'R0', 'clk_hard[0]', 1229.004),
                                               (298.104, 'MX', 'clk_hard[5]', 298.140)]):
        placement = dict(x=25.92, y=y, orient=orient)
        new = round(xf(placement, view['w'], view['h'], 0, 77.772)[1], 3)
        checked = 0
        for name, (px, py) in view['pins'].items():
            if name == 'clk' or view['uses'][name] in ('POWER', 'GROUND'):
                continue
            layer = layers[name]
            assert layer in ('M4', 'M5'), (name, layer)
            xg, yg = xf(placement, view['w'], view['h'], px, py)
            coordinate = yg if layer == 'M4' else xg
            residual = abs((coordinate - .012) / .048 - round((coordinate - .012) / .048)) * .048
            assert residual < 1e-6, (name, orient, coordinate, residual)
            checked += 1
        clearance = min(abs(py - new) for name, py in west if name != port)
        assert clearance > .048
        assert abs((new - .012) / .048 - round((new - .012) / .048)) < 1e-6
        children.append(dict(instance=f'u.g_lf[{i}].u_lh.u_xs', origin=[25.92, y], orient=orient,
                             parent_clock=port, parent_old_y=old, parent_new_y=new,
                             parent_clock_delta_y=round(new - old, 3), unchanged_signal_pins_checked=checked,
                             parent_nearest_other_W_pin_um=clearance, boundary_stub_um=25.92,
                             conservative_pin_center_stub_um=25.962))
    west_pins = [abs(py - 77.772) for name, (px, py) in view['pins'].items()
                 if name != 'clk' and layers[name] == 'M4' and px < .1]
    assert min(west_pins) > .048
    result = dict(schema='opentallas.hbm.xs_w_clock_grant.v1',
                  status='APPROVED_REPIN_CANDIDATE_REQUIRES_REAL_REROUTE', reroute_reason='die_window',
                  measured_cause='149um raw clock stub; TT slew269.9ps against120ps gate',
                  source_parent='e15f1ee76', source_view=str(LF.relative_to(ROOT)),
                  source_view_sha256=hashlib.sha256(LF.read_bytes()).hexdigest(), parent_pin_file=PP,
                  parent_pin_file_sha256=hashlib.sha256(parent).hexdigest(), outline_um=[view['w'], view['h']],
                  clock_grant=dict(port='clk', face='W', layer='M4', centre_um=77.772,
                                   span_um=[77.760, 77.784], x_span_um=[0, .084]),
                  nearest_other_child_W_pin_um=min(west_pins), children=children,
                  preserved='RTL, actual outline, child origins/orientations and every non-clock signal pin. PG unchanged.',
                  qualification='GEOMETRY_ONLY. Parent clocks move atomically with actual rerouted XS. Require native slew, TT, FF, DRC0; no inherited-view alias. Frozen d4 unchanged.')
    output = ROOT / 'results/arch/hbm_die_v16/xs_w_clock_grant_0844.json'
    output.write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
