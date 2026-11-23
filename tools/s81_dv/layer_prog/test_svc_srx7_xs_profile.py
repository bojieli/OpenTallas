"""S81-SVC-J9: service timing dates of the SRX 7 + OT_SVC_ENG_XS engine form (profile closing_allq_srx7_xs)."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lower_svc  # noqa: E402


def test_xs_profile_dates_on_the_rt2_calendar():
    base, srx7, xs = (lower_svc.SERVICE_TIMING[k] for k in ('closing_allq', 'closing_allq_srx7', 'closing_allq_srx7_xs'))
    assert (srx7['pio'] - base['pio'], srx7['kpv'] - base['kpv']) == (7, 7)
    # n = 9: scores +9, p feed on the next II=2 calendar slot +10, P.V +19 (svc_srx_lockstep --hcore --rt2-calendar)
    assert (xs['pio'] - base['pio'], xs['kpv'] - base['kpv']) == (10, 9)
    assert xs['engine_profile'] == 'closing' and xs['srx'] == 7 and xs['eng_xs'] == 2


def test_compiler_selects_the_xs_profile_from_the_die_defines():
    src = (HERE.parent / 'dv_layer_compile.py').read_text()
    assert "'OT_SVC_ENG_XS' in defines" in src and "expected += '_xs'" in src
    assert "'OT_SVC_NATIVE_RT2_CALENDAR' not in defines" in src
    choices = re.search(r"--svc-timing-profile', choices=\(([^)]*)\)", src).group(1)
    assert "'closing_allq_srx7_xs'" in choices
    assert "'closing_allq_cutk45'" in choices and "'closing_allq_srx7_xs_cutk45'" in choices
    assert "expected += '_cutk45'" in src


def test_cut_depth_profiles_add_the_rc15_dates():
    T = lower_svc.SERVICE_TIMING
    for a, b in (('closing_allq', 'closing_allq_cutk45'), ('closing_allq_srx7_xs', 'closing_allq_srx7_xs_cutk45')):
        # KA 4 + KR 5 = 9 stages each way: SM e rows +18 at the slice (PIO), P.V at the entry a further 2 x 9 (cut_lat)
        assert T[b]['pio'] - T[a]['pio'] == 18 and T[b]['kpv'] == T[a]['kpv'] and T[b]['cut'] == 9
        assert T[a].get('cut', 0) == 0
    src = (HERE / 'lower_svc.py').read_text()
    assert src.count("PV_LAT + 2 * self.timing.get('cut', 0)") == 4


def test_engine_tag_delay_matches_the_two_kept_stages():
    rtl = (HERE.parents[2] / 'rtl/dsrom_sys/s81_svc/ot_s81_svc_attn_s.sv').read_text()
    assert re.search(r"`ifdef OT_SVC_ENG_XS\s+localparam integer XSD = 2;\s+`else\s+localparam integer XSD = 0;", rtl)
    assert rtl.count('+ BXT + XSD') == 2
