"""KV-HG-CDE 11-24: land_intra_stations nets take an optional per-net `types` regex, so one asbuilt option carries the nets of several dies."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_intra_stations as IS  # noqa: E402

SITES = {
    "kv3_hub_C": [{"src": "ahub.fr_rz", "dst": "pvfin.rz", "regs_um": [[1.0, 2.0], [3.0, 4.0]]}],
    "kv3_hg_v1p5": [{"src": "ectl.e0", "dst": "hst0_g.e_a", "regs_um": [[5.0, 6.0], [7.0, 8.0], [9.0, 10.0]]}],
}


def ab(**kw):
    nets = [{"src": "ahub.fr_rz", "dst": "pvfin.rz", "stages": 2, "types": "kv3_hub_C"},
            {"src": "ectl.e0", "dst": "hst0_g.e_a", "stages": 3, "types": "kv3_hg_v1p5"}]
    return {IS.KEY: {"types": ["kv3_hub_C", "kv3_hg_v1p5"], "nets": nets, "sites": SITES, **kw}}


def test_each_type_sees_only_its_nets():
    cfg = IS.config(ab())
    hub = IS.type_sites(cfg, "kv3_hub_C")
    hg = IS.type_sites(cfg, "kv3_hg_v1p5")
    assert [n["label"] for n, _ in hub] == ["ahub.fr_rz->pvfin.rz"]
    assert [n["label"] for n, _ in hg] == ["ectl.e0->hst0_g.e_a"]
    assert len(hg[0][1]) == 3


def test_net_without_types_applies_to_every_selected_type():
    a = ab()
    del a[IS.KEY]["nets"][0]["types"]
    cfg = IS.config(a)
    assert [n["label"] for n, _ in IS.type_sites(cfg, "kv3_hub_C")] == ["ahub.fr_rz->pvfin.rz"]
    with pytest.raises(ValueError):          # old behaviour kept: the hg sites file has no row for this net
        IS.type_sites(cfg, "kv3_hg_v1p5")


def test_stage_count_still_checked_against_sites():
    a = ab()
    a[IS.KEY]["nets"][1]["stages"] = 2
    with pytest.raises(ValueError):
        IS.type_sites(IS.config(a), "kv3_hg_v1p5")
