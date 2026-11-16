#!/usr/bin/env python3
"""split_lane_reference_export: freeze the lane payloads of a BASE bind for a type split (FABLE-FIX-KV-PV-CUT 11-16).

    python3 tools/die_plan/split_lane_reference_export.py REF_OUT.json GROUPS.json -- bind PLAN --out DIR --asbuilt AB ...

Runs the ordinary bind of the UNSPLIT plan up to build_buses (same arguments as bind.py after "--"), then writes the
opentallas.split_lane_reference.v1 file that split_bind_routes.prefill / split_source_guard.validate_guard read
(asbuilt key split_lane_reference of the SPLIT plan): every plan lane with its symbolic drivers in lane-bit order, the
driver cells' fingerprints and partitions, the source-rule / logical-graph hashes and the RTL receipts of the driver
modules.  GROUPS.json = {base partition: [piece partitions]} of the split (an unsplit partition is its own group);
"-" = every partition its own group: the form type_split takes (spec lane_reference), it fills in the pieces.

Why: bind.build_buses packs as-built bits onto lanes greedily; after a split the lane graph has cut lanes, the greedy
packing changes, old lanes go empty (native stations: "expected one outgoing lane") and census-sized cut lanes
overflow (UNPLANNED).  With the reference the split bind first puts every old lane's measured payload back.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def build(b, all_lanes, groups):
    import bind_elab as E
    import split_bind_routes as SBR
    import split_source_guard as SSG
    F = b.F
    known = set(b.parts)
    part_groups = {p: [p] for p in sorted(known)}
    for base, pieces in groups.items():
        if base not in known:
            raise ValueError(f"group {base}: not a partition of the base plan")
        part_groups[base] = list(pieces)
    lanes, cells = [], {}
    for L in sorted(all_lanes, key=lambda L: L["id"]):
        keys = [] if L.get("plan") else [k for k, _i in sorted(L["carried"].items(), key=lambda kv: kv[1])]
        drivers = []
        for ci, pn, bit in keys:
            c = F.cells[ci]
            cells.setdefault(c.path, dict(fingerprint=SBR.cell_fingerprint(c), part=b.cpart[ci]))
            drivers.append([c.path, pn, bit])
        lanes.append(dict(id=L["id"], src=L["src"], dst=L["dst"], drivers=drivers))
    extra = list(getattr(b, "extra_lib", []))
    files = list(b.ab.get("files", [])) + extra
    absolute = lambda f: Path(f) if Path(f).is_absolute() else Path(b.base) / f
    prefer = [str(absolute(f)) for f in b.ab.get("prefer", [])] + [str(absolute(f)) for f in extra]
    index = E.module_index(b.ab.get("rtl_roots", ["rtl"]), files, b.base)
    base = Path(b.base).resolve()
    receipts = []
    for module in sorted({F.cells[ci].module for L in all_lanes if not L.get("plan") for ci, _pn, _bit in L["carried"]}):
        chosen, _amb = E.pick(index, module, prefer)
        if chosen is None:
            continue                      # an elaborated / generated master: covered by the cell fingerprints
        body = E.module_body(Path(chosen), module)
        if not body:
            continue
        p = Path(chosen).resolve()
        receipts.append(dict(kind="module", module=module, sha256=hashlib.sha256(body.encode()).hexdigest(),
                             file=str(p.relative_to(base)) if p.is_relative_to(base) else str(p)))
    return dict(schema=SBR.SCHEMA, part_groups=part_groups, cells=cells, lanes=lanes,
                payload_sha256=SBR.payload_sha256(lanes), source_rules_sha256=SSG.source_rules_fingerprint(b),
                source_graph_sha256=SSG.logical_graph_fingerprint(b), rtl_sources=receipts)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv or argv.index("--") != 2:
        print(__doc__)
        return 2
    out, groups = Path(argv[0]), ({} if argv[1] == "-" else json.loads(Path(argv[1]).read_text()))
    import bind
    got = {}
    plan_lanes, build_buses = bind.Binder.plan_lanes, bind.Binder.build_buses

    def lanes_hook(self):
        got["lanes"] = plan_lanes(self)
        return got["lanes"]

    def buses_hook(self):
        build_buses(self)
        ref = build(self, [L for ls in got["lanes"].values() for L in ls], groups)
        out.write_text(json.dumps(ref, separators=(",", ":")) + "\n")
        print("SPLIT_LANE_REFERENCE " + json.dumps(dict(file=str(out), lanes=len(ref["lanes"]), cells=len(ref["cells"]),
              bits=sum(len(r["drivers"]) for r in ref["lanes"]), rtl_sources=len(ref["rtl_sources"]),
              payload_sha256=ref["payload_sha256"], bind_errors=len(self.errors))), flush=True)
        raise SystemExit(0)
    bind.Binder.plan_lanes, bind.Binder.build_buses = lanes_hook, buses_hook
    sys.argv = ["bind.py"] + argv[3:]
    return bind.main()


if __name__ == "__main__":
    sys.exit(main())
