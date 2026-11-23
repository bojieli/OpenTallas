"""S81-SVC-J9: service timing dates of the SRX 7 + OT_SVC_ENG_XS engine form (profile closing_allq_srx7_xs)."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lower_svc  # noqa: E402


def test_xs_profile_moves_pio_and_kpv_by_srx_plus_two():
    base, srx7, xs = (lower_svc.SERVICE_TIMING[k] for k in ('closing_allq', 'closing_allq_srx7', 'closing_allq_srx7_xs'))
    assert (srx7['pio'] - base['pio'], srx7['kpv'] - base['kpv']) == (7, 7)
    assert (xs['pio'] - base['pio'], xs['kpv'] - base['kpv']) == (9, 9)
    assert xs['engine_profile'] == 'closing' and xs['srx'] == 7 and xs['eng_xs'] == 2


def test_compiler_selects_the_xs_profile_from_the_die_defines():
    src = (HERE.parent / 'dv_layer_compile.py').read_text()
    assert "'OT_SVC_ENG_XS' in defines" in src and "expected += '_xs'" in src
    choices = re.search(r"--svc-timing-profile', choices=\(([^)]*)\)", src).group(1)
    assert "'closing_allq_srx7_xs'" in choices


def test_engine_tag_delay_matches_the_two_kept_stages():
    rtl = (HERE.parents[2] / 'rtl/dsrom_sys/s81_svc/ot_s81_svc_attn_s.sv').read_text()
    assert re.search(r"`ifdef OT_SVC_ENG_XS\s+localparam integer XSD = 2;\s+`else\s+localparam integer XSD = 0;", rtl)
    assert rtl.count('+ BXT + XSD') == 2
