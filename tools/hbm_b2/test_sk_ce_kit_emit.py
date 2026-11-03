"""DIE-HBM-61/RTL-TAILX 11-03: sk_ce_kit.py --emit-rest must reproduce the committed tail rest RTL byte for byte,
and the RE-FORM form (REFORM=1 default: operand register, two-stage max4, registered phase/index) must be present."""
import subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
RTL = REPO / "rtl/hbm_accel/cores_split/sk_en_q4/ot_hbm_hc_tail_rest_core_ce.sv"

def test_emit_rest_matches_committed():
    out = subprocess.run([sys.executable, str(REPO / "tools/hbm_b2/sk_ce_kit.py"), "--emit-rest"],
                         capture_output=True, text=True, check=True).stdout
    assert out == RTL.read_text()

def test_reform_default_on():
    t = RTL.read_text()
    assert "parameter integer REFORM=1," in t and "parameter integer REFORM = 1," in t
    assert "g_operand_q" in t and "MAX=55+REFORM,P3=56+2*REFORM," in t and "age==MAX+1)for" in t
    assert "D(3+OPQ)) mt" in t and "D(49+OPQ)) et" in t and "D(19+OPQ)) dt" in t
