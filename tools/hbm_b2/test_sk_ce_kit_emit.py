"""DIE-HBM-61/RTL-TAILX 11-03: sk_ce_kit.py --emit-rest must reproduce the committed tail rest RTL byte for byte,
and the RE-FORM form (REFORM=1 default: operand register, two-stage max4, registered phase/index, c12 LAT-6 units, SKL sink launch) must be present."""
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
    assert "g_operand_q" in t and "g_c12" in t and "P3=MAX+1+MXS," in t and "age==MAX+1)for" in t
    assert "D(LMU+OPQ)) mt" in t and "D(LEU+OPQ)) et" in t and "D(LDU+OPQ)) dt" in t
    assert "age >= 10'(SKL) && wrap" in t and "parameter integer L = SKL + SDIV + CAP + 2" in t
    assert ".L7X(1)) add(" in t and ".L7X(1),.NREP(8),.TQ(1)) exp_(" in t
    assert "g_launch_q" in t and "P1=1+LDQ," in t and "g_onehot_q" in t and "oh_q<=onehot(i_nx)" in t and "ti_q<=t_sel" in t

def test_recipes_carry_c12_files():
    import importlib.util
    spec = importlib.util.spec_from_file_location("sk_ce_kit", REPO / "tools/hbm_b2/sk_ce_kit.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    r = m.recipes("land1-cap3")
    for core in ("ot_hbm_hc_root_static__tailx_rest__v4f4566", "ot_hbm_hc_root_static__tailx_rest__v6bc7f2"):
        files = r[core]["files"]
        for f in m.C12_FILES:
            assert (m.C12 + f) in files and (REPO / m.C12 / f).is_file()

def test_committed_recipes_b2_carry_c12_files():
    # KIT-WAVE d44v attempt_5 GEN_LINT: kits are built from recipes_b2.json, which must list the c12 files too.
    import json
    sys.path.insert(0, str(REPO / "tools/hbm_b2"))
    import sk_ce_kit
    b2 = json.loads((REPO / "physical/die_plan/hbm_arch_cores/recipes_b2.json").read_text())
    for m in ("ot_hbm_hc_root_static__tailx_rest__v6bc7f2", "ot_hbm_hc_root_static__tailx_rest__v4f4566"):
        for f in sk_ce_kit.C12_FILES:
            assert sk_ce_kit.C12 + f in b2[m]["files"], (m, f)
