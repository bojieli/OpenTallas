#!/usr/bin/env python3
"""Explicit, default-OFF QBS 13-cell PRE-CTS membership-only rebinding.

This does not extend the closed-leaf post_place_rebind option. A reviewed
manifest binds one original PLACE ODB/SDC, all 13 planned cells, and the four
493-register open leaves. No placement, sizing, clock stage or delay is chosen.
The existing exact-count geometry optimizer supplies the assignment. Native
execution requires OT_CTS_OPEN_REBIND_ENABLE=1 and writes a NEW database only.
No ordinary kit or global deployment calls this tool.
"""
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_leaf_rebind


class RebindError(ValueError):
    pass


FF_MASTERS = {"DFFHQNx1_ASAP7_75t_R", "DFFASRHQNx1_ASAP7_75t_R"}
LEAVES = {"qb_SW", "qb_SE", "qb_NW", "qb_NE"}
MASTERS = {"BUFx2_ASAP7_75t_R": 6, "BUFx16f_ASAP7_75t_R": 1,
           "BUFx12_ASAP7_75t_R": 6}


def require(ok, reason):
    if not ok:
        raise RebindError(reason)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate(state, manifest):
    """Read-only checks; unknown stages, members and drivers fail closed."""
    require(manifest.get("schema") == "opentallas.qbs_cts_open_rebind.v1", "MANIFEST_SCHEMA")
    require(manifest.get("stage") == "pre_cts", "PRE_CTS_STAGE_REQUIRED")
    require(manifest.get("module") == "dsfd_node_LLfd" == state["module"], "MODULE_SCOPE")
    require(manifest.get("period_ps") == 833, "SOURCE_FREQUENCY")
    require(manifest.get("reviewed_source_event"), "SOURCE_EVENT_REQUIRED")
    nodes = manifest.get("nodes", [])
    leaves = manifest.get("leaves", [])
    require(len(nodes) == 13 and len({n["name"] for n in nodes}) == 13, "PLANNED_13_CELLS")
    require(len(leaves) == 4 and {l["node"] for l in leaves} == LEAVES, "PLANNED_4_LEAVES")
    from collections import Counter
    require(dict(Counter(n["master"] for n in nodes)) == MASTERS, "PLANNED_MASTER_COUNTS")
    instances, nets = state["instances"], state["nets"]
    outputs, inputs = {}, {}
    for name, inst in instances.items():
        for pin, p in inst["pins"].items():
            if p["net"] is None:
                continue
            target = outputs if p["io"] == "OUTPUT" else inputs
            target.setdefault(p["net"], set()).add((name, pin))
    clock_port = manifest.get("clock_port")
    require(clock_port == "clk[0]" and clock_port in state["ports"], "COMMON_CLOCK_PORT")
    root_net = state["ports"][clock_port]["net"]
    require(state["ports"][clock_port]["io"] == "INPUT", "COMMON_CLOCK_INPUT")
    require(nets[root_net]["sig"] == "CLOCK", "COMMON_CLOCK_NET")
    require(not outputs.get(root_net), "FOREIGN_ROOT_DRIVER")
    by_name = {n["name"]: n for n in nodes}
    child_inputs = {root_net: set()}
    for n in nodes:
        actual = instances.get(n["name"])
        require(actual is not None, "MISSING_PLANNED_CELL")
        for key in ("master", "bbox", "orient", "status", "protected"):
            require(actual[key] == n[key], "PLANNED_CELL_POSE_OR_MASTER: " + n["name"])
        require(actual["protected"], "UNPROTECTED_PLANNED_CELL")
        require(actual["pins"]["Y"]["net"] == n["net_y"], "PLANNED_OUTPUT_NET")
        require(outputs.get(n["net_y"]) == {(n["name"], "Y")}, "FOREIGN_DRIVER")
        if n["name"] not in LEAVES:
            require(nets[n["net_y"]]["sig"] == "CLOCK" and nets[n["net_y"]]["protected"],
                    "PLANNED_TRUNK_PROTECTION")
        parent = n["parent"]
        require(parent == "port:clk[0]" or parent in by_name, "FOREIGN_PARENT")
        source = root_net if parent == "port:clk[0]" else by_name[parent]["net_y"]
        require(actual["pins"]["A"]["net"] == source, "PLANNED_TRUNK_TOPOLOGY")
        child_inputs.setdefault(source, set()).add((n["name"], "A"))
    depth = {}
    def level(name, trail=()):
        require(name not in trail, "CLOCK_CYCLE")
        if name not in depth:
            parent = by_name[name]["parent"]
            depth[name] = 1 if parent == "port:clk[0]" else 1 + level(parent, trail + (name,))
        return depth[name]
    require({level(n) for n in LEAVES} == {9}, "EXISTING_STAGE_DEPTH_9")
    target_pins, leaf_nets = set(), set()
    for leaf in leaves:
        name = leaf["node"]
        net = by_name[name]["net_y"]
        require(net not in leaf_nets, "ALIASED_LEAF_NET")
        leaf_nets.add(net)
        props = nets[net]
        require(props["sig"] == "CLOCK" and not props["protected"], "CTS_OPEN_NET_REQUIRED")
        require(not props["wire"] and not props["special"], "ALREADY_ROUTED_OR_CLOSED_CTS")
        members = leaf.get("sinks", [])
        require(len(members) == 493, "EXACT_493_PER_LEAF")
        expected = set()
        for s in members:
            name, pin = s["instance"], s["pin"]
            require(pin == "CLK" and s["master"] in FF_MASTERS, "DIRECT_REGISTER_CLK_ONLY")
            actual = instances.get(name)
            require(actual is not None and actual["master"] == s["master"], "MISSING_OR_CHANGED_MEMBER")
            require(pin in actual["pins"] and actual["pins"][pin]["io"] == "INPUT", "REGISTER_CLK_INPUT")
            require(actual["pins"][pin]["net"] == net, "SOURCE_MEMBERSHIP")
            key = (name, pin)
            require(key not in target_pins, "DUPLICATE_MEMBER")
            target_pins.add(key); expected.add(key)
        require(inputs.get(net, set()) == expected, "MISSING_MEMBER_OR_NONREG_CHILD")
    require(len(target_pins) == 1972, "EXACT_1972_ENDPOINTS")
    for net, children in child_inputs.items():
        require(inputs.get(net, set()) == children, "UNPLANNED_TRUNK_CHILD")
    # This event owns the complete single-root register census, not a selected subset.
    actual_regs = {(n, "CLK") for n, i in instances.items() if i["master"].startswith("DFF")}
    require(actual_regs == target_pins, "FOREIGN_REGISTER_OR_INCOMPLETE_CENSUS")
    return target_pins


def preserved_state(state, target_pins):
    value = copy.deepcopy(state)
    for name, pin in target_pins:
        value["instances"][name]["pins"][pin]["net"] = "<explicit-rebind-target>"
    return value


def proposal(state, manifest):
    validate(state, manifest)
    by_name = {n["name"]: n for n in manifest["nodes"]}
    u = state["dbu"]
    centre = lambda b: ((b[0] + b[2]) / (2*u), (b[1] + b[3]) / (2*u))
    leaves = [(l["node"], *centre(by_name[l["node"]]["bbox"])) for l in manifest["leaves"]]
    sinks = [(s["instance"] + "/CLK", *centre(state["instances"][s["instance"]]["bbox"]), l["node"], 0)
             for l in manifest["leaves"] for s in l["sinks"]]
    assigned, stats = core_leaf_rebind.rebind(leaves, sinks)
    require(stats["converged"], "GEOMETRY_OPTIMIZER_NOT_CONVERGED")
    new = copy.deepcopy(manifest)
    members = {l["node"]: [] for l in manifest["leaves"]}
    entries = {s["instance"]: s for l in manifest["leaves"] for s in l["sinks"]}
    moves = []
    for sink, leaf in zip(sinks, assigned):
        instance = sink[0].removesuffix("/CLK")
        members[leaf].append(entries[instance])
        if leaf != sink[3]:
            moves.append(dict(instance=instance, pin="CLK", source=sink[3], target=leaf))
    for l in new["leaves"]:
        l["sinks"] = members[l["node"]]
    return new, moves, stats


def snapshot(block):
    """Full named poses/connections/PG geometry; only target CLK attachments may differ."""
    instances, nets, ports = {}, {}, {}
    for i in block.getInsts():
        b = i.getBBox()
        instances[i.getName()] = dict(master=i.getMaster().getName(), bbox=[b.xMin(), b.yMin(), b.xMax(), b.yMax()],
            origin=list(i.getOrigin()), orient=str(i.getOrient()), status=str(i.getPlacementStatus()),
            protected=bool(i.isDoNotTouch()), pins={it.getMTerm().getName(): dict(
                net=it.getNet().getName() if it.getNet() else None, io=str(it.getMTerm().getIoType()),
                sig=str(it.getMTerm().getSigType())) for it in i.getITerms()})
    for n in block.getNets():
        shapes = []
        for sw in n.getSWires():
            for b in sw.getWires():
                via = (b.getTechVia() or b.getBlockVia()) if b.isVia() else None
                shapes.append([via.getName() if via else b.getTechLayer().getName(),
                               b.xMin(), b.yMin(), b.xMax(), b.yMax(), bool(b.isVia())])
        nets[n.getName()] = dict(sig=str(n.getSigType()), protected=bool(n.isDoNotTouch()),
                                wire=bool(n.getWire()), special=sorted(shapes))
    for b in block.getBTerms():
        boxes = [[r.getTechLayer().getName(), r.xMin(), r.yMin(), r.xMax(), r.yMax()]
                 for p in b.getBPins() for r in p.getBoxes()]
        ports[b.getName()] = dict(net=b.getNet().getName() if b.getNet() else None,
                                 io=str(b.getIoType()), sig=str(b.getSigType()), boxes=sorted(boxes))
    return dict(module=block.getName(), dbu=block.getDb().getTech().getDbUnitsPerMicron(),
                instances=instances, nets=nets, ports=ports)


def run_native(input_odb, source_sdc, manifest_path, output_odb, enabled=False):
    require(enabled, "DEFAULT_OFF: explicit native enable required")
    manifest = json.loads(Path(manifest_path).read_text())
    input_odb, output_odb = Path(input_odb), Path(output_odb)
    require(input_odb.resolve() != output_odb.resolve() and not output_odb.exists(), "FRESH_OUTPUT_REQUIRED")
    require(not any(Path(str(output_odb) + suffix).exists()
                    for suffix in (".tmp", ".receipt.json", ".manifest.json")), "FRESH_RECEIPTS_REQUIRED")
    require(hashlib.sha256(input_odb.read_bytes()).hexdigest() == manifest["input_odb_sha256"], "SOURCE_ODB_IDENTITY")
    require(hashlib.sha256(Path(source_sdc).read_bytes()).hexdigest() == manifest["source_sdc_sha256"], "SOURCE_SDC_IDENTITY")
    import odb
    db = odb.dbDatabase.create(); odb.read_db(db, str(input_odb)); block = db.getChip().getBlock()
    before = snapshot(block); targets = validate(before, manifest)
    updated, moves, stats = proposal(before, manifest)
    by_name = {n["name"]: n for n in manifest["nodes"]}
    for move in moves:
        i = block.findInst(move["instance"]); it = i.findITerm("CLK")
        old_protection = i.isDoNotTouch()
        try:
            if old_protection: i.setDoNotTouch(False)
            it.disconnect(); it.connect(block.findNet(by_name[move["target"]]["net_y"]))
        finally:
            if old_protection: i.setDoNotTouch(True)
    after = snapshot(block); validate(after, updated)
    preserved_before = digest(preserved_state(before, targets))
    preserved_after = digest(preserved_state(after, targets))
    require(preserved_before == preserved_after, "NON_TARGET_STATE_CHANGED")
    receipt = dict(schema="opentallas.qbs_cts_open_rebind_result.v1", stage="pre_cts_rebound_not_CTS",
                   input_odb_sha256=manifest["input_odb_sha256"], stats=stats,
                   preserved_before=preserved_before, preserved_after=preserved_after,
                   unchanged="all poses/masters/protection, DATA/reset/PG/non-targetCLOCK/ports/SDC; 13cells/depth9/833ps; 493each", moves=moves)
    tmp = output_odb.with_suffix(output_odb.suffix + ".tmp")
    require(not tmp.exists(), "FRESH_TEMP_OUTPUT_REQUIRED")
    odb.write_db(db, str(tmp)); tmp.rename(output_odb)
    receipt["output_odb_sha256"] = hashlib.sha256(output_odb.read_bytes()).hexdigest()
    updated["stage"] = "pre_cts_rebound"
    updated["output_odb_sha256"] = receipt["output_odb_sha256"]
    Path(str(output_odb) + ".receipt.json").write_text(json.dumps(receipt, indent=2))
    Path(str(output_odb) + ".manifest.json").write_text(json.dumps(updated, indent=2))
    print("OT_CTS_OPEN_REBIND " + json.dumps({k: v for k, v in receipt.items() if k != "moves"}))
    return receipt


if __name__ == "__main__":
    # OpenROAD -python entry: no implicit activation or arbitrary command arguments.
    run_native(os.environ.get("OT_CTS_OPEN_REBIND_INPUT", ""), os.environ.get("OT_CTS_OPEN_REBIND_SDC", ""),
               os.environ.get("OT_CTS_OPEN_REBIND_MANIFEST", ""), os.environ.get("OT_CTS_OPEN_REBIND_OUTPUT", ""),
               enabled=os.environ.get("OT_CTS_OPEN_REBIND_ENABLE") == "1")
