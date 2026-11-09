"""The calendar and the DS composer take the Engram lookup dates from lower_eng.LAT (S81-TRANSPORT-FIX 3b)."""
import importlib.util
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_engram_terms_follow_the_compiler_table():
    lat = _load('lower_eng_t', TOOLS / 'layer_prog/lower_eng.py').LAT
    assert (lat['return_age'], lat['ii']) == (1536, 1600)
    cal = _load('dv_mu_calendar_phys_t', TOOLS / 'dv_mu_calendar_phys.py')
    assert (cal.REL241['eng_age'], cal.REL241['eng_ii']) == (lat['return_age'], lat['ii'])
    comp = _load('compose_tok_ds_t', TOOLS / 'tokfunc/compose_tok_ds.py')
    assert comp.ENG_AGE == lat['return_age']
