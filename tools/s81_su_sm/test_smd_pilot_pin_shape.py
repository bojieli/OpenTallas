"""S81-SVC-9: regenerated SMD local2 pilot kits keep the rst_in pin vertical on vertical M5 and clear of the PDN stripes."""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'physical/die_plan/hbm_arch_cores'), str(ROOT / 'tools/die_plan')]


def load(rel):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _check(pilot):
    gen = load('physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py')
    pins = pilot.pin_table()
    text, rows = gen.declared_source_io_tcl(pins, pilot.SIDE, pilot.SIDE, 'pilot', {'clk'}, {'rst_in'})
    line = next(l for l in text.splitlines() if 'pin_name {rst_in}' in l)
    m = re.search(r'-layer (\S+) -location \{(\S+) (\S+)\} -pin_size \{(\S+) (\S+)\}', line)
    layer, x, y, sx, sy = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))
    assert layer == 'M5'
    assert sx < sy                                     # vertical shape on vertical M5 (DRT-0074 on the horizontal 0.192 x 0.024)
    assert abs((x - 0.024) / 0.048 - round((x - 0.024) / 0.048)) < 1e-6   # on the M5 track
    # x is off the M5 stripe pair at 75.696 +- (width 0.12 + spacing 0.072) pitch 4.32 offset 2.064
    assert abs(x - 75.696) > 0.5
    row = next(r for r in rows if r['bus'] == 'rst_in' or r.get('bit') is None and r['x'] == x)
    assert row.get('declared_native_shape') is True


def test_local2_pilot_rst_pin():
    _check(load('tools/s81_su_sm/fold2_divide_local2_pilot.py'))


def test_local_pilot_rst_pin():
    _check(load('tools/s81_su_sm/fold2_divide_local_pilot.py'))
