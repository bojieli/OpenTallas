"""Install the reviewed fE0 P2 row guidance through the stock placement hooks."""
import hashlib
import json
from pathlib import Path
import shutil


TYPE = "col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff"
TERMINAL_SEATS = "a0fa0ae48f118ed74975ce1043945327b99dc89b753b7b0693e4e55ed13b9250"
FRAME = "p2_frame_bridge_guide.tcl"
EDGE = ("p2_t2_native_guide.tcl", "p2_t2_row_specs.tcl",
        "p2_ft0_terminal_guide.tcl", "p2_ft0_terminal_specs.tcl")
FILES = {FRAME, *EDGE}


def install(cfg, kit_dir, type_name, typed_plan, stage_hook_lines, recipe, recipe_sha):
    from reviewed_station_prepare import checked_file

    source = json.loads(checked_file({"path": recipe, "sha256": recipe_sha}).read_bytes())
    if (type_name != TYPE or source["type"] != TYPE
            or typed_plan["outline_um"] != [1442.88, 1166.4] or set(source["p2_guides"]) != FILES):
        raise ValueError("the P2 guidance requires its exact reviewed south-cropped type")
    ft0, = (entry for entry in typed_plan["ft_slots"] if entry["name"] == "ft0")
    terminals = json.dumps(ft0["bit_sites_um"][-1], separators=(",", ":")).encode()
    if hashlib.sha256(terminals).hexdigest() != TERMINAL_SEATS:
        raise ValueError("the source FT0 terminal seats differ from the reviewed P2 guide")
    kit_dir = Path(kit_dir)
    for name in sorted(FILES):
        path = checked_file(source["p2_guides"][name])
        shutil.copyfile(path, kit_dir / name)
    grouping, frame_check = "p2_frame_bridge_group.tcl", "p2_frame_bridge_gate.tcl"
    (kit_dir / grouping).write_text(
        f"source /work/{FRAME}\n::ot_p2_frame_bridge::group_atoms [ord::get_db_block]\n")
    (kit_dir / frame_check).write_text(
        f"source /work/{FRAME}\n::ot_p2_frame_bridge::verify_and_release [ord::get_db_block]\n")
    lines = (stage_hook_lines(cfg, kit_dir, "PRE_GLOBAL_PLACE_TCL", [grouping], "p2_frame_pre_global.tcl")
             + stage_hook_lines(cfg, kit_dir, "PRE_DETAIL_PLACE_TCL", [grouping], "p2_frame_pre_detail.tcl")
             + stage_hook_lines(cfg, kit_dir, "POST_DETAIL_PLACE_TCL", [frame_check], "p2_frame_post_detail.tcl"))
    sources = "".join(f"source /work/{name}\n" for name in EDGE)
    setup, edge_check = "p2_edge_corridor_pre_detail.tcl", "p2_edge_corridor_post_detail.tcl"
    (kit_dir / setup).write_text(sources
        + "::ot_p2_t2_guard::guide_after_stock_release [ord::get_db_block] $::ot_p2_t2_specs\n"
        + "::ot_p2_ft0_guard::guide_after_stock_release [ord::get_db_block] $::ot_p2_ft0_specs\n")
    (kit_dir / edge_check).write_text(sources
        + "::ot_p2_ft0_guard::verify_after_detail_and_release [ord::get_db_block] $::ot_p2_ft0_specs\n"
        + "::ot_p2_t2_guard::verify_after_detail_and_release [ord::get_db_block] $::ot_p2_t2_specs\n")
    frame_cfg = cfg + lines
    lines += (stage_hook_lines(frame_cfg, kit_dir, "PRE_DETAIL_PLACE_TCL", [setup], "p2_edge_corridor_setup.tcl")
              + stage_hook_lines(frame_cfg, kit_dir, "POST_DETAIL_PLACE_TCL", [edge_check], "p2_edge_corridor_check.tcl"))
    return lines + ["export OT_S81_P2_CROP_REVIEW_GUIDES = 1"]
