"""hcp_sys1 split wrapper: the generator emits the same u_core parameters as the committed wrapper (hcpom4 form)."""
import importlib.util, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
WRAP = REPO / 'rtl/hbm_accel/cores_split/ot_hbm_hc_root_static/ot_hbm_hc_root_hcp_sys1_core.sv'


def _gen():
    spec = importlib.util.spec_from_file_location('build_split_tops', HERE / 'build_split_tops.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_hcp_sys1_params_match_wrapper():
    m = _gen()
    specs = [v for k, v in vars(m).items() if isinstance(v, dict) and 'hc_hcp_sys1' in v]
    assert specs, 'hc_hcp_sys1 spec table not found'
    mod, par = specs[0]['hc_hcp_sys1']['rtl']['u_core']
    assert mod == 'ot_hdc_v41x_hcp_sys1_static'
    for p in ('.SM_LAT(4)', '.OM_LAT(5)', '.NF_TIED(1)', '.CMD_RST(1)'):
        assert p in par
    if WRAP.exists():
        w = re.search(r'ot_hdc_v41x_hcp_sys1_static\s*(#\(.*\))\s*u_core', WRAP.read_text()).group(1)
        assert w.replace(' ', '') == par.replace(' ', '')
