"""DIE-HEAD-33: head_lep_pair_kit.add_land_decl appends the land_slots declaration to the core face_guard call for both
the pre-d379a4b741c one-line form (byte-identical to the former exact-string hook) and the current main form."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import head_lep_pair_kit as K  # noqa: E402

OLD = 'r = FG.guard(Path(net).read_text(), fz["design"], skip_re=skip, pins=pins)'


def test_old_form_byte_identical_to_former_hook():
    text = "x = 1\n    " + OLD + "\nr['skip_re'] = skip\n"
    former = text.replace(OLD, OLD[:-1] + ', land=FG.kit_land(kd / "land_slots.json"))')
    assert K.add_land_decl(text) == former


def test_current_main_face_guard_core():
    src = (ROOT / "physical/die_plan/hbm_arch_cores/face_guard_core.py").read_text()
    out = K.add_land_decl(src)
    assert out.count(K.LAND_ARG) == 1
    assert "dead=FG.kit_dead_list(kd), " + K.LAND_ARG + ")" in out
    assert "straps=FG.kit_strap_list(kd)" in out
    # only the guard call changed
    assert out.replace(", " + K.LAND_ARG, "", 1) == src
    compile(out, "face_guard_core.py", "exec")


def test_fail_closed():
    with pytest.raises(SystemExit):
        K.add_land_decl("no call here\n")
    with pytest.raises(SystemExit):
        K.add_land_decl(OLD + "\n" + OLD + "\n")
    with pytest.raises(SystemExit):
        K.add_land_decl(K.add_land_decl(OLD + "\n"))
    with pytest.raises(SystemExit):
        K.add_land_decl("r = FG.guard(a, (b\n")
