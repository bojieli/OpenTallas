#!/usr/bin/env python3
"""Feedthrough GRT probe harness (FT-TOOL, FT-PLAN owner 10-23): block-level and die-level read-only probes.

  abstract-probe  SPEC.json --lef MASTER.lef --out DIR [--layers M8-M9] [--run] [--mem 16]
      The ft traffic of one ftspec over the block's EXPORTED ABSTRACT: a DEF with die = block outline, the block
      macro FIXED at the origin (its OBS is what the die sees), every ft bit as an IO pin pair (in face -> out face, on
      the spec layer and offsets) joined by a 2-pin net; GRT on the ft layers only.  Overflow > 0 = the abstract's
      M8/M9 OBS or the face width cannot carry the ft bits (wrong layer contract / blanket OBS / too narrow a face).
  block-probe     SPEC.json --odb BLOCK_PLACED.odb --out DIR [--signal M2-M9] [--ft-only-layers M8-M9] [--run]
      The block's own placed ODB plus the ft pins and ft nets (pin to pin; the registers come from the real
      hardening): GRT with the block's signal layers, reported per layer (does the block still route with the ft
      traffic on top?).
  die-probe       --odb DIE.odb --out DIR [--plan PLAN.json --drop-pushed] [--eco ECO.tcl] [--signal M2-M9]
                  [--adjust 'M2-M3 0.5,M4-M5 0.3,M6-M9 0.2'] [--run] [--mem 128]
      Read-only die GRT.  --drop-pushed deletes the channel relays of every lane the plan pushes into blocks (an
      UPPER BOUND on the channel relief: the pushed lanes' die wires vanish into the blocks); --eco sources the
      die-side ECO from pushdown.py instead (exact, once the new abstracts exist).
  extract-lef     --odb DIE.odb --masters M1,M2 --out DIR [--run]
      Writes the LEF of the die-case library holding each master (odb.write_lef on that dbLib) -> DIR/<lib>.lef, the
      --lef input of abstract-probe when the block abstract only exists inside a die ODB.
  parse           GRT.log  -> JSON {layers: {M2: {resource, demand, usage_pct, overflow_h, overflow_v, overflow}},
                              total_overflow, wirelength_um}
Every probe writes DIR/run.sh (docker openroad/orfs:asap7lock, --memory = --memory-swap = --mem GB) and DIR/probe.tcl;
--run executes it and writes DIR/grt.json.  Probes are short diagnostics (owner 10-23: plain docker run with the
memory on the host; keep >= 64 GB physical headroom).
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
TECH_LEF = f"{PLAT}/lef/asap7_tech_1x_201209.lef"
SC_LEF = f"{PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef"
IMAGE = "openroad/orfs:asap7lock"
DBU = 1000
# ASAP7 routing layers (pitch um, direction) for DEF TRACKS
LAYERS = [("M1", 0.036, "V"), ("M2", 0.036, "H"), ("M3", 0.036, "V"), ("M4", 0.048, "H"), ("M5", 0.048, "V"),
          ("M6", 0.064, "H"), ("M7", 0.064, "V"), ("M8", 0.08, "H"), ("M9", 0.08, "V")]
PITCH = {n: p for n, p, _ in LAYERS}
GRT_ROW = re.compile(r"^\s*(M\d+|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)")


def parse_grt(text):
    """OpenROAD GRT congestion table (the LAST one in the log = final) -> dict."""
    tables = []
    cur = None
    for ln in text.splitlines():
        m = GRT_ROW.match(ln)
        if m:
            if cur is None:
                cur = {}
                tables.append(cur)
            cur[m.group(1)] = dict(resource=int(m.group(2)), demand=int(m.group(3)), usage_pct=float(m.group(4)),
                                   overflow_h=int(m.group(5)), overflow_v=int(m.group(6)),
                                   overflow=int(m.group(7)))
        elif cur is not None and ln.strip() and not ln.strip().startswith("-"):
            cur = None
    res = dict(layers={}, total_overflow=None, wirelength_um=None, tables=len(tables))
    if tables:
        t = tables[-1]
        res["total_overflow"] = t.get("Total", {}).get("overflow")
        res["layers"] = {k: v for k, v in t.items() if k != "Total"}
    m = re.findall(r"Total wirelength:\s*([\d.]+)\s*um", text)
    if m:
        res["wirelength_um"] = float(m[-1])
    return res


def bit_offsets(lo, hi, bits, pitch):
    """bits pin centres spread over [lo, hi] on the layer track grid (multiples of pitch), deterministic."""
    if bits <= 0:
        return []
    first = round(lo / pitch + 0.5) * pitch
    span = max(0.0, hi - lo - pitch)
    step = max(pitch, math.floor((span / max(1, bits - 1)) / pitch + 1e-9) * pitch) if bits > 1 else pitch
    return [round(first + k * step, 4) for k in range(bits)]


def pin_rect(face, off, W, H, layer, depth=0.4):
    w = PITCH.get(layer, 0.08) / 2
    if face == "W":
        return (0.0, off - w / 2, depth, off + w / 2)
    if face == "E":
        return (W - depth, off - w / 2, W, off + w / 2)
    if face == "S":
        return (off - w / 2, 0.0, off + w / 2, depth)
    return (off - w / 2, H - depth, off + w / 2, H)


def ft_pins(spec):
    """-> [(net, in_pin, out_pin, in_rect(layer, x0,y0,x1,y1), out_rect)] for every ft bit (master frame)."""
    W, H = spec["outline"]
    ports = {p["name"]: p for p in spec["ports"]}
    out = []
    for q in spec["paths"]:
        pi, po = ports[q["in"]], ports[q["out"]]
        oi = bit_offsets(pi["lo"], pi["hi"], q["bits"], PITCH.get(pi["layer"], 0.08))
        oo = bit_offsets(po["lo"], po["hi"], q["bits"], PITCH.get(po["layer"], 0.08))
        for k in range(q["bits"]):
            out.append((f"ftn{q['path']}_{k}", f"{q['in']}[{k}]", f"{q['out']}[{k}]",
                        (pi["layer"],) + pin_rect(pi["face"], oi[k], W, H, pi["layer"]),
                        (po["layer"],) + pin_rect(po["face"], oo[k], W, H, po["layer"])))
    return out


def d(v):
    return int(round(v * DBU))


def dedupe_pins(pins):
    """drop ft bits whose in or out pin lands on a track already taken on that face (overlapping port bands in the
    spec = plan track overflow); -> (kept, dropped count)."""
    used = set()
    kept = []
    for p in pins:
        ka = (p[3][0], round(p[3][1], 3), round(p[3][2], 3))
        kb = (p[4][0], round(p[4][1], 3), round(p[4][2], 3))
        if ka in used or kb in used:
            continue
        used.update((ka, kb))
        kept.append(p)
    return kept, len(pins) - len(kept)


def abstract_def(spec, macro_name=None):
    W, H = spec["outline"]
    pins, _ = dedupe_pins(ft_pins(spec))
    lines = ["VERSION 5.8 ;", "DIVIDERCHAR \"/\" ;", "BUSBITCHARS \"[]\" ;", "DESIGN ftprobe ;",
             f"UNITS DISTANCE MICRONS {DBU} ;", f"DIEAREA ( 0 0 ) ( {d(W)} {d(H)} ) ;"]
    # one placement row: GRT sizes its gcells from the row height (15 x 0.27 um); without rows it OOMs
    lines.append("ROW ROW_0 asap7sc7p5t 0 0 N DO 1 BY 1 STEP 54 0 ;")
    for n, p, dr in LAYERS:
        # GRT wants both track directions on every layer (preferred one first)
        ty = f"TRACKS Y {d(p)} DO {int(H / p)} STEP {d(p)} LAYER {n} ;"
        tx = f"TRACKS X {d(p)} DO {int(W / p)} STEP {d(p)} LAYER {n} ;"
        lines += [ty, tx] if dr == "H" else [tx, ty]
    lines += ["COMPONENTS 1 ;", f"- u_blk {macro_name or spec['master']} + FIXED ( 0 0 ) N ;", "END COMPONENTS"]
    lines.append(f"PINS {2 * len(pins)} ;")
    for net, a, b, ra, rb in pins:
        for nm, r, io in ((a, ra, "INPUT"), (b, rb, "OUTPUT")):
            L, x0, y0, x1, y1 = r
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            lines.append(f"- {nm} + NET {net} + DIRECTION {io} + USE SIGNAL + LAYER {L} ( {d(x0 - cx)} {d(y0 - cy)} ) "
                         f"( {d(x1 - cx)} {d(y1 - cy)} ) + FIXED ( {d(cx)} {d(cy)} ) N ;")
    lines += ["END PINS", f"NETS {len(pins)} ;"]
    for net, a, b, ra, rb in pins:
        lines.append(f"- {net} ( PIN {a} ) ( PIN {b} ) + USE SIGNAL ;")
    lines += ["END NETS", "END DESIGN", ""]
    return "\n".join(lines)


def run_sh(out, mem, cpus=4):
    return f"""#!/bin/bash
# FT probe: short read-only diagnostic (owner 10-23), docker --memory = --memory-swap
D=$(cd $(dirname $0) && pwd)
docker run --rm --name ftprobe-$$ --cpus={cpus} --memory={mem}g --memory-swap={mem}g -v $D:/work -w /work {IMAGE} \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/probe.tcl > /work/grt.log 2>&1; echo EXIT \\$? > /work/probe.exit; chmod -R a+rwX /work"
python3 $D/checks.py parse $D/grt.log > $D/grt.json 2>/dev/null || true
cat $D/probe.exit
"""


def grt_tail(signal, adjust, iters=30, extra=""):
    adj = "\n".join(f"set_global_routing_layer_adjustment {a.split()[0]} {a.split()[1]}"
                    for a in filter(None, (x.strip() for x in adjust.split(","))))
    return f"""set_routing_layers -signal {signal}
{adj}
{extra}
set t0 [clock seconds]
global_route -congestion_iterations {iters} -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
puts OT_DONE
"""


def cmd_abstract(a):
    spec = json.load(open(a.spec))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lef = Path(a.lef).resolve()
    (out / "block.lef").write_text(lef.read_text())
    (out / "ftprobe.def").write_text(abstract_def(spec, a.macro))
    (out / "probe.tcl").write_text(f"""read_lef {TECH_LEF}
read_lef {SC_LEF}
read_lef /work/block.lef
read_def /work/ftprobe.def
""" + grt_tail(a.layers, a.adjust, a.iters))
    (out / "run.sh").write_text(run_sh(out, a.mem))
    os.chmod(out / "run.sh", 0o755)
    _, dropped = dedupe_pins(ft_pins(spec))
    meta = dict(kind="abstract-probe", spec=str(a.spec), lef=str(lef), ft_bits=sum(q["bits"] for q in spec["paths"]),
                layers=a.layers, overlapping_bits_dropped=dropped)
    if dropped:
        print(f"WARNING {dropped} ft bits overlap another port band on the same face (plan track overflow); dropped")
    (out / "probe.json").write_text(json.dumps(meta, indent=1))
    return finish(a, out)


def block_tcl(spec, odb, signal, adjust, iters, ft_only_layers=None):
    pins = ft_pins(spec)
    tcl = [f"read_db {odb}", "set blk [ord::get_db_block]", "set tech [ord::get_db_tech]",
           "proc ftpin {net nm io L x0 y0 x1 y1} {",
           "  global blk tech",
           "  set bt [odb::dbBTerm_create $net $nm]; $bt setIoType $io; $bt setSigType SIGNAL",
           "  set bp [odb::dbBPin_create $bt]; $bp setPlacementStatus FIRM",
           "  odb::dbBox_create $bp [$tech findLayer $L] [ord::microns_to_dbu $x0] [ord::microns_to_dbu $y0] "
           "[ord::microns_to_dbu $x1] [ord::microns_to_dbu $y1]",
           "}"]
    # pins are in the master frame; the block ODB's die is the master outline at its own origin
    tcl.append("set die [$blk getDieArea]; set ox [expr {[$die xMin]/double([$tech getDbUnitsPerMicron])}]; "
               "set oy [expr {[$die yMin]/double([$tech getDbUnitsPerMicron])}]")
    for net, a_, b_, ra, rb in pins:
        tcl.append(f"set n [odb::dbNet_create $blk {net}]; $n setSigType SIGNAL")
        for nm, r, io in ((a_, ra, "INPUT"), (b_, rb, "OUTPUT")):
            L, x0, y0, x1, y1 = r
            tcl.append(f"ftpin $n {{{nm}}} {io} {L} [expr {{$ox+{x0}}}] [expr {{$oy+{y0}}}] "
                       f"[expr {{$ox+{x1}}}] [expr {{$oy+{y1}}}]")
    extra = ""
    if ft_only_layers:
        extra = f"# ft nets only are meant to use {ft_only_layers}; GRT has no per-net layer range in this flow, the " \
                f"probe reports per-layer usage so the ft share of {ft_only_layers} is visible"
    return "\n".join(tcl) + "\n" + grt_tail(signal, adjust, iters, extra)


def cmd_block(a):
    spec = json.load(open(a.spec))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    odb = Path(a.odb).resolve()
    tcl = block_tcl(spec, "/in/block.odb", a.signal, a.adjust, a.iters, a.ft_only_layers)
    (out / "probe.tcl").write_text(tcl)
    sh = run_sh(out, a.mem).replace("-v $D:/work", f"-v $D:/work -v {odb}:/in/block.odb:ro")
    (out / "run.sh").write_text(sh)
    os.chmod(out / "run.sh", 0o755)
    (out / "probe.json").write_text(json.dumps(dict(kind="block-probe", spec=str(a.spec), odb=str(odb),
                                                    ft_bits=sum(q["bits"] for q in spec["paths"])), indent=1))
    return finish(a, out)


def pushed_relays(plan):
    """relay instances of every lane the plan routes through at least one block (not keep_channel)."""
    rel = set()
    for l in plan["lanes"]:
        if not l.get("keep_channel") and l.get("segments"):
            rel.update(l.get("relays") or [])
    return sorted(rel)


def cmd_die(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    odb = Path(a.odb).resolve()
    pre = ["read_db /in/die.odb", "set blk [ord::get_db_block]"]
    meta = dict(kind="die-probe", odb=str(odb), signal=a.signal, adjust=a.adjust)
    if a.plan and a.drop_pushed:
        import gzip
        p = Path(a.plan)
        plan = json.load(gzip.open(p, "rt") if p.suffix == ".gz" else open(p))
        rel = pushed_relays(plan)
        (out / "drop_relays.txt").write_text("\n".join(rel) + "\n")
        pre += ["set nd 0; set nb 0",
                "# the repeater (buffer) trees on a dropped relay's DATA nets go with it (reset / clock trees are shared: kept)",
                "proc ft_buf_tree {net} {",
                "  set out {}; set todo [list $net]; set seen [dict create]",
                "  while {[llength $todo]} {",
                "    set n [lindex $todo end]; set todo [lrange $todo 0 end-1]",
                "    if {$n eq \"NULL\" || [dict exists $seen [$n getName]]} continue",
                "    dict set seen [$n getName] 1",
                "    foreach it [$n getITerms] {",
                "      set i [$it getInst]; set m [[$i getMaster] getName]",
                "      if {![regexp {^(BUF|INV|HB\\d|CKBUF|CKINV)} $m]} continue",
                "      if {[lsearch -exact $out $i] >= 0} continue",
                "      lappend out $i",
                "      foreach o [$i getITerms] { if {[[$o getMTerm] getSigType] ni {POWER GROUND}} { lappend todo [$o getNet] } }",
                "    }",
                "  }",
                "  return $out",
                "}",
                "foreach nm [split [string trim [read [open /work/drop_relays.txt]]] \"\\n\"] {",
                "  set i [$blk findInst $nm]; if {$i eq \"NULL\"} continue",
                "  set bufs {}",
                "  foreach it [$i getITerms] { if {![regexp {^(i|o|a|b|y|d|q[0-9]*)(\\[|$)} [[$it getMTerm] getName]]} continue; set n [$it getNet]; if {$n ne \"NULL\" && [$n getSigType] eq \"SIGNAL\"} { set bufs [concat $bufs [ft_buf_tree $n]] } }",
                "  odb::dbInst_destroy $i; incr nd",
                "  foreach b [lsort -unique $bufs] { if {![catch {odb::dbInst_destroy $b}]} { incr nb } }",
                "}",
                "puts \"OT_DROPPED_RELAYS $nd OT_DROPPED_BUFFERS $nb\""]
        meta.update(drop_pushed=True, dropped=len(rel), plan=str(p),
                    note="upper bound: the pushed lanes' die wiring is removed (absorbed by the hosting blocks)")
    if a.eco:
        (out / "eco.tcl").write_text(Path(a.eco).read_text())
        pre.append("source /work/eco.tcl")
        meta["eco"] = str(a.eco)
    (out / "probe.tcl").write_text("\n".join(pre) + "\n" + grt_tail(a.signal, a.adjust, a.iters))
    sh = run_sh(out, a.mem, a.cpus).replace("-v $D:/work", f"-v $D:/work -v {odb}:/in/die.odb:ro")
    (out / "run.sh").write_text(sh)
    os.chmod(out / "run.sh", 0o755)
    (out / "probe.json").write_text(json.dumps(meta, indent=1))
    return finish(a, out)


XL_PY = """import odb, os
db = odb.dbDatabase.create(); odb.read_db(db, "/in/die.odb")
want = os.environ["FT_MASTERS"].split(",")
for lib in db.getLibs():
    hits = [m for m in want if lib.findMaster(m)]
    if hits:
        p = "/work/%s.lef" % lib.getName()
        odb.write_lef(lib, p); print("LIB", lib.getName(), hits, p)
"""


def cmd_extract(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    odb = Path(a.odb).resolve()
    (out / "xl.py").write_text(XL_PY)
    (out / "run.sh").write_text(f"""#!/bin/bash
D=$(cd $(dirname $0) && pwd)
docker run --rm --name ftxl-$$ --cpus=2 --memory={a.mem}g --memory-swap={a.mem}g -e FT_MASTERS={a.masters} \\
  -v $D:/work -v {odb}:/in/die.odb:ro -w /work {IMAGE} \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/xl.py > /work/xl.log 2>&1; chmod -R a+rwX /work"
grep ^LIB $D/xl.log
""")
    os.chmod(out / "run.sh", 0o755)
    if a.run:
        subprocess.run(["bash", str(out / "run.sh")], check=False)
    else:
        print(f"prepared {out}/run.sh")
    return 0


def finish(a, out):
    import shutil
    shutil.copy(Path(__file__).resolve(), out / "checks.py")
    if getattr(a, "run", False):
        subprocess.run(["bash", str(out / "run.sh")], check=False)
        log = out / "grt.log"
        if log.exists():
            res = parse_grt(log.read_text(errors="replace"))
            (out / "grt.json").write_text(json.dumps(res, indent=1))
            print(json.dumps(dict(total_overflow=res["total_overflow"], wirelength_um=res["wirelength_um"])))
    else:
        print(f"prepared {out}/run.sh")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("abstract-probe")
    s.add_argument("spec")
    s.add_argument("--lef", required=True)
    s.add_argument("--macro", help="LEF MACRO name if it differs from spec master")
    s.add_argument("--out", required=True)
    s.add_argument("--layers", default="M8-M9")
    s.add_argument("--adjust", default="")
    s.add_argument("--iters", type=int, default=30)
    s.add_argument("--mem", type=int, default=48)
    s.add_argument("--run", action="store_true")
    s = sub.add_parser("block-probe")
    s.add_argument("spec")
    s.add_argument("--odb", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--signal", default="M2-M9")
    s.add_argument("--ft-only-layers", default="M8-M9")
    s.add_argument("--adjust", default="M2-M3 0.5,M4-M5 0.3,M6-M7 0.2")
    s.add_argument("--iters", type=int, default=30)
    s.add_argument("--mem", type=int, default=48)
    s.add_argument("--run", action="store_true")
    s = sub.add_parser("die-probe")
    s.add_argument("--odb", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--plan")
    s.add_argument("--drop-pushed", action="store_true")
    s.add_argument("--eco")
    s.add_argument("--signal", default="M2-M9")
    s.add_argument("--adjust", default="M2-M3 0.5,M4-M5 0.3,M6-M9 0.2")
    s.add_argument("--iters", type=int, default=30)
    s.add_argument("--mem", type=int, default=128)
    s.add_argument("--cpus", type=int, default=8)
    s.add_argument("--run", action="store_true")
    s = sub.add_parser("extract-lef")
    s.add_argument("--odb", required=True)
    s.add_argument("--masters", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--mem", type=int, default=40)
    s.add_argument("--run", action="store_true")
    s = sub.add_parser("parse")
    s.add_argument("log")
    a = ap.parse_args(argv)
    if a.cmd == "abstract-probe":
        return cmd_abstract(a)
    if a.cmd == "block-probe":
        return cmd_block(a)
    if a.cmd == "die-probe":
        return cmd_die(a)
    if a.cmd == "extract-lef":
        return cmd_extract(a)
    print(json.dumps(parse_grt(Path(a.log).read_text(errors="replace")), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
