"""HBMc/CHAIN 10-22: [0:0] view pins carry the scalar 1-bit contract port (col_su.pw_we / collar c_fault fix)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))


def _key():
    import importlib
    try:
        return importlib.import_module('die_case_v16').view_pin_key
    except Exception:          # heavy imports unavailable: exec the pure function source
        import re
        src = (Path(__file__).resolve().parent / 'die_case_v16.py').read_text()
        i = src.index('def view_pin_key('); j = src.index('\ndef ', i + 1)
        ns = {'re': re}; exec(src[i:j], ns)
        return ns['view_pin_key']


def test_zero_zero_port_maps_to_scalar():
    k = _key()
    assert k('pw_we[0]', {'pw_we': 1}, {'pw_we[0]'}) == 'pw_we'
    assert k('c_fault[0]', {'c_fault': 1}, {'c_fault[0]', 'pw_we[0]'}) == 'c_fault'


def test_real_buses_and_scalars_unchanged():
    k = _key()
    assert k('pw_we[0]', {'pw_we': 2}, {'pw_we[0]', 'pw_we[1]'}) == 'pw_we[0]'
    assert k('c_fault[3]', {'c_fault': 5}, set()) == 'c_fault[3]'
    assert k('rst_n', {'rst_n': 1}, {'rst_n'}) == 'rst_n'
    assert k('x[0]', {}, {'x[0]'}) == 'x[0]'
