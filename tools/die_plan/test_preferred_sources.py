"""Missing explicitly selected PHY definitions cannot silently fall back to a different ABI."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind
import bind_elab as E


def test_missing_preferred_phy_rejects_valid_alternate_before_index(tmp_path, monkeypatch):
    alternate = tmp_path / 'other.v'
    alternate.write_text('module phy(input wrong_abi); endmodule\n')
    top = tmp_path / 'top.v'
    top.write_text('module top(input clk);\n phy u_phy (.clk(clk));\nendmodule\n')
    missing = tmp_path / 'physical' / 'phy_bb.v'
    idx = {'phy': [str(alternate)]}
    with pytest.raises(E.ElabError, match='preferred HDL source missing'):
        bind.kit_closure(['phy'], idx, [str(missing)])
    def no_index(*args):
        raise AssertionError('source index must not be built with a missing explicit preferred file')
    monkeypatch.setattr(E, 'module_index', no_index)
    with pytest.raises(E.ElabError, match='phy_bb.v'):
        E.plan_sources({'netlist': ['top.v'], 'prefer': [str(missing)]}, tmp_path)


def test_present_preference_or_ordinary_fallback_remains_unchanged(tmp_path):
    alternate = tmp_path / 'other.v'; preferred = tmp_path / 'phy_bb.v'
    alternate.write_text('module phy(input wrong_abi); endmodule\n')
    preferred.write_text('module phy(input clk); endmodule\n')
    idx = {'phy': [str(alternate), str(preferred)]}
    picks = {}
    files, missing, macros = bind.kit_closure(['phy'], idx, [str(preferred)], picks)
    assert files == [str(preferred)] and not missing and not macros
    assert picks == {'phy': str(preferred)}
    assert bind.kit_closure(['phy'], idx, [])[0] == [str(alternate)]
    # Legacy optional search roots have no effect when they are absent.
    assert bind.kit_closure(['phy'], idx, [str(tmp_path / 'absent_library')])[0] == [str(alternate)]
