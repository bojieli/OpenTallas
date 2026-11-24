"""STB-COMMON 11-24 (S81-SERDES-TAPSKEW): plan clock.stb_common -> OT_STB_COMMON exports (default off)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G  # noqa: E402


def test_absent_or_false_is_off():
    assert G.stb_common_exports({}) == []
    assert G.stb_common_exports({"clock": {"stb_common": False}}) == []


def test_true_and_dict():
    assert "export OT_STB_COMMON = 1" in G.stb_common_exports({"clock": {"stb_common": True}})
    e = G.stb_common_exports({"clock": {"stb_common": {"outlier_ps": 30, "rehome_um": 120, "max_ps": 420}}})
    assert e[1:] == ["export OT_STB_COMMON = 1", "export OT_STB_OUTLIER_PS = 30", "export OT_STB_REHOME_UM = 120",
                     "export OT_STB_COMMON_MAX_PS = 420"]


@pytest.mark.parametrize("bad", [{"x": 1}, {"outlier_ps": -1}, {"max_ps": True}, "yes"])
def test_bad_spec_refused(bad):
    with pytest.raises(ValueError):
        G.stb_common_exports({"clock": {"stb_common": bad}})
