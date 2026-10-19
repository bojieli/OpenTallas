#!/usr/bin/env python3
"""Face landing standard for tile reset / late input pins (HKV-RSTCAP 2026-10-19; coordinator: ONE shared stage for every
KV tile whose native audit fails capture on rst_n or other late inputs -- hr_core_order 386.9, kvs_attn 383.3,
astk_rly_296 277.4, hr_core_queue 274.0 ps against 190).

The standard (two shared RTL modules, one generated wrapper per tile, never hand copied):
  * reset: every declared reset port drives only rtl/lib/ot_rst_relay.sv (REGIONS 1, SYNC 2, TREE 1): asynchronous,
    immediate assertion; registered release +3 rising edges of the tile clock; the relay flop then fans out with a full
    cycle (reg -> async clear).  Zero steady-state cycles; the die startup calendar waits 3 more edges after release.
  * late data pins (spec "land"): rtl/lib/ot_pin_land.sv -- one capture flop per bit at the face (no reset), LAT edges on
    the whole bus; tools/ref_tile io_flop_at_pins anchors each flop at its pin.  The die schedule prices LAT.

Kit hook: a ref_tile spec carrying
    "face_land": {"core": "<original top>", "core_src": "<file that defines it>",
                  "reset_ports": ["rst_n"], "land": {"fin": 1, "i_ctl": 1}, "reason": "..."}
is completed by `ref_tile.py gen` (apply()): top := <core>_fl, the wrapper rtl/lib/face_land/<core>_fl.sv is (re)written
from the core's port list, and the three files join the sources.  The kit keeps its name (same element, same pins), so
the re-route of a CLOSED view cites reroute_reason native_capture with the committed audit receipt.

Bench (exact contract, Verilator; one generic vehicle for every wrapped tile):
    face_land.py bench --spec physical/ref_tile/<kit>/spec.json --out DIR [--mut 0|1|2] [--cycles N]
DUT = <core>_fl; REF = <core> with an independent reset model (async assert, release on the 3rd rising edge) and the
landed buses delayed LAT edges in the bench.  Every output is compared at every negative edge AND right after every
asynchronous assertion, over many reset epochs (long, short and sub-cycle pulses), random inputs on every other pin.
    PASS: FACE_LAND PASS top=<core>_fl ... errors=0
    --mut 1 (reset relay bypassed) / --mut 2 (landing bypassed) must print FACE_LAND FAIL (mutant witnesses).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = "rtl/lib/face_land"
RELAY = "rtl/lib/ot_rst_relay.sv"
LAND = "rtl/lib/ot_pin_land.sv"
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
RELEASE_EDGES = 3          # ot_rst_relay SYNC_STAGES 2 + TREE_STAGES 1


class FaceLandError(Exception):
    pass


def _strip_comments(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", " ", t)


def module_text(src: Path, top: str) -> str:
    t = _strip_comments(src.read_text(errors="replace"))
    m = re.search(r"\bmodule\s+" + re.escape(top) + r"\b(.*?)\bendmodule\b", t, re.S)
    if not m:
        raise FaceLandError(f"module {top} not found in {src}")
    return m.group(1)


def _split_top(s: str, sep: str = ",") -> list[str]:
    out, depth, cur = [], 0, []
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


DECL = re.compile(r"^(input|output|inout)\b\s*(?:wire|reg|logic)?\s*(signed)?\s*(\[[^\]]+\])?\s*(.*)$", re.S)


def ports(src: Path, top: str) -> list[tuple[str, str, str]]:
    """[(direction, range or '', name)] in header order; ANSI and non-ANSI headers."""
    body = module_text(src, top)
    body = re.sub(r"^\s*#\s*\(.*?\)\s*(?=\()", "", body, flags=re.S)       # parameter port list
    m = re.match(r"\s*\((.*?)\)\s*;", body, re.S)
    if not m:
        raise FaceLandError(f"{top}: no port list")
    head = m.group(1)
    out = []
    if re.search(r"\b(input|output|inout)\b", head):
        d = r = None
        for item in _split_top(head):
            dm = DECL.match(item)
            if dm:
                d, r, name = dm.group(1), dm.group(3) or "", dm.group(4).strip()
            else:
                name = item
            if d is None:
                raise FaceLandError(f"{top}: port {item!r} before any direction")
            out.append((d, r, name.split("=")[0].strip()))
        return out
    names = [n.strip() for n in head.split(",") if n.strip()]
    decl = {}
    for st in _split_top(body[m.end():], ";"):
        dm = DECL.match(st.strip())
        if dm:
            for n in _split_top(dm.group(4)):
                decl[n.split("=")[0].strip()] = (dm.group(1), dm.group(3) or "")
    missing = [n for n in names if n not in decl]
    if missing:
        raise FaceLandError(f"{top}: undeclared header ports {missing[:5]}")
    return [(decl[n][0], decl[n][1], n) for n in names]


def width(rng: str) -> int | None:
    if not rng:
        return 1
    m = re.fullmatch(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", rng)
    return abs(int(m.group(1)) - int(m.group(2))) + 1 if m else None


def check_cfg(fl: dict, plist, clock: str, spec_resets=()) -> None:
    names = {p[2]: p for p in plist}
    for r in fl.get("reset_ports", []):
        if r not in names or names[r][0] != "input" or width(names[r][1]) != 1:
            raise FaceLandError(f"face_land: reset port {r!r} is not a 1-bit input of {fl['core']}")
    for p, lat in fl.get("land", {}).items():
        if p not in names or names[p][0] != "input":
            raise FaceLandError(f"face_land: land port {p!r} is not an input of {fl['core']}")
        if p == clock or p in fl.get("reset_ports", []) or p in spec_resets:
            raise FaceLandError(f"face_land: {p!r} is a clock / reset role, not data")
        if not (isinstance(lat, int) and lat >= 1):
            raise FaceLandError(f"face_land: land[{p!r}] must be an integer LAT >= 1")
    if clock not in names:
        raise FaceLandError(f"face_land: clock {clock!r} is not a port of {fl['core']}")
    if not fl.get("reset_ports") and not fl.get("land"):
        raise FaceLandError("face_land: nothing to land")
    rc = fl.get("reset_copies")
    if rc is not None and (not isinstance(rc, dict) or any(r not in fl.get("reset_ports", []) for r in rc)
                           or any(not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 64 for n in rc.values())):
        raise FaceLandError("face_land: reset_copies must map face_land reset_ports to integers 1..64")


def wrapper(fl: dict, plist, clock: str) -> str:
    core = fl["core"]
    rs, land = list(fl.get("reset_ports", [])), dict(fl.get("land", {}))
    L = ["`timescale 1ns/1ps",
         f"// GENERATED by tools/ref_tile/face_land.py from {fl['core_src']} (module {core}) -- do not edit; re-run",
         "// ref_tile.py gen (spec \"face_land\").  Face landing standard (HKV-RSTCAP 2026-10-19):",
         f"//   reset {', '.join(rs) or '-'}: rtl/lib/ot_rst_relay.sv (async assert, release +{RELEASE_EDGES} {clock} edges, zero steady-state cycles)",
         "//   landed buses: " + (", ".join(f"{p} +{n}" for p, n in land.items()) or "-") + " (rtl/lib/ot_pin_land.sv, one capture flop per bit at the face)",
         f"//   reason: {fl.get('reason', '')}",
         "// MUT bit0 = reset relay bypassed, bit1 = landing bypassed (bench mutants only).",
         f"module {core}_fl #(parameter integer MUT=0) ("]
    L.append(",\n".join(f"    {d} wire {r + ' ' if r else ''}{n}" for d, r, n in plist))
    L.append(");")
    conn = {}
    for r in rs:
        L += [f"    wire fl_rst__{r};",
              "    generate if (MUT % 2) begin : g_rbyp_" + r,
              f"        assign fl_rst__{r} = {r};",
              "    end else begin : g_rrel_" + r,
              f"        ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_fl_rst_{r} (.clk({clock}), "
              f".rst_n_in({r}), .rst_n(fl_rst__{r}));",
              "    end endgenerate"]
        nc = int((fl.get("reset_copies") or {}).get(r, 1))
        if nc > 1:
            # KV-RELAYGEN 2026-10-19: N KEPT identical relay copies; the core still takes copy 0 and synthesis
            # (physical/common_flow/ot_rst_copies.tcl, kit "reset_relay_split") spreads its reset loads over all copies
            L[-2:-1] = [f"        wire [{nc - 1}:0] fl_rstc__{r};  // KV-RELAYGEN: {nc} kept relay copies (ot_rst_copies.tcl)",
                        f"        ot_rst_relay #(.REGIONS({nc}), .SYNC_STAGES(2), .TREE_STAGES(1)) u_fl_rst_{r} (.clk({clock}), "
                        f".rst_n_in({r}), .rst_n(fl_rstc__{r}));",
                        f"        assign fl_rst__{r} = fl_rstc__{r}[0];"]
        conn[r] = f"fl_rst__{r}"
    rng = {p[2]: p[1] for p in plist}
    for p, n in land.items():
        w = width(rng[p])
        wexp = str(w) if w is not None else f"$bits({p})"
        L += [f"    wire {rng[p] + ' ' if rng[p] else ''}fl_land__{p};",
              f"    ot_pin_land #(.W({wexp}), .LAT({n}), .MUT((MUT / 2) % 2)) u_fl_land_{p} (.clk({clock}), .d({p}), "
              f".q(fl_land__{p}));"]
        conn[p] = f"fl_land__{p}"
    L.append(f"    {core} u_core (")
    L.append(",\n".join(f"        .{n}({conn.get(n, n)})" for _, _, n in plist))
    L += ["    );", "endmodule", ""]
    return "\n".join(L)


def apply(s: dict, write: bool = True, root: Path = ROOT) -> dict:
    """ref_tile gen hook: complete a spec carrying "face_land" (top, sources) and (re)write its wrapper."""
    fl = s.get("face_land")
    if not fl:
        return s
    for k in ("core", "core_src", "reason"):
        if not fl.get(k):
            raise FaceLandError(f"face_land needs {k!r}")
    plist = ports(root / fl["core_src"], fl["core"])
    check_cfg(fl, plist, s["clock_port"], s.get("reset_ports") or ())
    rel = f"{OUT_DIR}/{fl['core']}_fl.sv"
    text = wrapper(fl, plist, s["clock_port"])
    if write:
        (root / OUT_DIR).mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    elif not (root / rel).exists() or (root / rel).read_text() != text:
        raise FaceLandError(f"{rel} is stale: run ref_tile.py gen")
    s["top"] = fl["core"] + "_fl"
    if fl["core_src"] not in s["sources"]:
        raise FaceLandError(f"face_land: core_src {fl['core_src']} is not in sources")
    for f in (RELAY, LAND, rel):
        if f not in s["sources"]:
            s["sources"].append(f)
    if s.get("reset_ports") is not None:
        missing = [r for r in fl.get("reset_ports", []) if r not in s["reset_ports"]]
        if missing:
            raise FaceLandError(f"face_land: {missing} must also be declared reset_ports")
    return s


# ----------------------------------------------------------------------------------------------------------- bench
def bench_tb(s: dict, cycles: int, mut: int) -> str:
    fl = s["face_land"]
    core = fl["core"]
    plist = ports(ROOT / fl["core_src"], core)
    clocks = {s["clock_port"], *[c for c in s.get("clock_ports", []) if isinstance(c, str)]}
    rs, land = list(fl.get("reset_ports", [])), dict(fl.get("land", {}))
    T = ["`timescale 1ns/1ps", "module tb_face_land;",
         "reg ck = 0; always #0.5 ck = ~ck;",
         "reg rst_n = 0;",
         # independent reset model: async assert, the core leaves reset on the 3rd rising edge after release
         f"reg [{RELEASE_EDGES - 1}:0] ref_rp = 0;",
         f"always @(posedge ck or negedge rst_n) if (!rst_n) ref_rp <= 0; else ref_rp <= {{ref_rp[{RELEASE_EDGES - 2}:0], 1'b1}};",
         f"wire ref_rst = ref_rp[{RELEASE_EDGES - 1}];",
         "integer errors = 0, comparisons = 0, epochs = 0, toggles = 0, first_err = -1, c;",
         "reg [8191:0] rnd;"]
    dcon, rcon, drive, cmp, snap = [], [], [], [], []
    for d, r, n in plist:
        w = width(r)
        decl = f"[{w - 1}:0] " if w and w > 1 else ("" if w == 1 else f"{r} ")
        if n in clocks:
            dn = rn = "ck"
        elif n in rs:
            dn, rn = "rst_n", "ref_rst"
        elif d == "input":
            dn = f"i_{n}"
            T.append(f"reg {decl}{dn} = 0;")
            nw = w or 64
            words = max(1, math.ceil(nw / 32))
            drive.append(f"{dn} = {{{', '.join(['$urandom'] * words)}}};")
            if n in land:
                lat = land[n]
                T.append(f"reg [{(nw * lat) - 1}:0] dl_{n} = 0;")
                if lat == 1:
                    T.append(f"always @(posedge ck) dl_{n} <= {dn};")
                else:
                    T.append(f"always @(posedge ck) dl_{n} <= {{dl_{n}[{nw * (lat - 1) - 1}:0], {dn}}};")
                rn = f"dl_{n}[{nw * lat - 1}-:{nw}]"
            else:
                rn = dn
        else:
            dn, rn = f"d_{n}", f"r_{n}"
            T += [f"wire {decl}{dn}, {rn};", f"reg {decl}p_{n} = 0;"]
            cmp.append(f"if ({dn} !== {rn}) begin errors = errors + 1; if (first_err < 0) begin first_err = c; "
                       f"$display(\"MISMATCH c=%0d port={n}\", c); end end")
            snap.append(f"if ({dn} !== p_{n}) begin toggles = toggles + 1; p_{n} = {dn}; end")
        dcon.append(f".{n}({dn})")
        rcon.append(f".{n}({rn})")
    T.append(f"{core}_fl #(.MUT({mut})) dut ({', '.join(dcon)});")
    T.append(f"{core} ref_core ({', '.join(rcon)});")
    T.append("task compare; begin comparisons = comparisons + 1;")
    T += ["  " + x for x in cmp]
    T.append("end endtask")
    T += ["initial begin",
          "  repeat (4) @(negedge ck);",
          "  rst_n = 1;",
          f"  for (c = 0; c < {cycles}; c = c + 1) begin",
          "    @(negedge ck);",
          "    compare;"] + ["    " + x for x in snap] + [
          # reset epochs: long hold (c%257==0, 1..8 cycles), a sub-cycle pulse between edges (c%389==5), and a pulse
          # landing on each release edge (c%613 == 9..11 relative to an assertion at c%613==7)
          "    if (c % 257 == 0) begin #0.1; rst_n = 0; epochs = epochs + 1; #0.05; compare; end",
          "    if (c % 257 == 1 + (c / 257) % 8) rst_n = 1;",
          "    if (c % 389 == 5) begin #0.1; rst_n = 0; epochs = epochs + 1; #0.05; compare; #0.1; rst_n = 1; end",
          "    if (c % 613 == 7) begin #0.1; rst_n = 0; epochs = epochs + 1; #0.05; compare; end",
          "    if (c % 613 == 8) rst_n = 1;",
          "    if (c % 613 == 9 + (c / 613) % 3) begin #0.1; rst_n = 0; epochs = epochs + 1; #0.05; compare; #0.1; rst_n = 1; end"] + [
          "    " + x for x in drive] + [
          "  end",
          f"  $display(\"FACE_LAND %s top={core}_fl mut={mut} checks=%0d comparisons=%0d epochs=%0d toggles=%0d errors=%0d first_err=%0d\","
          f" (errors == 0 && toggles >= {max(20, cycles // 200)}) ? \"PASS\" : \"FAIL\", comparisons, comparisons, epochs, toggles, errors, first_err);",
          f"  if (errors != 0 || toggles < {max(20, cycles // 200)}) $fatal(1, \"face_land contract mismatch or no output activity\");",
          "  $finish;",
          "end",
          "endmodule", ""]
    return "\n".join(T)


def bench(spec_path: str, out: str, mut: int, cycles: int, threads: int) -> int:
    s = json.loads((ROOT / spec_path).read_text())
    if not s.get("face_land"):
        print("FACE_LAND ERROR spec has no face_land")
        return 2
    apply(s, write=False)
    od = Path(out).resolve()
    od.mkdir(parents=True, exist_ok=True)
    tb = od / "tb_face_land.sv"
    tb.write_text(bench_tb(s, cycles, mut))
    v = str(VERILATOR) if VERILATOR.exists() else "verilator"
    ver = subprocess.run([v, "--version"], capture_output=True, text=True).stdout.strip()
    print(f"FACE_LAND verilator {ver}", flush=True)
    defs = [f"-D{k}" if v is True else f"-D{k}={v}" for k, v in (s.get("defines") or {}).items()]
    cmd = [v, "--binary", "--timing", "-j", str(threads), "--top-module", "tb_face_land", "-Wno-fatal", "-Wno-lint",
           "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--x-assign", "0", "--x-initial", "0",
           "-Mdir", str(od / "obj"), "-o", "tb", *defs, str(tb)] + [str(ROOT / f) for f in s["sources"]]
    with (od / "build.log").open("w") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        print("FACE_LAND BUILD_ERROR\n" + (od / "build.log").read_text()[-3000:])
        return 2
    r = subprocess.run([str(od / "obj/tb")], capture_output=True, text=True)
    print(r.stdout + r.stderr, flush=True)
    return 0 if "FACE_LAND PASS" in r.stdout else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen", help="write the wrapper of a spec (ref_tile.py gen does this too)")
    g.add_argument("spec")
    b = sub.add_parser("bench")
    b.add_argument("--spec", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--mut", type=int, default=0)
    b.add_argument("--cycles", type=int, default=20000)
    b.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)
    if a.cmd == "gen":
        s = json.loads(Path(a.spec).read_text())
        apply(s)
        print(f"{OUT_DIR}/{s['face_land']['core']}_fl.sv")
        return 0
    return bench(a.spec, a.out, a.mut, a.cycles, a.threads)


if __name__ == "__main__":
    sys.exit(main())
