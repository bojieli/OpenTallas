#!/usr/bin/env python3
"""Compile source-selected HBM accelerator composition into OpenROAD inputs.

No model replay, elaboration, abstract fabrication, RTL or physical tool launch.
The binding manifest names SHA-pinned owner selection and unified-model records.
Missing selection/slot/abstract/port budgets stop emission; GPU-ablation inputs
and pending-outline SM substitutes are never accepted as accelerator geometry.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = "results/uarch/hbm_accel_fulldie_inputs_20261004/bindings.json"
ROLES = {"deepseek": {"sm", "service", "controller", "phy", "collective"},
         "qwen": {"tile", "service", "controller", "phy", "collective"}}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pinned(root, ref):
    require(isinstance(ref, dict), "missing source-pinned owner record")
    path = ref.get("path")
    require(isinstance(path, str) and not Path(path).is_absolute() and
            ".." not in Path(path).parts, "repository-relative source required")
    raw = (root / path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ref.get("sha256"), "source drift: " + path)
    return raw


def record(root, ref):
    value = json.loads(pinned(root, ref))
    # JSON Pointer selects the actual target, not an inferred/default preset.
    pointer = ref.get("pointer", "")
    require(pointer == "" or pointer.startswith("/"), "invalid JSON pointer")
    for key in pointer.split("/")[1:]:
        key = key.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def finite(value, label, positive=False):
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and
            math.isfinite(value) and (value > 0 if positive else value >= 0),
            "unknown/invalid " + label)
    return value


def box(value, label):
    require(isinstance(value, list) and len(value) == 4, "missing box: " + label)
    x, y, w, h = value
    for q in value:
        finite(q, label)
    require(w > 0 and h > 0, "empty box: " + label)
    return x, y, w, h


def contains(a, b):
    return b[0] >= a[0] and b[1] >= a[1] and b[0]+b[2] <= a[0]+a[2] and b[1]+b[3] <= a[1]+a[3]


def overlaps(a, b):
    return a[0] < b[0]+b[2] and b[0] < a[0]+a[2] and a[1] < b[1]+b[3] and b[1] < a[1]+a[3]


def atom(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_./\[\]:-]+", value),
            "unsafe/unknown Tcl identifier")
    return "{" + value + "}"


def parameters(raw, module):
    # Public parameters of this exact module header only. Never infer a chosen
    # value from an RTL default or include parameters of another module in file.
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", raw, flags=re.S)
    header = re.search(r"\bmodule\s+"+re.escape(module)+r"\b(.*?);", clean, re.S)
    require(header, "missing RTL module: " + module)
    start = re.search(r"#\s*\(", header[1])
    if start is None:
        return set()
    # Split only top-level commas; defaults may contain nested function calls,
    # concatenations or strings. Also cover `parameter int A=1, B=2`.
    pieces, part, level, quoted, escaped, ended = [], [], 1, False, False, False
    for char in header[1][start.end():]:
        if quoted:
            part.append(char)
            if escaped: escaped = False
            elif char == "\\": escaped = True
            elif char == '"': quoted = False
            continue
        if char == '"': quoted = True
        elif char in "([{": level += 1
        elif char in ")]}":
            level -= 1
            if level == 0:
                pieces.append("".join(part)); ended = True; break
        elif char == "," and level == 1:
            pieces.append("".join(part)); part = []; continue
        part.append(char)
    require(ended and not quoted, "unsupported/truncated parameter header: " + module)
    names = []
    for piece in pieces:
        require("=" in piece, "parameter without explicit source default: " + module)
        match = re.search(r"\b([A-Za-z_]\w*)\s*$", piece.split("=", 1)[0])
        require(match, "unsupported public parameter declaration: " + module)
        names.append(match[1])
    require(len(names) == len(set(names)), "duplicate public parameter: " + module)
    return set(names)


def compile_inputs(root, manifest):
    require(manifest.get("schema") == "hbm_accel_fulldie_bindings.v1", "wrong binding schema")
    for ref in manifest["inputs"]:
        pinned(root, ref)
    selected = record(root, manifest.get("selected_instances"))
    model = record(root, manifest.get("unified_model"))
    require(selected.get("design_kind") == model.get("design_kind") == "hbm_accelerator",
            "accelerator selection/model required; ablation geometry forbidden")
    require(selected.get("target") == model.get("target") == manifest["target"], "wrong target selection")
    require(selected.get("adopted") is True and selected.get("census_complete") is True,
            "owner-adopted complete source census required")
    require(model.get("slot_latency_route_ready") is True, "unified slot/latency/route model not ready")
    require(model["selection_sha256"] == manifest["selected_instances"]["sha256"],
            "model is not bound to this exact source selection")
    require(model["uarch_source"] == manifest["uarch_source"], "unified-model source mismatch")
    pinned(root, model["uarch_source"])
    for ref in selected["source_pins"]:
        pinned(root, ref)
    top_rtl = pinned(root, selected["top_source"]).decode()
    require(set(selected["top_parameters"]) == parameters(top_rtl, selected["top"]),
            "all top parameters must be explicit; no RTL defaults")
    pinned(root, model["technology_source"])
    require(selected["top_parameters"] == model["top_parameters"], "full-shape parameter mismatch")
    atom(selected["top"])
    die = box(model["die_um"], "die")
    core = box(model["core_um"], "core")
    require(contains(die, core), "core outside die")
    require(die[2]*die[3]/1e6 <= finite(model["reticle_mm2"], "reticle", True), "reticle exceeded")
    layers = set(model["routing_layers"])
    require(layers and all(re.fullmatch(r"M[1-9][0-9]*", l) for l in layers), "unknown route layers")
    sx, sy = model["macro_grid_um"]
    finite(sx, "x grid", True); finite(sy, "y grid", True)
    instances = selected["instances"]
    names = [i["name"] for i in instances]
    require(len(names) == len(set(names)) and names, "empty/duplicate instance census")
    require(set(names) == set(model["instances"]), "missing/extra model instance slots")
    counts = Counter(i["role"] for i in instances)
    required_roles = set(model["required_roles"])
    require(ROLES[manifest["target"]] <= required_roles <= counts.keys(), "missing selected target roles")
    for role in ("rf", "l2"):
        if role not in counts:
            require(selected["absent_roles"][role] == model["absent_roles"][role], "unbound absent role: " + role)
            pinned(root, selected["absent_roles"][role])
    require(dict(counts) == model["replica_counts"], "replica counts differ from unified model")
    # Contained RF/storage still belongs in the census and model, but is not
    # emitted/charged again beside the enclosing hardened SM. Its residence
    # must be proved by that SM's pinned abstract provenance.
    by_name = {i["name"]: i for i in instances}
    views = {i["name"]: record(root, i["abstract_provenance"]) for i in instances}
    placements, lefs, ports, regions = [], set(), {}, []
    child_regions = {}
    libs = {"ss": set(), "ff": set()}
    for instance in instances:
        name = instance["name"]
        atom(name); atom(instance["master"])
        ref = instance["rtl_source"]
        raw = pinned(root, ref).decode()
        require(re.search(r"\bmodule\s+"+re.escape(instance["module"])+r"\b", raw), "wrong RTL module: " + name)
        require(isinstance(instance["parameters"], dict), "unknown instance parameters: " + name)
        require(set(instance["parameters"]) == parameters(raw, instance["module"]),
                "all instance parameters must be explicit: " + name)
        slot = model["instances"][name]
        require(slot["parameters"] == instance["parameters"], "instance/model parameters differ: " + name)
        view = views[name]
        require(view.get("actual_macro_abstract") is True and view.get("pending_outline") is not True,
                "unknown/pending footprint: " + name)
        require(view["rtl_source"] == ref and view["parameters"] == instance["parameters"],
                "abstract source/parameter mismatch: " + name)
        require(view["master"] == instance["master"] and view["lef"] == instance["lef"], "wrong abstract master")
        lef = pinned(root, instance["lef"]).decode()
        master = instance["master"]
        match = re.search(r"\bMACRO\s+"+re.escape(master)+r"\s+(.*?)\bEND\s+"+re.escape(master)+r"\b", lef, re.S)
        require(match, "master absent from LEF: " + name)
        size = re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;", match[1])
        require(size, "LEF has no actual footprint: " + name)
        w, h = map(float, size.groups())
        require(w > 0 and h > 0 and [w, h] == view["size_um"], "abstract footprint mismatch: " + name)
        # Include timing views in the input bundle without declaring signoff.
        for corner in ("ss", "ff"):
            liberty = pinned(root, view["liberty"][corner]).decode()
            require(re.search(r'\bcell\s*\(\s*"?'+re.escape(master)+r'"?\s*\)', liberty),
                    "master absent from " + corner + " Liberty: " + name)
            if not instance.get("contained_in"):
                libs[corner].add(view["liberty"][corner]["path"])
        footprint = box(slot["reservation_um"], name)
        require(contains(core, footprint), "reservation outside core: " + name)
        x, y = slot["location_um"]
        finite(x, "macro x"); finite(y, "macro y")
        require(abs(x/sx-round(x/sx)) < 1e-6 and abs(y/sy-round(y/sy)) < 1e-6, "off-grid macro: " + name)
        orient = slot["orientation"]
        require(orient in ("R0", "MX", "MY", "R180"), "unpriced rotated footprint: " + name)
        require(contains(footprint, (x, y, w, h)), "undersized slot: " + name)
        parent = instance.get("contained_in")
        if parent is not None:
            require(parent in by_name and parent != name and not by_name[parent].get("contained_in"),
                    "unknown/nested physical parent: " + name)
            require(views[parent]["contained_instances"][name] == instance["abstract_provenance"],
                    "parent abstract does not prove child residence: " + name)
            px, py = model["instances"][parent]["location_um"]
            pw, ph = views[parent]["size_um"]
            require(contains((px, py, pw, ph), footprint),
                    "contained footprint outside parent: " + name)
            siblings = child_regions.setdefault(parent, [])
            require(not any(overlaps(footprint, r) for r in siblings), "overlapping contained reservations: " + name)
            siblings.append(footprint)
        else:
            require(not any(overlaps(footprint, other) for other in regions), "overlapping root reservations: " + name)
            regions.append(footprint)
            lefs.add(instance["lef"]["path"])
        pins = set(re.findall(r"\bPIN\s+(\S+)", match[1]))
        require(isinstance(instance["ports"], dict) and instance["ports"], "unknown ports: " + name)
        require(slot["ports"] == instance["ports"], "model port mismatch: " + name)
        accounted_pins = set()
        for port, info in instance["ports"].items():
            mapped = info.get("lef_pins", [port])
            require(isinstance(mapped, list) and mapped and len(mapped) == len(set(mapped)) and
                    set(mapped) <= pins, "missing abstract pin mapping: " + name + "/" + port)
            require(accounted_pins.isdisjoint(mapped), "multiply-owned abstract pins: " + name)
            accounted_pins.update(mapped)
            require(info["kind"] in ("memory", "signal", "clock_power"), "unknown port kind")
            finite(info["bits_per_cycle"], "boundary bits/cycle")
            finite(info["physical_bits"], "physical port width", True)
            require(info["physical_bits"] == len(mapped), "port width differs from physical pin map: " + name)
            if info["kind"] == "memory": finite(info["bytes_per_cycle"], "memory bytes/cycle")
        tied = set(instance["tied_ports"])
        require(accounted_pins.isdisjoint(tied) and accounted_pins | tied == pins,
                "unaccounted or multiply-owned abstract pins: " + name)
        for key in ("macs_per_cycle", "communication_intensity", "mux_demux_fanout_area_um2", "latency_cycles"):
            finite(slot[key], name + " " + key)
        ports[name] = instance["ports"]
        if parent is None:
            placements.append(dict(name=name, master=master, x=x, y=y, orientation=orient))
    require(model["boundaries"], "no composed boundary routes")
    seen_ports = set()
    for route in model["boundaries"]:
        required_bits = 0
        for name, port in route["endpoints"]:
            require(name in ports and port in ports[name] and ports[name][port]["kind"] != "clock_power",
                    "route references unknown/non-signal port")
            # Routing is charged for bus width, never reduced by a low duty cycle.
            required_bits = max(required_bits, ports[name][port]["physical_bits"])
            seen_ports.add((name, port))
        require(route["layers"] and set(route["layers"]) <= layers, "route layer not reserved")
        required = math.ceil(required_bits * finite(route["tracks_per_bit"], "tracks/bit", True))
        require(required <= finite(route["required_tracks"], "priced route tracks") <=
                finite(route["capacity_tracks"], "channel tracks", True), "boundary route over capacity/underpriced")
        for key in ("wire_cycles", "cdc_cycles", "credit_cycles", "composed_latency_cycles"):
            finite(route[key], "route " + key)
    require(seen_ports == {(n,p) for n, ps in ports.items() for p, info in ps.items() if info["kind"] != "clock_power"},
            "unpriced/unrouted instance ports")
    require(model["layer_reservations"], "missing routing/PG layer reservations")
    for region in model["layer_reservations"]:
        require(region["layers"] and set(region["layers"]) <= layers, "unbound reservation layers")
        require(contains(die, box(region["box_um"], "layer reservation")), "layer reservation outside die")
        require(region["purpose"] in ("signal", "power", "clock", "keepout"), "unknown reservation purpose")
    finite(model["composed_token_cycles"], "composed token latency", True)
    require(model["clock_domains_ns"], "unpriced clock domains")
    for period in model["clock_domains_ns"].values(): finite(period, "clock period", True)
    require(model["uncertainty_ps"] == {"setup_ss": 60, "hold_ff": 25}, "uncertainty policy changed")
    return dict(top=selected["top"], die_um=die, core_um=core, lefs=sorted(lefs), placements=placements,
                ports=ports, boundaries=model["boundaries"], reservations=model["layer_reservations"],
                liberty={k:sorted(v) for k,v in libs.items()}, clock_domains_ns=model["clock_domains_ns"],
                replica_counts=dict(counts), composed_token_cycles=model["composed_token_cycles"],
                signoff=False, model_ref=manifest["unified_model"], selection_ref=manifest["selected_instances"])


def emit(out, result):
    require(not out.exists(), "refuse to overwrite previous floorplan inputs")
    # All validation completed before creating the output directory.
    out.mkdir(parents=True)
    (out/"composition.json").write_text(json.dumps(result, indent=2)+"\n")
    (out/"lef_files.txt").write_text("\n".join(result["lefs"])+"\n")
    for corner, paths in result["liberty"].items():
        (out/("liberty_"+corner+".txt")).write_text("\n".join(paths)+"\n")
    # Slot boxes use x/y/width/height; OpenROAD areas use xmin/ymin/xmax/ymax.
    def area(b): return " ".join(str(v) for v in (b[0], b[1], b[0]+b[2], b[1]+b[3]))
    (out/"floorplan.tcl").write_text("# Use only after loading the selected netlist and listed views.\n"+
        f'initialize_floorplan -die_area {{{area(result["die_um"])}}} -core_area {{{area(result["core_um"])}}}\n')
    tcl = ["# Source-selected accelerator macros only; this file launches no tool.",
           "set ot_block [ord::get_db_block]", "set ot_macros 0",
           "foreach inst [$ot_block getInsts] { if {[[$inst getMaster] isBlock]} { incr ot_macros } }"]
    tcl += [f'if {{$ot_macros != {len(result["placements"])}}} {{ error "full-die macro census mismatch" }}']
    for p in result["placements"]:
        tcl += [f'set ot_inst [$ot_block findInst {atom(p["name"])}]',
                'if {$ot_inst eq "NULL"} { error "selected instance absent" }',
                f'if {{[[$ot_inst getMaster] getName] ne {atom(p["master"])}}} {{ error "selected master mismatch" }}']
    for p in result["placements"]:
        tcl += [f'place_macro -macro_name {atom(p["name"])} -location {{{p["x"]} {p["y"]}}} -orientation {p["orientation"]}']
    (out/"macro_place.tcl").write_text("\n".join(tcl)+"\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--bindings", type=Path)
    ap.add_argument("--target", choices=sorted(ROLES), default="deepseek")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    try:
        manifest = json.loads((args.bindings or args.root/DEFAULT).read_text())
        manifest = dict(manifest, **manifest["targets"][args.target], target=args.target)
        result = compile_inputs(args.root, manifest)
        emit(args.out, result)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps(dict(status="BLOCKED", floorplan_emitted=False, reason=str(exc),
                              required_bindings=locals().get("manifest", {}).get("required_bindings", [])), indent=2))
        ap.exit(2, "HBM full-die emission REFUSED: "+str(exc)+"\n")


if __name__ == "__main__":
    main()
