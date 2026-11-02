#!/usr/bin/env python3
"""Extend the held UCIe repack to its measured northern pin-window dependency.

G0 schema rejected twelve coll_core N inputs after its25.92um origin move.
Translating its complete north bank west would put corner windows outside
the outline. Keep the core bank intact and move all existing coll_ftm south
interfaces east25.92um instead. Its source input windows already inherit this
shift; their actual collector bands/clock pins must follow them too.
No new type, data stage or die-edge change.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/die_plan"))
import schema as S
import rederive_coll_1101 as RC
import reset_tree as RT
import propose_coll_ucie_repack_1101 as BASE


def translate(o, dx):
    if isinstance(o, dict):
        for key, value in o.items():
            if key in ("rect_um", "resized_from_um") and isinstance(value, list) and len(value) == 4:
                value[0], value[2] = round(value[0] + dx, 6), round(value[2] + dx, 6)
            elif key in ("xy_um", "pin_xy_um") and isinstance(value, list) and len(value) == 2:
                value[0] = round(value[0] + dx, 6)
            elif key == "rects_um":
                for rect in value:
                    rect[0], rect[2] = round(rect[0] + dx, 6), round(rect[2] + dx, 6)
            else:
                translate(value, dx)
    elif isinstance(o, list):
        for value in o:
            translate(value, dx)


def move_bus_landing(raw, side, tn, bus, dx, direction):
    t = raw["partition_types"][tn]
    lc = t["clock"]["landing_contract"]
    names = {f"fclk_{direction}_{bus}", f"cland_fstart_{direction}_{bus}"}
    for pin in lc["pins"]:
        if pin["name"] in names:
            translate(pin, dx)
    for edge in t["clock"].get("edge_clocks", []):
        if edge["port"] in names:
            edge["tap_um"][0] = round(edge["tap_um"][0] + dx, 6)
    if direction == "in":
        translate(lc["bands"][bus], dx)
        for src in lc["collector_local_sources"]:
            if src["name"] == bus:
                translate(src, dx)
        sc = side["collector"]["types"][tn]
        sc["bands"] = copy.deepcopy(lc["bands"])
        sc["local_sources"] = copy.deepcopy(lc["collector_local_sources"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("original_plan")
    ap.add_argument("original_sidecar")
    ap.add_argument("held_proposal", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--proposal-only", action="store_true", required=True)
    a = ap.parse_args()
    original = json.load(open(a.original_plan))
    side0 = json.load(open(a.original_sidecar))
    raw = json.load(open(a.held_proposal / "PROPOSAL_NOT_RELEASED.json"))
    side = json.load(open(a.held_proposal / "sidecar.json"))
    report = json.load(open(a.held_proposal / "proposal.json"))
    peers = [p for p in raw["ports"] if p["src"]["part"] == "coll_f3" and p["dst"]["part"] == "coll_core"]
    changes = []
    ft = raw["partition_types"]["coll_ftm"]
    for slot in ft["ft_slots"]:
        for stem, direction in (("in", "in"), ("out", "out")):
            if slot[stem + "_face"] != "S":
                continue
            bus = slot["name"] + ("_i" if stem == "in" else "_o")
            window_key = stem + "_window_um"
            old_window = copy.deepcopy(slot.get(window_key))
            if old_window is not None:
                slot[window_key] = [round(x + 25.92, 6) for x in old_window]
            move_bus_landing(raw, side, "coll_ftm", bus, 25.92, direction)
            changes.append(dict(type="coll_ftm", bus=bus, before=old_window,
                                after=slot.get(window_key),
                                window_rule="explicit +25.92" if old_window else "input inherits moved coll_core north bank",
                                landing_translation_um=25.92))
    assert len(peers) == 12, len(peers)
    schema_errors = S.validate(raw)
    if schema_errors:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "schema_FAIL.json").write_text(json.dumps(schema_errors, indent=1) + "\n")
        raise ValueError(f"north remap still has {len(schema_errors)} schema findings")
    P = S.Plan(raw, a.original_plan)
    fourth_model = None
    for tn in ("coll_core", "coll_ftm"):
        lc = raw["partition_types"][tn]["clock"]["landing_contract"]
        tree, taps, children, exports = RC.derive(P, lc, tn)
        lc["collector_tree"] = tree
        for src, tap in zip(lc["collector_local_sources"], taps):
            src["tap"] = tap
        for child, node in zip(lc["collector_children"], children):
            child["node"] = node
        for pin in lc["pins"]:
            if pin["name"] in exports:
                pin["source_clock_tap"] = exports[pin["name"]]
        sc = side["collector"]["types"][tn]
        for key, value in (("tree", tree), ("local_sources", lc["collector_local_sources"]), ("children", lc["collector_children"])):
            sc[key] = copy.deepcopy(value)
        if tn == "coll_ftm":
            oldtree = original["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"]
            fourth_model = dict(type=tn, normal_clock_ports_before=oldtree["n_clock_taps"],
                normal_clock_ports_after=tree["n_clock_taps"],
                release_after_pin_before=RT.release_clocks(oldtree), release_after_pin_after=RT.release_clocks(tree),
                extra_local_boot_cycles=RT.release_clocks(tree)-RT.release_clocks(oldtree), extra_mission_cycles=0)
    hops0 = BASE.monitor_hops(S.Plan(original, a.original_plan), side0)
    hops1 = BASE.monitor_hops(S.Plan(raw, a.original_plan), side)
    hopdiff = [dict(src=s, dst=d, before_um=hops0[s, d], after_um=v)
               for (s, d), v in hops1.items() if abs(v - hops0[s, d]) > 1e-6]
    for edge in side["collector"]["edges"]:
        edge["hop_um"] = hops1[edge["src"], edge["dst"]]
    side["collector"]["max_die_hop_um"] = max(hops1.values())
    assert side["count_aligned"] == side0["count_aligned"]
    report.update(verdict="PENDING_G0C_BIND_REVIEW", modified_types=[*BASE.TYPES, "coll_ftm"],
                  north_window_remap=changes, schema_errors=schema_errors,
                  monitor_hop_diff=hopdiff, required_scope_extension="coll_ftm complete S face +25.92um, including implicit input landing geometry")
    if fourth_model is not None:
        report["boot_clock_model"].append(fourth_model)
    report["errors"]["new_monitor_reach"] = [x for x in hopdiff if x["after_um"] > 405]
    if report["errors"]["new_monitor_reach"]:
        report["verdict"] = "REJECT"
    a.out.mkdir(parents=True, exist_ok=True)
    for name, value, indent in (("PROPOSAL_NOT_RELEASED.json", raw, None), ("sidecar.json", side, 1), ("proposal.json", report, 1)):
        (a.out / name).write_text(json.dumps(value, indent=indent) + "\n")
    print(json.dumps(dict(verdict=report["verdict"], schema_errors=schema_errors,
                         changes=changes, maximum_monitor_hop=max(hops1.values())), indent=1))


if __name__ == "__main__":
    main()
