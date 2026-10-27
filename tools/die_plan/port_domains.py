#!/usr/bin/env python3
"""port_domains: the clock domain of every port bit of a (multi-clock) leaf module, derived from its RTL (TOK-QK/D 10-24).

bind.py binds leaves as black boxes, so it cannot see which clock a leaf port is launched / captured by.  A leaf with ONE
clock pin is unambiguous; a leaf with several (KV kvpc: ck + hck) needs a declaration (asbuilt.port_domains) -- this tool
derives it from the leaf RTL so the declaration is evidence, not a guess.

    port_domains.py yosys   --files FILES.f [--incdirs INCDIRS.f] --top M[,M...] --out DIR [--mem 48]
        Yosys (ORFS image in docker, memory capped; or $OT_BIND_YOSYS): DIR/<M>.json = hierarchy -top M; proc; flatten
        (ASAP7 standard cells and macros stay black boxes).  Then runs `analyse` on each.
    port_domains.py analyse DIR/<M>.json --top M [--out PD.json]
        per port: {"dir", "width", "clocks": {clock pin: bits}, "bits": [per-bit clock pins], "kind", "sync": {...}}.

Analysis (flattened netlist, net = bit):
  * flops: Yosys $dff family ($dff $dffe $adff $adffe $sdff* $aldff* $dffsr*), $dlatch*, $mem_v2 (RD/WR clocks), and
    black boxes whose name looks sequential (ASAP7 DFF* / SDF* / DHL* / DLL* / ICG*: pin CLK, outputs Q / QN / GCLK).
  * a flop's clock net is traced back through combinational cells / buffers / clock gates to a module input port bit:
    that port is the flop's clock pin (a leaf's clock pins = the ports its flops are clocked from).
  * output bit: backward cone through combinational cells to flop outputs -> the set of their clock pins (plus any input
    port reached combinationally = a feed-through).  Input bit: forward cone to flop inputs -> their clock pins; an input
    reaching only asynchronous set/reset pins is a reset; one whose first flop F1 feeds only a second flop F2 on the same
    clock with no logic between is a synchroniser input ("sync2").
A bit with exactly one clock pin is in that pin's domain; the die domain is whatever die clock the binder connects there.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:latest")
YOSYS_IN_IMAGE = "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys"

FF_PORTS = {   # yosys internal flop / latch types: clock pin, data-like inputs, async inputs, outputs
    "$dff": ("CLK", ["D"], [], ["Q"]), "$dffe": ("CLK", ["D", "EN"], [], ["Q"]),
    "$adff": ("CLK", ["D"], ["ARST"], ["Q"]), "$adffe": ("CLK", ["D", "EN"], ["ARST"], ["Q"]),
    "$sdff": ("CLK", ["D", "SRST"], [], ["Q"]), "$sdffe": ("CLK", ["D", "EN", "SRST"], [], ["Q"]),
    "$sdffce": ("CLK", ["D", "EN", "SRST"], [], ["Q"]), "$aldff": ("CLK", ["D"], ["AD", "ALOAD"], ["Q"]),
    "$aldffe": ("CLK", ["D", "EN"], ["AD", "ALOAD"], ["Q"]), "$dffsr": ("CLK", ["D"], ["SET", "CLR"], ["Q"]),
    "$dffsre": ("CLK", ["D", "EN"], ["SET", "CLR"], ["Q"]),
    "$dlatch": ("EN", ["D"], [], ["Q"]), "$adlatch": ("EN", ["D"], ["ARST"], ["Q"]),
    "$dlatchsr": ("EN", ["D"], ["SET", "CLR"], ["Q"]),
}
SEQ_BB = re.compile(r"^(DFF|SDF|DHL|DLL|ICG|ASYNC_DFF)", re.I)
MACRO_BB = re.compile(r"sram|_rom_|^ot_rom|regfile", re.I)       # memory macros: black boxes (their clocked ports)
CLK_PIN = re.compile(r"(^|_)(clk|ck|clock|CLK)[a-zA-Z0-9]*$")


def is_seq_bb(ctype, conns=None):
    n = ctype.lstrip("\\")
    if SEQ_BB.match(n):
        return True
    return bool(MACRO_BB.search(n)) and conns is not None and any(CLK_PIN.search(p) for p in conns)


def bb_clock_pins(c):
    """clock pins of a sequential black box: CLK for a standard cell, every clock-named input of a macro"""
    if "CLK" in c["connections"]:
        return ["CLK"]
    return [p for p in c["connections"] if CLK_PIN.search(p) and c.get("port_directions", {}).get(p, "input") == "input"]


def analyse(js, top):
    m = js["modules"][top]
    ports = m["ports"]
    cells = m["cells"]
    drv = {}                                  # bit -> (cell, port) | ("port", name, i)
    loads = defaultdict(list)                 # bit -> [(cell, port)]
    in_bit = {}
    for pn, p in ports.items():
        for i, b in enumerate(p["bits"]):
            if isinstance(b, int) and p["direction"] == "input":
                drv[b] = ("port", pn, i)
                in_bit[b] = (pn, i)
    for cn, c in cells.items():
        dirs = c.get("port_directions", {})
        for pn, bits in c["connections"].items():
            d = dirs.get(pn, "input")
            for b in bits:
                if not isinstance(b, int):
                    continue
                if d == "output":
                    drv[b] = (cn, pn)
                else:
                    loads[b].append((cn, pn))

    def kind(cn):
        t = cells[cn]["type"]
        if t in FF_PORTS:
            return "ff"
        if t == "$mem_v2" or t == "$mem":
            return "mem"
        if not t.startswith("$") and is_seq_bb(t, cells[cn]["connections"]):
            return "bbseq"
        return "comb"

    def cell_inputs(cn):
        c = cells[cn]
        dirs = c.get("port_directions", {})
        return [b for pn, bits in c["connections"].items() if dirs.get(pn, "input") != "output" for b in bits
                if isinstance(b, int)]

    def cell_outputs(cn):
        c = cells[cn]
        dirs = c.get("port_directions", {})
        return [b for pn, bits in c["connections"].items() if dirs.get(pn) == "output" for b in bits if isinstance(b, int)]

    clk_memo = {}

    def clock_root(b, depth=0):
        """the input port(s) a clock net comes from (through comb / clock gates / buffers)"""
        if b in clk_memo:
            return clk_memo[b]
        clk_memo[b] = frozenset()
        res = set()
        stack, seen = [b], set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            d = drv.get(x)
            if d is None:
                continue
            if d[0] == "port":
                res.add(d[1])
                continue
            cn = d[0]
            k = kind(cn)
            c = cells[cn]
            if k == "bbseq":     # ICG: GCLK from CLK
                for p in bb_clock_pins(c):
                    for x2 in c["connections"].get(p, []):
                        if isinstance(x2, int):
                            stack.append(x2)
                continue
            if k in ("ff", "mem"):
                res.add(f"derived:{cn}")
                continue
            stack.extend(cell_inputs(cn))
        clk_memo[b] = frozenset(res)
        return clk_memo[b]

    def ff_clock(cn, which="CLK"):
        c = cells[cn]
        k = kind(cn)
        if k == "ff":
            pins = [FF_PORTS[c["type"]][0]]
        elif k == "bbseq":
            pins = bb_clock_pins(c)
        else:
            pins = [which]
        bits = [x for p in pins for x in c["connections"].get(p, []) if isinstance(x, int)]
        r = set()
        for x in bits:
            r |= clock_root(x)
        return frozenset(r)

    # flop / mem output bits -> clock set
    q_clock = {}
    for cn, c in cells.items():
        k = kind(cn)
        if k == "ff":
            for x in c["connections"].get("Q", []):
                if isinstance(x, int):
                    q_clock[x] = (ff_clock(cn), cn)
        elif k == "bbseq":
            ck = ff_clock(cn)
            dirs = c.get("port_directions", {})
            for pn, bits in c["connections"].items():
                if dirs.get(pn) != "output":
                    continue
                for x in bits:
                    if isinstance(x, int):
                        q_clock[x] = (ck, cn) if pn != "GCLK" else (frozenset(), cn)
        elif k == "mem":
            p = c["parameters"]
            rdck = c["connections"].get("RD_CLK", [])
            en = str(p.get("RD_CLK_ENABLE", "0"))
            wck = frozenset().union(*[clock_root(x) for x in c["connections"].get("WR_CLK", []) if isinstance(x, int)]) \
                if c["connections"].get("WR_CLK") else frozenset()
            sync = "1" in en
            rck = frozenset().union(*[clock_root(x) for x in rdck if isinstance(x, int)]) if sync else wck
            for x in c["connections"].get("RD_DATA", []):
                if isinstance(x, int):
                    q_clock[x] = (rck, cn)

    def out_cone(b):
        clocks, feed, stack, seen = set(), set(), [b], set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            if x in q_clock:
                clocks |= q_clock[x][0]
                continue
            d = drv.get(x)
            if d is None:
                continue
            if d[0] == "port":
                feed.add(d[1])
                continue
            stack.extend(cell_inputs(d[0]))
        return clocks, feed

    def in_cone(b):
        """clock pins capturing input bit b, whether only async pins see it, and synchroniser shape"""
        clocks, asyn, data, firsts, stack, seen = set(), False, False, [], [b], set()
        clkpin = False
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            for cn, pn in loads.get(x, []):
                k = kind(cn)
                c = cells[cn]
                if k == "ff":
                    ckp, dps, aps, _ = FF_PORTS[c["type"]]
                    if pn == ckp:
                        clkpin = True
                    elif pn in aps:
                        asyn = True
                        clocks |= ff_clock(cn)
                    else:
                        data = True
                        clocks |= ff_clock(cn)
                        firsts.append((cn, pn, x == b))
                elif k == "bbseq":
                    if pn in bb_clock_pins(c):
                        clkpin = True
                    elif pn.upper() in ("RESETN", "SETN", "RN", "SN"):
                        asyn = True
                        clocks |= ff_clock(cn)
                    else:
                        data = True
                        clocks |= ff_clock(cn)
                        firsts.append((cn, pn, x == b))
                elif k == "mem":
                    if pn in ("RD_CLK", "WR_CLK"):
                        clkpin = True
                        continue
                    data = True
                    if pn.startswith("WR_"):
                        clocks |= ff_clock(cn, "WR_CLK")
                    else:
                        clocks |= ff_clock(cn, "RD_CLK") if "1" in str(c["parameters"].get("RD_CLK_ENABLE", "0")) \
                            else frozenset()
                        if "1" not in str(c["parameters"].get("RD_CLK_ENABLE", "0")):
                            stack.extend(x2 for x2 in c["connections"].get("RD_DATA", []) if isinstance(x2, int))
                else:
                    stack.extend(cell_outputs(cn))
        sync = None
        if data and len(firsts) == 1 and firsts[0][2]:
            cn = firsts[0][0]
            qs = [x for x in cells[cn]["connections"].get("Q", cells[cn]["connections"].get("QN", [])) if isinstance(x, int)]
            ld = [l for q in qs for l in loads.get(q, [])]
            if ld and all(kind(c2) in ("ff", "bbseq") and p2 in ("D",) and ff_clock(c2) == ff_clock(cn) for c2, p2 in ld):
                sync = "sync2"
            else:
                sync = "sampled1"
        return clocks, asyn and not data, clkpin and not data and not asyn, sync

    res = {}
    for pn, p in ports.items():
        bits = p["bits"]
        per, ck, kinds, syncs, feeds = [], defaultdict(int), set(), defaultdict(int), set()
        for b in bits:
            if not isinstance(b, int):
                per.append(["const"])
                kinds.add("const")
                continue
            if p["direction"] == "input":
                cl, rst, isclk, sync = in_cone(b)
                if isclk:
                    kinds.add("clock")
                elif rst:
                    kinds.add("reset")
                elif not cl:
                    kinds.add("unloaded")
                else:
                    kinds.add("data")
                if sync:
                    syncs[sync] += 1
            else:
                cl, feed = out_cone(b)
                feeds |= feed
                kinds.add("data" if cl else ("feedthrough" if feed else "const"))
            cl = sorted(cl)
            per.append(cl)
            for x in cl:
                ck[x] += 1
        res[pn] = dict(dir=p["direction"], width=len(bits), clocks=dict(ck), kind=sorted(kinds),
                       mixed=len({tuple(x) for x in per if x and x != ["const"]}) > 1,
                       bits=per if len({tuple(x) for x in per}) > 1 else None,
                       sync=dict(syncs) or None, feedthrough=sorted(feeds) or None)
    clock_pins = sorted({x for r in res.values() for x in r["clocks"] if not x.startswith("derived:")})
    return dict(module=top, clock_pins=clock_pins, ports=res)


def cmd_yosys(a):
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    files = [x.strip() for x in Path(a.files).read_text().split() if x.strip() and not x.startswith("+")]
    ydirs, incs = [], set()
    if a.incdirs:
        toks = Path(a.incdirs).read_text().split()
        for i, t in enumerate(toks):
            if t == "-y" and i + 1 < len(toks):
                ydirs.append(toks[i + 1])
            elif t.startswith("+incdir+"):
                incs.add(t[8:])
    incs |= {str(Path(f).parent) for f in files}
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import bind_elab as E
    lib = [f for f in files if re.search(r"asap7sc7p5t_|/asap7_cells/", f)]
    # module / package index: files.f first (first definition wins, as the Verilator build), then the -y dirs
    idx, pkg = {}, {}
    cand = [f for f in files if f not in lib] + [str(p) for d in ydirs for p in sorted(Path(d).glob("*.*v"))]
    for f in cand:
        try:
            s = E._strip(Path(f).read_text(errors="replace"))
        except OSError:
            continue
        for m in E.MOD_RE.finditer(s):
            idx.setdefault(m.group(1), f)
        for m in re.finditer(r"^\s*package\s+(\w+)", s, re.M):
            pkg.setdefault(m.group(1), f)
    # memory macro models are black boxes too (a 1024x256 behavioural array would flatten into 262k flops)
    lib += sorted({f for f in cand if MACRO_BB.search(Path(f).stem) and f not in lib})
    libmods = set()
    for f in lib:
        libmods |= {m.group(1) for m in E.MOD_RE.finditer(E._strip(Path(f).read_text(errors="replace")))}
    tops = a.top.split(",")
    need, todo, seen = [], list(tops), set()
    while todo:
        n = todo.pop()
        if n in seen or n in libmods:
            continue
        seen.add(n)
        f = idx.get(n)
        if f is None:
            continue
        if f not in need:
            need.append(f)
            for m in E.MOD_RE.finditer(E._strip(Path(f).read_text(errors="replace"))):
                todo += sorted(E.instantiated(E.module_body(f, m.group(1)), idx))
    pk = []
    for f in list(need):
        for nm in re.findall(r"\b(\w+)::", E._strip(Path(f).read_text(errors="replace"))):
            if nm in pkg and pkg[nm] not in pk:
                pk.append(pkg[nm])
    iflags = " ".join(f"-I{d}" for d in sorted(incs))
    stub = E.lib_stubs(lib, out / "lib_stubs.v") if lib else None    # UDP cell models: interface only (black boxes)
    lines = [f"read_verilog -sv -lib -overwrite {stub}"] if stub else []
    # Yosys reads `import pkg::*;` only at file scope: copies with in-module imports hoisted in front of the module
    fixd = out / "src_fix"
    srcs = []
    for f in pk + [x for x in need if x not in pk]:
        s = Path(f).read_text(errors="replace")
        imps = re.findall(r"^[ \t]*import\s+\w+::\*\s*;[ \t]*$", s, re.M)
        fatal = re.search(r"\$(fatal|error)\b", s)
        if (imps and f not in pk) or fatal:
            # analysis copy only: elaboration-time checks ($fatal / $error in generate / always) become $display
            fixd.mkdir(exist_ok=True)
            body = re.sub(r"^[ \t]*import\s+\w+::\*\s*;[ \t]*$", "", s, flags=re.M) if f not in pk else s
            body = re.sub(r"\$(fatal|error)\s*\(\s*\d+\s*,", "$display(", body)
            body = re.sub(r"\$(fatal|error)\b", "$display", body)
            imps = imps if f not in pk else []
            g = fixd / (re.sub(r"[^\w.]", "_", str(Path(f).parent.name)) + "__" + Path(f).name)
            g.write_text("".join(sorted({x.strip() + "\n" for x in imps})) + body)
            f = str(g)
        srcs.append(f)
    lines += [f"read_verilog -sv -overwrite {iflags} {f}" for f in srcs]
    lines.append("design -save srcs")
    for t in tops:
        cp = " ".join(f"-chparam {k} {v}" for x in (a.chparam or []) if x.startswith(t + ":")
                      for k, v in (kv.split("=", 1) for kv in x.split(":", 1)[1].split(",")))
        lines += ["design -load srcs", f"hierarchy -top {t} {cp}".rstrip(), "proc", "setattr -mod -unset keep_hierarchy *", "flatten", "opt_clean -purge",
                  f"write_json {out}/{t}.json"]
    sc = out / "pd.ys"
    sc.write_text("\n".join(lines) + "\n")
    exe = os.environ.get("OT_BIND_YOSYS")
    if exe:
        cmd = [exe, "-q", "-l", str(out / "pd.log"), "-s", str(sc)]
    else:
        mounts = sorted({str(Path(x).resolve()) for x in [out] + [Path(f).parent for f in files] + ydirs})
        top_m = []
        for m in mounts:
            if not any(m.startswith(t + "/") for t in mounts if t != m):
                top_m += ["-v", f"{m}:{m}"]
        cmd = ["docker", "run", "--rm", f"--memory={a.mem}g", f"--memory-swap={a.mem}g", "-u", f"{os.getuid()}:{os.getgid()}"] \
            + top_m + ["-w", str(out), IMAGE, YOSYS_IN_IMAGE, "-q", "-l", str(out / "pd.log"), "-s", str(sc)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write((r.stderr or "")[-3000:])
        tail = (out / "pd.log").read_text()[-3000:] if (out / "pd.log").exists() else ""
        sys.stderr.write(tail)
        return 2
    allr = {}
    for t in tops:
        js = json.loads((out / f"{t}.json").read_text())
        allr[t] = analyse(js, t)
        (out / f"{t}.json").unlink() if a.drop_json else None
    (out / "port_domains.json").write_text(json.dumps(allr, indent=1, sort_keys=True) + "\n")
    for t in tops:
        summary(allr[t])
    print(f"port_domains -> {out}/port_domains.json")
    return 0


def summary(r):
    print(f"== {r['module']}: clock pins {r['clock_pins']}")
    for pn, p in sorted(r["ports"].items()):
        tag = "MIXED " if p["mixed"] else ""
        print(f"  {p['dir']:6} {pn:32} w{p['width']:<5} {tag}{p['kind']} clocks {p['clocks']}"
              + (f" sync {p['sync']}" if p["sync"] else "") + (f" feed {p['feedthrough']}" if p["feedthrough"] else ""))


def cmd_analyse(a):
    r = analyse(json.loads(Path(a.json).read_text()), a.top)
    summary(r)
    if a.out:
        Path(a.out).write_text(json.dumps({a.top: r}, indent=1, sort_keys=True) + "\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    y = sp.add_parser("yosys")
    y.add_argument("--files", required=True)
    y.add_argument("--incdirs")
    y.add_argument("--top", required=True)
    y.add_argument("--out", required=True)
    y.add_argument("--mem", type=int, default=48)
    y.add_argument("--drop-json", action="store_true")
    y.add_argument("--chparam", action="append", help="M:K=V[,K=V...] instance parameters of top M (repeatable)")
    y.set_defaults(fn=cmd_yosys)
    n = sp.add_parser("analyse")
    n.add_argument("json")
    n.add_argument("--top", required=True)
    n.add_argument("--out")
    n.set_defaults(fn=cmd_analyse)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
