"""FLOW-REFRESH-ALL-1124: every flow tcl of a kit reaches the newest rt: verbatim copies (gutter_block.tcl, GUTTER-LAND-CARVE) by the index pass,
appended / prefixed gen edits (clock_taps.tcl, reset_taps.tcl) by the edited-copy pass; generated and inside-edited files are kept."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_flow_refresh as KFR  # noqa: E402

OLD_GB = b"# gutter_block.tcl (9fb4)\nproc gb {} { return old }\n"
NEW_GB = b"# gutter_block.tcl (efc0, GUTTER-LAND-CARVE)\nproc gb {} { gb_carve; return new }\n"


def tree(root, files):
    for rel, data in files.items():
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
    return root


def test_gutter_block_and_gen_edited_copies_take_the_newest_rt(tmp_path):
    old = tree(tmp_path / "rt_old", {"tools/die_plan/gutter_block.tcl": OLD_GB, "tools/die_plan/clock_taps.tcl": b"ct v1\n",
                                       "tools/die_plan/reset_taps.tcl": b"rt v1\n", "tools/die_plan/face_flops.tcl": b"ff v1\nend\n"})
    new = tree(tmp_path / "rt_new", {"tools/die_plan/gutter_block.tcl": NEW_GB, "tools/die_plan/clock_taps.tcl": b"ct v2\n",
                                       "tools/die_plan/reset_taps.tcl": b"rt v2\n", "tools/die_plan/face_flops.tcl": b"ff v2\nend\n"})
    (new / "tools").mkdir(exist_ok=True)
    (new / KFR.INDEX).write_text(json.dumps({"sha": "efc0", "blobs": {"tools/die_plan/gutter_block.tcl": [KFR.blob_id(OLD_GB), KFR.blob_id(NEW_GB)]}}))
    kit = tree(tmp_path / "kit", {"gutter_block.tcl": OLD_GB,                                         # verbatim gen copy of the older rt
                                   "clock_taps.tcl": b"ct v1\n\nsource /work/landing_exports.tcl\n",  # gen appended a line
                                   "reset_taps.tcl": b"set rt_leaf_tap 3\nrt v1\n",                    # gen put a prefix
                                   "face_flops.tcl": b"ff v1\nEDIT\nend\n",                            # edited inside: kept
                                   "landing_placement.tcl": b"generated\n"})                         # generated: kept
    rec = KFR.refresh(str(kit), "place", rt=str(new), gen_tools=str(old))
    assert (kit / "gutter_block.tcl").read_bytes() == NEW_GB
    assert (kit / "clock_taps.tcl").read_bytes() == b"ct v2\n\nsource /work/landing_exports.tcl\n"
    assert (kit / "reset_taps.tcl").read_bytes() == b"set rt_leaf_tap 3\nrt v2\n"
    assert (kit / "face_flops.tcl").read_bytes() == b"ff v1\nEDIT\nend\n"
    assert (kit / "landing_placement.tcl").read_bytes() == b"generated\n"
    froms = {r["file"]: r.get("from", "index") for r in rec["replaced"]}
    assert froms["gutter_block.tcl"] == "index" and froms["clock_taps.tcl"].startswith("edited-copy (suffix")
    assert froms["reset_taps.tcl"].startswith("edited-copy (prefix")
    rec2 = KFR.refresh(str(kit), "cts", rt=str(new), gen_tools=str(old))                  # idempotent
    assert rec2["replaced"] == []
