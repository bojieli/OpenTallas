"""demacro_row: a de-macro row for the kv3_pc_v1 shape (bank sites on kvpc1_f) leaves 0 bank sites in the macro."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_site_in_macro as AS  # noqa: E402
import demacro_row as D  # noqa: E402
from test_core_place_station_sites import pc_type  # noqa: E402


def test_row_clears_the_macro_and_touches_only_banks():
    raw = {"partition_types": {"pc": pc_type((993.6, 246.24)), "ok": pc_type((665.28, 246.24))}}
    assert AS.counts(raw)["pc"]["in_core"] >= 1
    ops, rep = D.row_ops(raw)
    assert set(rep) == {"pc"} and rep["pc"]["before"] >= 1 and rep["pc"]["after"] == 0
    assert ops and all(o["op"] == "replace" and o["path"].startswith("/partition_types/pc/internal_stations/0/") for o in ops)
    new = copy.deepcopy(raw)
    for o in ops:
        _, tn, key, i, k = o["path"].strip("/").split("/")
        assert new["partition_types"][tn][key][int(i)][k] == o["old"]
        new["partition_types"][tn][key][int(i)][k] = o["value"]
    assert AS.counts(new) == {}
