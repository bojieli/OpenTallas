#!/usr/bin/env python3
"""Bounded three-type UCIe slot proposal; existing die edge/types are preserved.

Both coll_ft replicas and coll_core move east by 25.92um and narrow by the
same amount. Native macro positions inside those peers remain unchanged.
Only their east-face infrastructure moves locally; their east die edge stays
fixed. UCIe gains the released strip. Outputs are PROPOSALS, never releases.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/die_plan"))
import schema as S
import reset_tree as RT
import rederive_coll_1101 as RC

DELTA = 25.92
TYPES = ("coll_ucie", "coll_core", "coll_ft__cla4a25d77")


def sync_clock_pin_heights(raw, original, tn):
    """Keep explicit physical heights aligned with the priced clock ABI."""
    t = raw["partition_types"][tn]
    heights = t["clock"].get("tap_pin_heights_um")
    if not heights:
        return
    def names(value):
        n = value["clock"]["landing_contract"]["collector_tree"]["n_clock_taps"]
        return {"clk"} | {f"clk_t{i}" for i in range(1, n)}
    old = names(original["partition_types"][tn])
    new = names(t)
    template = heights.get("clk")
    if new - old and template is None:
        raise ValueError(f"{tn}: new clock pins need an explicit physical height")
    for name in old - new:
        heights.pop(name, None)
    for name in new - old:
        heights[name] = template


def shift_point(p, oldw, delta):
    """Keep interior homes fixed; translate only the existing east perimeter."""
    if isinstance(p, list) and len(p) == 2 and all(isinstance(x, (int, float)) for x in p):
        if p[0] >= oldw - 12.96 - 1e-6:
            p[0] = round(p[0] + delta, 6)


def shift_rectangles(o, dx):
    if isinstance(o, dict):
        for key, val in o.items():
            if key in ("rect_um", "resized_from_um") and isinstance(val, list) and len(val) == 4:
                val[0], val[2] = round(val[0] + dx, 6), round(val[2] + dx, 6)
            elif key == "rects_um":
                for r in val:
                    r[0], r[2] = round(r[0] + dx, 6), round(r[2] + dx, 6)
            else:
                shift_rectangles(val, dx)
    elif isinstance(o, list):
        for v in o:
            shift_rectangles(v, dx)


def perimeter_fields(o, oldw, dx):
    if isinstance(o, dict):
        for key, val in o.items():
            if key == "collector_tree":
                continue  # re-derived, not translated or numerically relabelled
            if key in ("xy_um", "pin_xy_um", "tap_um", "up_xy", "in_um", "reset_entry_um", "collector_root_xy"):
                shift_point(val, oldw, dx)
            perimeter_fields(val, oldw, dx)
    elif isinstance(o, list):
        for v in o:
            perimeter_fields(v, oldw, dx)


def macro_fit(raw, types):
    errors = []
    for tn in types:
        t = raw["partition_types"][tn]
        w, h = t["outline_um"]
        for m in t.get("contents", []) + t.get("hard_cores", []):
            if not m.get("lef") or not m.get("outline_um"):
                continue
            x, y = m["origin_um"]
            mw, mh = m["outline_um"]
            if x < 0 or y < 0 or x + mw > w + 1e-6 or y + mh > h + 1e-6:
                errors.append([tn, m["inst"], [x, y, mw, mh], [w, h]])
    return errors


def overlaps(P):
    rows = []
    names = list(P.parts)
    for i, a in enumerate(names):
        ar = P.rect(a)
        for b in names[i + 1:]:
            br = P.rect(b)
            dx = min(ar[2], br[2]) - max(ar[0], br[0])
            dy = min(ar[3], br[3]) - max(ar[1], br[1])
            if min(dx, dy) > 1e-6:
                rows.append([a, b, round(dx, 6), round(dy, 6)])
    return rows


def monitor_hops(P, side):
    out = {}
    for e in side["collector"]["edges"]:
        src, dst = e["src"], e["dst"]
        def pin(part, name):
            lc = P.types[P.parts[part]["type"]]["clock"]["landing_contract"]
            return P.to_die(part, next(p["xy_um"] for p in lc["pins"] if p["name"] == name))
        pairs = [("cland_up_ready", "cland_dn_ready_" + str(e["dst_index"])),
                 ("cland_up_fault", "cland_dn_fault_" + str(e["dst_index"]))]
        if e.get("seam"):
            pairs.append(("fclk_out_cland_up", "fclk_in_cland_dn_" + str(e["dst_index"])))
        lengths = []
        for sp, dp in pairs:
            a, b = pin(src, sp), pin(dst, dp)
            lengths.append(abs(a[0] - b[0]) + abs(a[1] - b[1]))
        out[(src, dst)] = round(max(lengths), 6)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("sidecar")
    ap.add_argument("out", type=Path)
    ap.add_argument("--proposal-only", action="store_true", required=True)
    a = ap.parse_args()
    original = json.load(open(a.plan))
    side0 = json.load(open(a.sidecar))
    raw, side = copy.deepcopy(original), copy.deepcopy(side0)
    changed_parts = []
    for tn in TYPES:
        t = raw["partition_types"][tn]
        oldw = t["outline_um"][0]
        dx = DELTA if tn == "coll_ucie" else -DELTA
        assert oldw == (777.6 if tn == "coll_ucie" else 786.24)
        t["outline_um"][0] = round(oldw + dx, 6)
        perimeter_fields(t, oldw, dx)
        perimeter_fields(side["collector"]["types"][tn], oldw, dx)
        shift_point(raw["reset"]["in_sites"][tn], oldw, dx)
        if tn == "coll_ucie":
            c = next(c for c in t["contents"] if c["inst"] == "u_io_ucie")
            c.update(physical_inst="u_bound.u_io_ucie", physical_master=c["module"], origin_um=[12.996, 4.32])
            prefix = "physical/qwen_missing_phy/nface_tall_g5_lclk_1020/ot_qfd_ucie_x64_phy/ot_qfd_ucie_x64_phy"
            c["lef"], c["lib"] = prefix + ".lef", prefix + "_tt.lib"
            t["core_pg_connect"] = True  # matching native LEF declares VDD/VSS
            shift_rectangles(t["clock"]["landing_contract"]["bands"], DELTA)
            for src in t["clock"]["landing_contract"]["collector_local_sources"]:
                shift_rectangles(src.get("band", {}), DELTA)
            shift_rectangles(side["collector"]["types"][tn]["bands"], DELTA)
            for src in side["collector"]["types"][tn]["local_sources"]:
                shift_rectangles(src.get("band", {}), DELTA)
    for p in raw["partitions"]:
        if p["type"] in TYPES[1:]:
            p["origin_um"][0] = round(p["origin_um"][0] + DELTA, 6)
            changed_parts.append(p["name"])
    # Modern reset derivation consumes the changed physical sites. Its exact
    # tree drives BOTH the plan wrapper and the sidecar collector emitter.
    P = S.Plan(raw, a.plan)
    P0 = S.Plan(original, a.plan)
    child_site_remap = []
    # Reset face sites are proportional to the outline (e.g. the third S
    # terminal moves 655.20 -> 633.60). Preserve its face/j identity and move
    # the associated actual collector pins together, rather than retaining a
    # stale point or guessing a nearest terminal.
    for tn in TYPES:
        lc = raw["partition_types"][tn]["clock"]["landing_contract"]
        lc0 = original["partition_types"][tn]["clock"]["landing_contract"]
        sites0 = RT.face_sites(P0, tn)
        sites1 = {(s["face"], s["j"]): s["xy"] for s in RT.face_sites(P, tn)}
        p0 = {p["name"]: p for p in lc0["pins"]}
        for child, oldchild in zip(lc["collector_children"], lc0["collector_children"]):
            if not oldchild["node"].startswith("rst_n_t"):
                continue
            match = [s for s in sites0 if RC.L1(s["xy"], oldchild["xy_um"]) < 1e-6]
            if len(match) != 1:
                raise ValueError(f"{tn}: child {oldchild['part']} does not identify one old reset face site")
            key = (match[0]["face"], match[0]["j"])
            point = sites1[key]
            shift = [point[i] - oldchild["xy_um"][i] for i in (0, 1)]
            child["xy_um"] = list(point)
            idx = child["index"]
            names = {f"cland_dn_ready_{idx}", f"cland_dn_fault_{idx}",
                     f"fclk_in_cland_dn_{idx}", f"cland_fstart_in_cland_dn_{idx}"}
            for p in lc["pins"]:
                if p["name"] in names:
                    p["xy_um"] = [round(p0[p["name"]]["xy_um"][i] + shift[i], 6) for i in (0, 1)]
            for e in raw["partition_types"][tn]["clock"].get("edge_clocks", []):
                if e["port"] in names:
                    e["tap_um"] = next(p["xy_um"][:] for p in lc["pins"] if p["name"] == e["port"])
            child_site_remap.append(dict(type=tn, child=child["part"], face=key[0], site_j=key[1],
                                         before=oldchild["xy_um"], after=child["xy_um"]))
    reset_deltas = []
    for tn in TYPES:
        lc = raw["partition_types"][tn]["clock"]["landing_contract"]
        oldtree = copy.deepcopy(lc["collector_tree"])
        tree, taps, children, exports = RC.derive(P, lc, tn)
        lc["collector_tree"] = tree
        for s, tap in zip(lc["collector_local_sources"], taps):
            s["tap"] = tap
        for c, node in zip(lc["collector_children"], children):
            c["node"] = node
        for p in lc["pins"]:
            if p["name"] in exports:
                p["source_clock_tap"] = exports[p["name"]]
        sc = side["collector"]["types"][tn]
        assert len(sc["mask"].get("children", [])) == len(lc["collector_children"])
        for mask_child, child in zip(sc["mask"].get("children", []), lc["collector_children"]):
            mask_child["xy_um"] = list(child["xy_um"])
        for k, v in (("tree", tree), ("local_sources", lc["collector_local_sources"]),
                     ("children", lc["collector_children"]), ("collector_root_node", lc.get("collector_root_node"))):
            sc[k] = copy.deepcopy(v)
        reset_deltas.append(dict(type=tn, old_depth=oldtree["depth"], new_depth=tree["depth"],
                                 old_relays=len(oldtree["relays"]), new_relays=len(tree["relays"]),
                                 old_clock_ports=oldtree["n_clock_taps"], new_clock_ports=tree["n_clock_taps"],
                                 old_release_after_pin=RT.release_clocks(oldtree),
                                 new_release_after_pin=RT.release_clocks(tree)))
    P = S.Plan(raw, a.plan)
    for tn in TYPES:
        sync_clock_pin_heights(raw, original, tn)
    for region in side["regions"]:
        # A region tag can name one member of a merged multi-partition
        # region. Preserve every unaffected region's complete box.
        if region["tag"] in P.parts and P.parts[region["tag"]]["type"] in TYPES:
            if region.get("parts") != 1:
                raise ValueError(f"changed footprint belongs to merged region {region['tag']}")
            region["box_um"] = list(P.rect(region["tag"]))
    before, after = monitor_hops(P0, side0), monitor_hops(P, side)
    hop_diff = [dict(src=s, dst=d, before_um=before[s, d], after_um=v)
                for (s, d), v in after.items() if abs(v - before[s, d]) > 1e-6]
    for e in side["collector"]["edges"]:
        e["hop_um"] = after[e["src"], e["dst"]]
    side["collector"]["max_die_hop_um"] = max(after.values())
    old_overlaps = {(x[0], x[1]) for x in overlaps(P0)}
    new_overlaps = [x for x in overlaps(P) if (x[0], x[1]) not in old_overlaps]
    errors = dict(macro_fit=macro_fit(raw, TYPES), new_footprint_overlaps=new_overlaps,
                  new_monitor_reach=[x for x in hop_diff if x["after_um"] > 405])
    assert raw["die"] == original["die"], "die edge/PG contract changed silently"
    assert set(raw["partition_types"]) == set(original["partition_types"]), "new type"
    assert side["count_aligned"] == side0["count_aligned"], "count/programme contract changed"
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "PROPOSAL_NOT_RELEASED.json").write_text(json.dumps(raw) + "\n")
    (a.out / "sidecar.json").write_text(json.dumps(side, indent=1) + "\n")
    report = dict(verdict="REJECT" if any(errors.values()) else "PENDING_G0C_BIND_REVIEW",
                  types=list(TYPES), shifted_parts=changed_parts, added_mission_cycles=0,
                  new_unowned_gap_um=DELTA, gap_beside="coll_f1", reset_deltas=reset_deltas,
                  monitor_hop_diff=hop_diff, child_site_remap=child_site_remap, errors=errors,
                  boot_clock_model=[dict(type=x["type"], normal_clock_ports_before=x["old_clock_ports"],
                      normal_clock_ports_after=x["new_clock_ports"],
                      release_after_pin_before=x["old_release_after_pin"],
                      release_after_pin_after=x["new_release_after_pin"],
                      extra_local_boot_cycles=x["new_release_after_pin"]-x["old_release_after_pin"],
                      extra_mission_cycles=0) for x in reset_deltas],
                  boot_model_scope="Per-partition source release model at833ps; composed die boot/START qualification still held",
                  held=["G0/C differential all reach/clock/reset/ports", "strict native bind",
                        "new clock ABI/parent prefix and composed boot model event",
                        "actual measured fill/native source qualification", "GEN and actual LOOK",
                        "licensed PHY remains assumed, no physical release"])
    (a.out / "proposal.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
