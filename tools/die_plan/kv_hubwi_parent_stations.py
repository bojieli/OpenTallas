#!/usr/bin/env python3
"""KV-HR-DEEPCLK 11-24 (COORD ruling 03:1x): registered boundary stations and input lockup latches inside the kv3_hub_Wi
clustered host parent (physical/die_plan/qwen_kvsys/bind/kv_host_wi/parent.sv).

Why: the 21 qkd_hr_* hard cores of kv3_hub_Wi sit INSIDE the bound leaf u_host (form-S parent), so neither
asbuilt.land_intra_stations nor clock.core_input_lockup reaches them (both act on bound leaves only; the hub_Wi RTL of a
lockup plan was byte-equal to the plain one).  Core-to-core and core-to-glue boundary paths with less than the 150 ps
wire + margin budget (signed hr libs, early-tap credit) get a structural fix here, in the parent generator step:

  station  every output port of a core instance whose name starts with a listed prefix: the core pin drives a new wire
           and a D-stage register (kvhw_dly, reset-less, (* keep *)) drives the ORIGINAL net, so every load of that net
           (cores and glue alike) sees the bundle `stages` cycles later, together (+cycles pre-approved, declared in the
           receipt for LEC and the compiler).
  latch    listed input ports of a core instance: a negative-level lockup latch (kvhw_lk, transparent while the core
           clock is low, 0 cycles) between the net and the pin: the glue -> core hold check gains T/2.

The generator reads the pristine parent (parent_src.sv, the KV-HOST-WI step-4 output) and the wrapper port directions
(wrappers_s/<module>/<module>.sv), and writes parent.sv + parent_stations.json.  Fail closed: unknown instance, a prefix
or port that matches nothing, a station on an input, a latch on an output, a ready/reset port (never stationed: a late
ready breaks valid/ready flow control), an output connection that is not a plain net / slice / concatenation of nets,
or an input that already carries a latch.

usage: kv_hubwi_parent_stations.py --dir DIR [--spec DIR/parent_stations_spec.json] [--check]
       (--check: regenerate in memory and exit 1 when parent.sv / parent_stations.json differ)
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

MARK = "// KV-HR-DEEPCLK parent_stations:"
NEVER = re.compile(r"(^|_)(rdy|ready|rst_n|rst)$")
MODS = """
// KV-HR-DEEPCLK: D reset-less register stages (boundary station, +D cycles declared in parent_stations.json)
module kvhw_dly #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
  (* keep *) reg [W-1:0] r [0:D-1];
  integer k;
  always @(posedge clk) begin
    r[0] <= d;
    for (k = 1; k < D; k = k + 1) r[k] <= r[k-1];
  end
  assign q = r[D-1];
endmodule
// KV-HR-DEEPCLK: negative-level lockup latch (transparent while clk is low; 0 cycles)
module kvhw_lk #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
  always @* if (!clk) q = d;
endmodule
"""


class GenError(ValueError):
    pass


def wrapper_ports(text):
    """-> {port: (dir, width)} from a generated hr wrapper text (input/output wire [h:l] name;)"""
    out = {}
    for m in re.finditer(r"^\s*(input|output)\s+wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)\s*;", text, re.M):
        d, h, l, n = m.groups()
        out[n] = (d, abs(int(h) - int(l)) + 1 if h is not None else 1)
    return out


NET = r"(?:\\\S+\s*|[A-Za-z_][\w$]*\s*)(?:\[\d+(?::\d+)?\]\s*)?"
LVALUE = re.compile(rf"^\s*(?:{NET}|\{{\s*{NET}(?:,\s*{NET})*\}})\s*$")


def generate(src, wrappers_dir, spec):
    """wrappers from DIR/<module>/<module>.sv"""
    return generate_text(src, lambda mod: (Path(wrappers_dir) / mod / f"{mod}.sv").read_text(), spec)


def generate_text(src, wrappers, spec):
    """-> (parent text, receipt dict); GenError on any rule.  wrappers: {module: wrapper text} or module -> text"""
    load = wrappers.__getitem__ if isinstance(wrappers, dict) else wrappers
    if MARK in src:
        raise GenError("source parent already carries parent_stations output")
    insts = {}
    for m in re.finditer(r"\n(\s*)(qkd_hr_\w+)\s+(host__\w+)\s*\((.*?)\n\s*\);", src, re.S):
        insts[m.group(3)] = (m.group(2), m.start(4), m.end(4))
    rows, edits, decl, cells = [], [], [], []
    plan = [(s, "station") for s in spec.get("stations", [])] + [(l, "latch") for l in spec.get("latches", [])]
    for item, kind in plan:
        inst = item["inst"]
        if inst not in insts:
            raise GenError(f"{kind} {inst}: no such core instance in the parent")
        mod, a, b = insts[inst]
        ports = wrapper_ports(load(mod))
        body = src[a:b]
        conns = {m.group(1): m for m in re.finditer(r"\.(\w+)\((.*?)\)(?=,?\s*$)", body, re.M)}
        ck = conns.get("ck")
        if ck is None:
            raise GenError(f"{inst}: no .ck connection")
        clk = ck.group(2).strip()
        if kind == "station":
            names = sorted(p for p, (d, _) in ports.items() if d == "output" and any(p.startswith(x) for x in item["prefixes"]))
            empty = [x for x in item["prefixes"] if not any(p.startswith(x) for p in names)]
            if empty:
                raise GenError(f"station {inst}: prefix(es) {empty} match no output port")
            D = int(item.get("stages", 1))
            if D < 1:
                raise GenError(f"station {inst}: stages must be >= 1")
        else:
            names = list(item["ports"])
            D = 0
        for p in names:
            if p not in ports:
                raise GenError(f"{kind} {inst}.{p}: not a port of {mod}")
            d, w = ports[p]
            if NEVER.search(p):
                raise GenError(f"{kind} {inst}.{p}: ready / reset ports are never stationed or latched")
            if (kind == "station") != (d == "output"):
                raise GenError(f"{kind} {inst}.{p}: is an {d}")
            m = conns.get(p)
            if m is None or not m.group(2).strip():
                raise GenError(f"{kind} {inst}.{p}: unconnected")
            expr = m.group(2).strip()
            if kind == "station" and not LVALUE.match(expr):
                raise GenError(f"station {inst}.{p}: connection {expr!r} is not a net / slice / concatenation of nets")
            tag = f"{inst[len('host__'):]}__{p}"
            wire = f"kvhw_{'st' if kind == 'station' else 'lk'}_{tag}"
            decl.append(f"  wire [{w - 1}:0] {wire};")
            if kind == "station":
                cells.append(f"  kvhw_dly #(.W({w}), .D({D})) u_{wire} (.clk({clk}), .d({wire}), .q({expr} ));")
            else:
                cells.append(f"  kvhw_lk #(.W({w})) u_{wire} (.clk({clk}), .d({expr} ), .q({wire}));")
            edits.append((a + m.start(2), a + m.end(2), wire))
            rows.append(dict(kind=kind, inst=inst, module=mod, port=p, dir=d, width=w, cycles=D, clk=clk, net=expr,
                             cell=f"u_{wire}"))
    if not rows:
        raise GenError("empty spec")
    out = src
    for s, e, wire in sorted(edits, reverse=True):
        out = out[:s] + wire + out[e:]
    end = out.rindex("endmodule")
    out = (out[:end] + f"{MARK} {len(rows)} ports ({sum(r['kind'] == 'station' for r in rows)} stationed, "
           f"{sum(r['kind'] == 'latch' for r in rows)} latched)\n" + "\n".join(decl + cells) + "\n" + out[end:])
    out = out.rstrip("\n") + "\n" + MODS
    rec = dict(schema="kv-hubwi.parent_stations.v1", spec=spec,
               source_sha256=hashlib.sha256(src.encode()).hexdigest(),
               parent_sha256=hashlib.sha256(out.encode()).hexdigest(), rows=rows,
               declared_cycles={f"{r['inst']}.{r['port']}": r["cycles"] for r in rows if r["kind"] == "station"})
    return out, rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--spec")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    d = Path(a.dir)
    spec = json.loads(Path(a.spec or d / "parent_stations_spec.json").read_text())
    try:
        out, rec = generate((d / "parent_src.sv").read_text(), d / "wrappers_s", spec)
    except GenError as e:
        print(f"PARENT_STATIONS_REFUSED {e}")
        return 2
    txt = json.dumps(rec, indent=1) + "\n"
    if a.check:
        ok = (d / "parent.sv").read_text() == out and (d / "parent_stations.json").read_text() == txt
        print("PARENT_STATIONS_CHECK", "OK" if ok else "STALE")
        return 0 if ok else 1
    (d / "parent.sv").write_text(out)
    (d / "parent_stations.json").write_text(txt)
    print(f"PARENT_STATIONS {len(rec['rows'])} ports parent {rec['parent_sha256'][:12]} from {rec['source_sha256'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
