import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "physical/common_flow"))
from const_dff_keep import selected, verify, CELL


def fixture():
    return dict(modules=dict(t=dict(netnames=dict(q=dict(bits=[4])), cells=dict(
        capture=dict(type="$_DFF_P_", attributes=dict(keep="1"),
                     port_directions=dict(C="input", D="input", Q="output"),
                     connections=dict(C=[2], D=["0"], Q=[4])))))), dict(captures=[dict(module="t", wire="q", bits=[0])])


def test_preserves_original_state_clock_and_real_cell_polarity():
    design, spec = fixture()
    rows = selected(design, spec)
    mapped = copy.deepcopy(design)
    cell = mapped["modules"]["t"]["cells"]["capture"]
    cell.update(type=CELL, connections=dict(CLK=[2], D=["1"], QN=[4]))
    verify(mapped, rows)
    cell["connections"]["CLK"] = [9]
    with pytest.raises(ValueError, match="clock or polarity"):
        verify(mapped, rows)


def test_cannot_create_state_for_a_constant_output_without_original_ff():
    design, spec = fixture()
    design["modules"]["t"]["cells"] = {}
    design["modules"]["t"]["netnames"]["q"]["bits"] = ["0"]
    with pytest.raises(ValueError, match="existing FF driver"):
        selected(design, spec)


def test_never_preserves_nonconstant_or_reset_state_by_this_hook():
    design, spec = fixture()
    design["modules"]["t"]["cells"]["capture"]["connections"]["D"] = [3]
    with pytest.raises(ValueError, match="constant-D"):
        selected(design, spec)
    design, spec = fixture()
    design["modules"]["t"]["cells"]["capture"]["type"] = "$_DFF_PN0_"
    with pytest.raises(ValueError, match="plain DFFs"):
        selected(design, spec)


def test_distinct_contract_outputs_cannot_silently_share_one_ff():
    design, spec = fixture()
    design["modules"]["t"]["netnames"]["alias"] = dict(bits=[4])
    spec["captures"].append(dict(module="t", wire="alias", bits=[0]))
    with pytest.raises(ValueError, match="shared by target bits"):
        selected(design, spec)
