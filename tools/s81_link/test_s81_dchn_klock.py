"""SERDES-DCHN-KLOCK-J9: the tree flat_lp carries exactly the generated KLOCK option, the option is idempotent and
define-off identical, and lp.py gen() applies it (so a regen keeps it)."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "s81_link"))
import s81_dchn_klock as K  # noqa: E402

FLAT = ROOT / "rtl/dsrom_sys/s81_link/lp/ot_s81_kp4_dec_native_flat_lp.sv"


def test_tree_file_is_generated_form():
    tree = FLAT.read_text()
    base = K.strip_klock_option(tree)
    assert K.FLAG not in base
    assert K.add_klock_option(base) == tree          # byte for byte: define-on text = transform(define-off text)
    assert K.add_klock_option(tree) == tree          # idempotent (a regen post-pass keeps the file)


def test_define_off_branch_is_original():
    tree = FLAT.read_text()
    assert tree.count("`ifdef OT_S81_DCHN_KLOCK\n") == len(K.SIGS)
    base = K.strip_klock_option(tree)
    for dst, src, _ in K.SIGS:
        assert base.count(f"    assign {dst} = {src};\n") == 1


def test_lockup_is_negedge_same_clock():
    tree = FLAT.read_text()
    for dst, src, _ in K.SIGS:
        assert f"always @(negedge ck_chn) {dst}__lk <= {src};" in tree
        assert f"assign {dst} = {dst}__lk;" in tree
    assert re.search(r"ot_s81_kp4_dchn u_chn \(\.clk\(ck_chn\)", tree)


def test_lp_gen_applies_hook():
    src = (ROOT / "tools/landed_parent/lp.py").read_text()
    assert "add_klock_option" in src and 'top_lp == "ot_s81_kp4_dec_native_flat_lp"' in src


def test_template_change_refused():
    tree = K.strip_klock_option(FLAT.read_text()).replace("    assign k_lo__l_chn = lpl_2_o;\n", "")
    try:
        K.add_klock_option(tree)
    except ValueError:
        return
    raise AssertionError("missing landing output must be refused")
