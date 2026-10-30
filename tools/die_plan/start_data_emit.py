#!/usr/bin/env python3
"""Opt-in ordinary START/RAW data buffers with explicit, checked physical homes.

This does not choose a clock, add a register, invent a source-driver location, or
qualify a timing model. A route manifest must name the actual mapped source INV
and QN pins, each ordinary BUF8, and every pin-to-pin route. Missing source homes
are an error. The default START emitter never invokes this module.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

SCHEMA = "ot_start_data/1"
BUF = "BUFx8_ASAP7_75t_R"
INV = {"start": "INVx1_ASAP7_75t_R", "raw": "INVx3_ASAP7_75t_R"}
EPS = 1e-6


class DataError(ValueError):
    pass


def point(p):
    if len(p) != 2 or not all(math.isfinite(float(v)) for v in p):
        raise DataError(f"invalid physical point: {p}")
    return tuple(float(v) for v in p)


def distance(a, b):
    return sum(abs(x-y) for x, y in zip(point(a), point(b)))


def ident(src, dst, signal):
    return "sd_" + hashlib.sha256((src + "\0" + dst + "\0" + signal).encode()).hexdigest()[:20]


def key(e):
    return e["src_region"], e["dst_region"], e["signal"]


def box(c, library):
    w, h = library[c["master"]]["size_um"]
    x, y = point(c["xy_um"])
    if c["orient"] not in ("R0", "MX", "MY", "R180"):
        raise DataError("DATA cell must retain a native horizontal-row orientation")
    return x, y, x+float(w), y+float(h)


def pin(c, name, library):
    w, h = library[c["master"]]["size_um"]
    x, y = point(library[c["master"]]["pins_um"][name])
    if c["orient"] in ("MY", "R180"):
        x = float(w)-x
    if c["orient"] in ("MX", "R180"):
        y = float(h)-y
    ox, oy = point(c["xy_um"])
    return ox+x, oy+y


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0])+EPS and min(a[3], b[3]) > max(a[1], b[1])+EPS


def crosses(a, b, r):
    """An axis-aligned wire crosses the INTERIOR of a declared hard exclusion."""
    x, y = point(a); X, Y = point(b)
    if abs(x-X) <= EPS:
        return r[0]+EPS < x < r[2]-EPS and min(max(y, Y), r[3]) > max(min(y, Y), r[1])+EPS
    if abs(y-Y) <= EPS:
        return r[1]+EPS < y < r[3]-EPS and min(max(x, X), r[2]) > max(min(x, X), r[0])+EPS
    raise DataError("DATA routes require explicit legal axis-aligned bends")


def route_length(route, a, b, forbidden):
    if len(route) < 2 or distance(route[0], a) > EPS or distance(route[-1], b) > EPS:
        raise DataError("pin-to-pin route endpoints do not match literal cell pins")
    total = 0.0
    for p, q in zip(route, route[1:]):
        point(p); point(q)
        if distance(p, q) <= EPS:
            raise DataError("zero-length/duplicated route vertex")
        for r in forbidden:
            if crosses(p, q, r):
                raise DataError(f"DATA route crosses a hard exclusion: {r}")
        # Also reject diagonal segments when no hard exclusion was supplied.
        crosses(p, q, (1e30, 1e30, 1e30+1, 1e30+1))
        total += distance(p, q)
    return total


def validate(doc, site=None):
    """Validate literal hardware and routes; return a truthful source-only receipt.

    library geometry must be extracted from the actual locked LEF/OpenDB. A caller
    can omit a SiteMap for source/FV preparation; this never becomes physical PASS.
    """
    if doc.get("schema") != SCHEMA:
        raise DataError("unknown START DATA manifest schema")
    if doc.get("added_register_cycles", 0) or doc.get("added_flops", 0):
        raise DataError("DATA buffering may not add register cycles or flops")
    if not re.fullmatch(r"[0-9a-f]{64}", doc.get("library_source_sha256", "")):
        raise DataError("locked library geometry source SHA256 is required")
    if not doc.get("edges"):
        raise DataError("empty DATA inventory")
    library = doc["cell_library"]
    if BUF not in library or set(library[BUF]["pins_um"]) != {"A", "Y"}:
        raise DataError("actual BUF8 A/Y pin geometry is required")
    occupied = [tuple(r) for r in doc.get("occupied_rects_um", [])]
    forbidden = [tuple(r) for r in doc.get("wire_exclusions_um", [])]
    seen, names, counts, source_records = set(), set(), {}, {}
    longest = 0.0
    for e in doc["edges"]:
        k = key(e)
        if k in seen or e["signal"] not in INV:
            raise DataError("duplicate/unknown START DATA edge")
        seen.add(k)
        src = e["source_inv"]
        if src["master"] != INV[e["signal"]]:
            raise DataError(f"wrong actual mapped source inverter for {k}")
        for n in [src.get("instance", ""), src.get("ff_instance", ""), src.get("kept_buf2_instance", "")]:
            if n and not re.fullmatch(r"[A-Za-z0-9_./$\[\]-]+", n):
                raise DataError("unsupported mapped instance name")
        if not src.get("instance") or not src.get("ff_instance"):
            raise DataError("actual source INV and QN flop identities are required")
        point(src["xy_um"]); point(src["ff_xy_um"])
        if src["orient"] not in ("R0", "MX", "MY", "R180"):
            raise DataError("actual source gate orientation required")
        if distance(src["qn_pin_um"], src["input_pin_um"]) > 1+EPS:
            raise DataError("QN to source INV exceeds the priced 1um bound")
        sk = e["src_region"], e["signal"]
        # One source, one actual gate record. Never silently use different homes
        # or duplicate an already existing RAW kept-load cell for sibling edges.
        if sk in source_records and source_records[sk] != src:
            raise DataError("inconsistent source gate/home records")
        source_records[sk] = src
        if e["signal"] == "raw" and not src.get("kept_buf2_instance"):
            raise DataError("RAW actual kept BUF2 load identity is required")
        counts[sk] = counts.get(sk, 0)+1
        if not e.get("cells"):
            raise DataError("each outgoing edge needs its own first ordinary BUF8")
        endpoints = [point(src["output_pin_um"])]
        for j, c in enumerate(e["cells"]):
            expected = ident(*k) + "_b" + str(j)
            if c["instance"] != expected or expected in names or c["master"] != BUF:
                raise DataError("nonunique or unexpected literal BUF8 instance/master")
            names.add(expected)
            r = box(c, library)
            sx, sy = doc["site_grid_um"]
            gx, gy = doc.get("site_origin_um", (0, 0))
            if abs((r[0]-gx)/sx-round((r[0]-gx)/sx)) > EPS or abs((r[1]-gy)/sy-round((r[1]-gy)/sy)) > EPS:
                raise DataError("buffer does not occupy a native row/site")
            if any(overlaps(r, q) for q in occupied):
                raise DataError("DATA buffer overlaps a declared cell/PG exclusion")
            if site and not all(site.legal(q) for q in ((r[0], r[1]), (r[0], r[3]), (r[2], r[1]), (r[2], r[3]))):
                raise DataError("DATA buffer violates actual Plan SiteMap")
            occupied.append(r)
            endpoints += [pin(c, "A", library), pin(c, "Y", library)]
        endpoints.append(point(e["capture_pin_um"]))
        pairs = list(zip(endpoints[::2], endpoints[1::2]))
        if len(e["routes_um"]) != len(pairs):
            raise DataError("one literal pin-to-pin route is required per wire segment")
        lengths = [route_length(r, a, b, forbidden) for r, (a, b) in zip(e["routes_um"], pairs)]
        if lengths[0] > 3+EPS or max(lengths[1:], default=0) > 100+EPS:
            raise DataError("source-to-first BUF8 exceeds3um or buffered segment exceeds100um")
        longest = max(longest, *lengths)
    for sk, n in counts.items():
        if source_records[sk].get("outgoing_edges") != n:
            raise DataError("actual outgoing fanout and first-driver inventory differ")
    return dict(schema=SCHEMA, edges=len(seen), buffers=len(names), added_flops=0, added_register_cycles=0,
                max_segment_um=longest, site_checked=bool(site), physical_qualified=False,
                holds=["actual synthesis retention/source-gate/load audit", "common native clock ownership and quantitative repricing",
                       "actual routed PG/pin access and related-pair timing", "cold/warm full source assembly coherence"])


def body(e, source):
    """Literal noninverting technology cells; no substitute flop or timing bypass."""
    prev = source; out = []
    for c in e["cells"]:
        wire = c["instance"] + "_q"
        out += [f"    (* keep = \"true\" *) wire {wire};",
                f"    (* keep = \"true\", dont_touch = \"true\" *) {BUF} {c['instance']} (.A({prev}), .Y({wire}));"]
        prev = wire
    return out, prev


def apply(stages, text, manifest, site=None):
    """Buffer ALL emitted virtual START/RAW edges, or reject partial coverage.

    Existing native-to-native direct ports are outside this module's ownership;
    refuse to qualify them by omission. No clock net/port or FF equation changes.
    """
    receipt = validate(manifest, site)
    if stages.get("direct_ports"):
        raise DataError("direct native START edges need an explicit top-level DATA assembly owner")
    edges = {key(e): e for e in manifest["edges"]}
    by = {s["region"]: s for s in stages["stages"]}
    sn = lambda r: "st_"+by[r]["id"]+"_start" if r in by else "rs_"+re.sub(r"\W", "_", r)
    rn = lambda r: "st_"+by[r]["id"]+"_rraw" if r in by else "rraw_"+re.sub(r"\W", "_", r)
    required, additions = set(), []

    def replace_line(instance, old, new):
        nonlocal text
        lines = text.splitlines(keepends=True)
        indices = [i for i, line in enumerate(lines) if re.search(r"\b"+re.escape(instance)+r"\s*\(", line)]
        if len(indices) != 1 or lines[indices[0]].count(old) != 1:
            raise DataError(f"actual emitted connection not found exactly once: {instance} {old}")
        lines[indices[0]] = lines[indices[0]].replace(old, new)
        text = "".join(lines)

    def chain(src, dst, signal, net):
        k = src, dst, signal; required.add(k)
        if k not in edges:
            raise DataError(f"unbuffered emitted DATA edge: {k}")
        lines, q = body(edges[k], net); additions.extend(lines)
        return q

    for s in stages["stages"]:
        if s["root"]:
            continue
        q = chain(s["parent"], s["region"], "start", sn(s["parent"]))
        replace_line("u_st_"+s["id"], ".p_start("+sn(s["parent"])+")", ".p_start("+q+")")
        if stages.get("reset_wave"):
            q = chain(s["parent"], s["region"], "raw", rn(s["parent"]))
            replace_line("u_rst_"+s["id"], ".d("+rn(s["parent"])+")", ".d("+q+")")
    for e in stages["die_outputs"]:
        src = next(s["region"] for s in stages["stages"] if s["id"] == e["stage"])
        q = chain(src, e["dst_region"], "start", sn(src))
        old = f"    assign {e['net']} = {sn(src)};"
        if text.count(old) != 1:
            raise DataError("native START output connection is not unique")
        text = text.replace(old, f"    assign {e['net']} = {q};")
    if set(edges) != required:
        raise DataError("DATA manifest contains edges not owned by this emitted graph")
    i = text.index("endmodule")
    text = text[:i]+"\n"+"\n".join(additions)+"\n"+text[i:]
    stages = dict(stages, data_buffers=dict(receipt, manifest_schema=SCHEMA))
    return stages, text


def placement_tcl(doc):
    """Explicit placements and fail-closed retention; no CTS directive or clock edit."""
    out = ["# Generated ordinary START DATA buffers; no clock changes.",
           "if {![info exists OT_START_DATA_PREFIX]} {set OT_START_DATA_PREFIX {}}",
           "set sd_block [ord::get_db_block]", "set sd_units [[ord::get_db_tech] getDbUnitsPerMicron]"]
    # Validate actual mapped source gate, QN driver and complete sink inventory.
    # Listing every sink is essential: native START may also drive local readers.
    checked = set()
    for e in doc["edges"]:
        src = e["source_inv"]
        sk = (e["src_region"], e["signal"])
        if sk not in checked:
            checked.add(sk)
            out += [f"set sd_src [$sd_block findInst {{{src['instance']}}}]",
                    f'if {{$sd_src eq "NULL" || [[$sd_src getMaster] getName] ne "{src["master"]}"}} {{error "START DATA actual source INV mismatch"}}',
                    "set sd_a [$sd_src findITerm A]", "set sd_y [$sd_src findITerm Y]",
                    'if {$sd_a eq "NULL" || $sd_y eq "NULL" || [$sd_a getNet] eq "NULL" || [$sd_y getNet] eq "NULL"} {error "START DATA source pins unconnected"}',
                    f"set sd_ff [$sd_block findInst {{{src['ff_instance']}}}]",
                    'if {$sd_ff eq "NULL"} {error "START DATA actual source flop absent"}',
                    'set sd_qn [$sd_ff findITerm QN]',
                    'if {$sd_qn eq "NULL" || [$sd_qn getNet] ne [$sd_a getNet]} {error "START DATA source not actual QN-to-INV"}',
                    f"set sd_expect [list [expr {{round({src['xy_um'][0]}*$sd_units)}}] [expr {{round({src['xy_um'][1]}*$sd_units)}}]]",
                    'if {[$sd_src getLocation] ne $sd_expect} {error "START DATA source INV home differs from priced manifest"}',
                    f"set sd_expect [list [expr {{round({src['ff_xy_um'][0]}*$sd_units)}}] [expr {{round({src['ff_xy_um'][1]}*$sd_units)}}]]",
                    'if {[$sd_ff getLocation] ne $sd_expect} {error "START DATA source FF home differs from priced manifest"}',
                    f'if {{[$sd_src getOrient] ne "{src["orient"]}"}} {{error "START DATA source INV orientation mismatch"}}',
                    'set_dont_touch [get_cells [$sd_src getName]]',
                    'set_dont_touch [get_cells [$sd_ff getName]]',
                    'set sd_sinks {}',
                    'foreach sd_t [[$sd_y getNet] getITerms] {if {[$sd_t getIoType] eq "INPUT"} {lappend sd_sinks "[[$sd_t getInst] getName]/[[$sd_t getMTerm] getName]"}}',
                    'foreach sd_t [[$sd_y getNet] getBTerms] {lappend sd_sinks "PORT/[$sd_t getName]"}']
            expected = src.get("all_output_sinks")
            if not expected:
                raise DataError("actual complete source output sink inventory required for placement audit")
            for n in expected:
                if not re.fullmatch(r"[A-Za-z0-9_./$\[\]-]+", n):
                    raise DataError("unsupported mapped sink name")
            out += ["set sd_expected {"+" ".join(expected)+"}",
                    'if {[lsort $sd_sinks] ne [lsort $sd_expected]} {error "START DATA unpriced source output loads"}']
            if e["signal"] == "raw":
                out += [f"set sd_keep [$sd_block findInst {{{src['kept_buf2_instance']}}}]",
                        'if {$sd_keep eq "NULL" || [[$sd_keep getMaster] getName] ne "BUFx2_ASAP7_75t_R" || [[$sd_keep findITerm A] getNet] ne [$sd_y getNet]} {error "START DATA kept RAW BUF2 missing/wrong load"}']
        for c in e["cells"]:
            x, y = point(c["xy_um"]); n = c["instance"]
            out += [f"set sd_name $OT_START_DATA_PREFIX{n}", "set sd_i [$sd_block findInst $sd_name]",
                    f'if {{$sd_i eq "NULL" || [[$sd_i getMaster] getName] ne "{BUF}"}} {{error "START DATA missing/wrong retained BUF8: $sd_name"}}',
                    f"$sd_i setOrient {c['orient']}", f"$sd_i setLocation [expr {{round({x:.9f}*$sd_units)}}] [expr {{round({y:.9f}*$sd_units)}}]",
                    "$sd_i setPlacementStatus FIRM", "set_dont_touch [get_cells $sd_name]",
                    "foreach sd_t [$sd_i getITerms] {if {[$sd_t getNet] ne {NULL}} {set_dont_touch [get_nets [[$sd_t getNet] getName]]}}"]
    return "\n".join(out)+"\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest"); p.add_argument("--out", required=True); p.add_argument("--plan")
    a = p.parse_args(argv); d = json.loads(Path(a.manifest).read_text()); site = None
    if a.plan:
        import schema as S
        import die_trial as DT
        site = DT.SiteMap(S.Plan(S.load(a.plan)))
    r = validate(d, site); o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    (o/"start_data.tcl").write_text(placement_tcl(d))
    (o/"start_data_check.json").write_text(json.dumps(r, indent=2)+"\n")
    print(json.dumps(r))


if __name__ == "__main__":
    main()
