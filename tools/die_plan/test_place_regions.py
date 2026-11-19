"""PLACE-REGION (lever 5): plan key partition_types.<type>.place_regions -> place_regions_data.tcl + place_regions.tcl in the kit."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402
import schema  # noqa: E402

ROW = {"name": "core", "inst_re": r"(^|[./])u_core\.", "util": 0.55, "near_re": r"u_core\.u_gi\.g_op"}


def test_absent_key_writes_nothing(tmp_path):
    assert gen_phys.install_place_regions(tmp_path, None) == []
    assert gen_phys.install_place_regions(tmp_path, []) == []
    assert list(tmp_path.iterdir()) == []


def test_kit_gets_data_and_hook(tmp_path):
    cfg = gen_phys.install_place_regions(tmp_path, [ROW, {"name": "rows", "inst_re": r"u_x\.(tt_pw|dh_prog)\[", "centre_um": [550, 955.5]}])
    assert len(cfg) == 1 and cfg[0].startswith("#") and "core, rows" in cfg[0]
    data = (tmp_path / "place_regions_data.tcl").read_text()
    assert "set ::ot_place_regions {" in data
    assert r"  {core {(^|[./])u_core\.} 0.55 {} {} {u_core\.u_gi\.g_op}}" in data
    assert r"  {rows {u_x\.(tt_pw|dh_prog)\[} 0.55 550 955.5 {}}" in data
    hook = (tmp_path / "place_regions.tcl").read_text()
    assert "dbRegion_create" in hook and "OT_PLACE_REGION" in hook
    assert hook == (Path(gen_phys.__file__).resolve().parent / "place_regions.tcl").read_text()


def test_face_flops_sources_the_hook_only_with_data():
    t = (Path(gen_phys.__file__).resolve().parent / "face_flops.tcl").read_text()
    assert "if {[file exists /work/place_regions_data.tcl] && [file exists /work/place_regions.tcl]} { source /work/place_regions_data.tcl; source /work/place_regions.tcl }" in t
    assert t.index("place_regions.tcl") < t.index("OT_GPL_GUARD begin")      # regions exist before the GPL guard / global_placement


@pytest.mark.parametrize("bad", [dict(ROW, util=0.95), dict(ROW, name="1x"), dict(ROW, inst_re="a{b"), dict(ROW, inst_re=""),
                                 dict(ROW, centre_um=[1, 2]), dict(ROW, inst_re="(")])
def test_bad_rows_are_refused(tmp_path, bad):
    with pytest.raises(Exception):
        gen_phys.install_place_regions(tmp_path, [bad])
    assert not (tmp_path / "place_regions_data.tcl").exists()


def test_repeated_name_is_refused(tmp_path):
    with pytest.raises(ValueError):
        gen_phys.install_place_regions(tmp_path, [ROW, ROW])


def test_schema_has_the_key():
    p = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["place_regions"]
    assert p["items"]["required"] == ["name", "inst_re"] and p["items"]["additionalProperties"] is False
    assert set(p["items"]["properties"]) == {"name", "inst_re", "util", "centre_um", "near_re", "note"}
