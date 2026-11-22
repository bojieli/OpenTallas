"""FLOW-STRIPBODY-1121: strip pieces of a strip / body split (type_split <type>__strip_<face>) inherit the base type wave env"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K  # noqa: E402


def test_piece_base():
    assert K.piece_base("dsdv_slice_lepe_mu_C__t1__strip_S") == "dsdv_slice_lepe_mu_C__t1"
    assert K.piece_base("dsdv_slice_lepe_mu_C__t1") == "dsdv_slice_lepe_mu_C__t1"
    assert K.piece_base("x__strip_Q") == "x__strip_Q"


def test_strip_piece_inherits_item_env_unless_it_has_its_own():
    d = {"die_gen_env": {"OT_D": "0"}, "item_env": {"a__t1": {"OT_X": "1"}, "b__t1__strip_N": {"OT_X": "2"}, "c_*": {"OT_G": "g"}}}
    assert K.item_env(d, "a__t1__strip_S") == {"OT_D": "0", "OT_X": "1"}
    assert K.item_env(d, "b__t1__strip_N") == {"OT_D": "0", "OT_X": "2"}
    assert K.item_env(d, "c_t2__strip_W") == {"OT_D": "0", "OT_G": "g"}
    assert K.item_env(d, "z__strip_E") == {"OT_D": "0"}
