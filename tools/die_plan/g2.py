"""G2 probes (TOPDOWN-PLAN, redefined by COORD 10-23): short read-only OpenROAD GRT diagnostics from die_plan.json.

Abutted partitions leave nothing for a die-level signal route (every lane is inside a partition), so G2 has two parts:

  (a) die probe   -- the die-level nets only: the clock spine (root -> every partition's clock tap) and the reset
                     spine (root -> every reset tap) on the die layers (M8/M9), with the partitions blocking M1..M7
                     (except die.channels), the die PG grid (die.pg.grid) as M8/M9 blockages.  Reports GRT overflow per
                     layer, wirelength, and root -> tap reach (max / p90 Manhattan um).
  (b) partition FT probes -- per partition TYPE among the N worst by G0 (max per-partition cut-segment ratio, then face
                     pin density): the exact outline and pins (the kit io.tcl), a boundary flop per pin bit next to its
                     pin, the ft station flops at their sites (slot regs_um or evenly along the in->out route; data +
                     the epoch bit, i.e. one flop per pin bit), the leaf blockages (contents origin_um/outline_um, layers
                     M1..obs_max, default M5) as obstructions + placement blockages, detailed placement, then GRT on
                     M2..partition_signal_max with the partition's own logic modelled by a layer capacity adjustment.
                     Reports overflow per layer, wirelength and pin access (pin_access warnings).

    python3 tools/die_plan/g2.py die  PLAN.json --out DIR [--run] [--mem 64]
    python3 tools/die_plan/g2.py part PLAN.json --out DIR (--types t1,t2 | --worst 5) [--adjust 0.5] [--run] [--mem 32]
    python3 tools/die_plan/g2.py all  PLAN.json --out DIR [--worst 5] [--run]   -> DIR/g2_report.json
Each probe directory holds probe.v, probe.tcl, run.sh (docker, --memory = --memory-swap = MEM, owner 10-23 rule for
diagnostic probes) and, after --run, grt.log and grt.json.  Runs are diagnostics: they never write into the plan.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import gen_phys  # noqa: E402
import ft_bit_sites  # noqa: E402
import schema as S  # noqa: E402

IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
TECH_LEF = f"{PLAT}/lef/asap7_tech_1x_201209.lef"
SC_LEF = f"{PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef"
FLOP = "DFFHQNx1_ASAP7_75t_R"
TAPBUF = "BUFx24_ASAP7_75t_R"
FLOP_INSET_UM = 1.0
GRT_ROW = re.compile(r"^\s*(M\d+|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)")


def parse_grt(text):
    """last OpenROAD GRT congestion table + wirelength + pin access / error counts."""
    tables, cur = [], None
    for ln in text.splitlines():
        m = GRT_ROW.match(ln)
        if m:
            if cur is None:
                cur = {}
                tables.append(cur)
            cur[m.group(1)] = dict(resource=int(m.group(2)), demand=int(m.group(3)), usage_pct=float(m.group(4)),
                                   overflow=int(m.group(7)))
        elif cur is not None and ln.strip() and not ln.strip().startswith("-"):
            cur = None
    res = dict(layers={}, total_overflow=None, wirelength_um=None)
    if tables:
        t = tables[-1]
        res["total_overflow"] = t.get("Total", {}).get("overflow")
        res["layers"] = {k: v for k, v in t.items() if k != "Total"}
    m = re.findall(r"Total wirelength:\s*([\d.]+)\s*um", text)
    if m:
        res["wirelength_um"] = float(m[-1])
    res["errors"] = sorted(set(re.findall(r"\[ERROR ([A-Z]+-\d+)\]", text)))
    res["pin_access_warnings"] = len(re.findall(r"\[WARNING DRT-0(?:073|068|069|142)\]", text))
    res["pin_access_no_ap"] = {k: int(v) for k, v in re.findall(r"#(\w+)NoAp\s*=\s*(\d+)", text)}
    res["pin_access_done"] = "Complete pin access" in text
    m = re.findall(r"OT_REACH (\S+) max ([\d.]+) p90 ([\d.]+) n (\d+)", text)
    res["reach"] = {k: dict(max_um=float(a), p90_um=float(b), taps=int(n)) for k, a, b, n in m}
    res["done"] = "OT_DONE" in text
    return res


def run_sh(mem, cpus=4, name="g2probe"):
    return f"""#!/bin/bash
# G2 probe: short read-only diagnostic (owner 10-23: docker run with --memory = --memory-swap, not ot-run)
D=$(cd $(dirname $0) && pwd)
docker run --rm --name {name}-$$ --cpus={cpus} --memory={mem}g --memory-swap={mem}g -v $D:/work -w /work {IMAGE} \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/probe.tcl > /work/grt.log 2>&1; echo EXIT \\$? > /work/probe.exit; chmod -R a+rwX /work"
python3 {HERE}/g2.py parse $D/grt.log > $D/grt.json 2>/dev/null || true
cat $D/probe.exit
"""


def grt_tail(signal, adjust):
    adj = "\n".join(f"set_global_routing_layer_adjustment {l} {v:g}" for l, v in adjust)
    return f"""set_routing_layers -signal {signal}
{adj}
set t0 [clock seconds]
global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
"""


def lrange(a, b):
    return [f"M{i}" for i in range(int(a[1:]), int(b[1:]) + 1)]


# --------------------------------------------------------------------------------------------- (a) die probe
def die_probe(P, out, mem=64):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    W, H = P.W, P.H
    die_l = P.layer_budget["die_layers"]
    top_part = P.layer_budget["partition_signal_max"]
    root = P.clock.get("spine", {}).get("root_um") or [W / 2, H / 2]
    taps = {"clk": [], "rst": []}
    declared = []
    for n, p in sorted(P.parts.items()):
        ck, rs = gen_phys.tap_points(P, P.parts[n]["type"])
        taps["clk"].append((n, P.to_die(n, ck)))
        for tnm, tx, ty in gen_phys.clock_pins(P, P.parts[n]["type"])[1:]:     # R4 grid taps beyond tap 0
            taps["clk"].append((f"{n}__{tnm}", P.to_die(n, (tx, ty))))
        taps["rst"].append((n, P.to_die(n, rs)))
        for i, tap in enumerate(P.ptype(n).get("clock", {}).get("taps", [])):
            # xy is already in the type frame (including any core orientation). Apply only the partition transform.
            xy = P.to_die(n, tap["xy"])
            taps["clk"].append((f"{n}__declared_{i}", xy))
            declared.append(dict(tap, partition=n, type=P.parts[n]["type"], xy_die_um=list(xy)))
    tcl = [f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}", "read_verilog /work/probe.v", "link_design die_probe",
           f"initialize_floorplan -die_area {{0 0 {W:g} {H:g}}} -core_area {{0 0 {W:g} {H:g}}} -site asap7sc7p5t"]
    # tracks: die layers real; M1..M7 coarse (fully blocked under the partitions) so GRT gcells stay die-sized
    for n in lrange("M1", "M9"):
        L = P.layers.get(n)
        if n in die_l and L:
            tcl.append(f"make_tracks {n} -x_offset {L['offset_um']:g} -x_pitch {L['pitch_um']:g} "
                       f"-y_offset {L['offset_um']:g} -y_pitch {L['pitch_um']:g}")
        else:
            tcl.append(f"make_tracks {n} -x_offset 0.32 -x_pitch 0.64 -y_offset 0.32 -y_pitch 0.64")
    tcl.append("set block [ord::get_db_block]")
    pin_l = {"clk": die_l[-1], "rst": die_l[0]}
    for net, lst in taps.items():
        tcl.append(f"set n [odb::dbNet_create $block {net}_spine]")
        tcl.append(f"set b [odb::dbBTerm_create $n {net}_root]; $b setIoType INPUT")
        for part, _ in lst:
            tcl.append(f"set b [odb::dbBTerm_create $n {net}_tap_{part}]; $b setIoType OUTPUT")
    for net, lst in taps.items():
        L = pin_l[net]
        sz = "{0.04 0.32}" if P.layers[L]["dir"] == "V" else "{0.32 0.04}"
        rp = {n: (x, y) for n, _, x, y in gen_phys.die_root_pins(P)}["clk" if net == "clk" else "rst_n"]
        tcl.append(f"place_pin -pin_name {net}_root -layer {L} -location {{{rp[0]:.4f} {rp[1]:.4f}}} -pin_size {sz}")
        for part, (x, y) in lst:
            tcl.append(f"place_pin -pin_name {net}_tap_{part} -layer {L} -location {{{x:.3f} {y:.3f}}} -pin_size {sz}")
    # partitions block M1..partition_signal_max (die.channels stay open)
    chans = [c["rect_um"] for c in P.die.get("channels", [])]
    for n in sorted(P.parts):
        x0, y0, x1, y1 = P.rect(n)
        for L in lrange("M1", top_part):
            tcl.append(f"create_obstruction -region {{{x0:g} {y0:g} {x1:g} {y1:g}}} -layer {L}")
    # die PG stripes as M8/M9 obstructions
    nst = 0
    for g in P.die.get("pg", {}).get("grid", []):
        L = P.layers.get(g["layer"])
        if not L:
            continue
        k = max(1, len(g.get("nets", ["VDD", "VSS"])))
        ext = H if L["dir"] == "V" else W
        span = W if L["dir"] == "V" else H
        pos = g["offset_um"]
        while pos < span:
            for j in range(k):
                c = pos + j * g["pitch_um"] / k
                if c + g["width_um"] / 2 > span:
                    continue
                a, b = c - g["width_um"] / 2, c + g["width_um"] / 2
                r = (a, 0, b, ext) if L["dir"] == "V" else (0, a, ext, b)
                tcl.append(f"create_obstruction -region {{{r[0]:.3f} {r[1]:.3f} {r[2]:.3f} {r[3]:.3f}}} -layer {g['layer']}")
                nst += 1
            pos += g["pitch_um"]
    for net, lst in taps.items():
        ds = sorted(abs(x - root[0]) + abs(y - root[1]) for _, (x, y) in lst)
        if ds:
            tcl.append(f'puts "OT_REACH {net} max {ds[-1]:.1f} p90 {ds[int(0.9 * (len(ds) - 1))]:.1f} n {len(ds)}"')
    tcl.append(grt_tail(f"{die_l[0]}-{die_l[-1]}", []))
    tcl.append('puts OT_DONE')
    (out / "probe.v").write_text("module die_probe ();\nendmodule\n")
    (out / "probe.tcl").write_text("\n".join(tcl) + "\n")
    (out / "run.sh").write_text(run_sh(mem, 8, "g2die"))
    os.chmod(out / "run.sh", 0o755)
    meta = dict(kind="g2-die", die=P.name, taps=len(taps["clk"]), pg_stripes=nst, channels=len(chans),
                route_layers=die_l, root_um=root)
    if declared:
        meta.update(partition_root_taps=len(P.parts), grid_taps=sum(len(S.tap_grid(P, p['type'])) for p in P.parts.values()), declared_clock_taps=len(declared), declared_taps=declared,
                    clock_scope="virtual connectivity/PG/reach only; declared insertion budgets are estimates, "
                                "not measured regional clock-tree, STA or insertion qualification")
    (out / "probe.json").write_text(json.dumps(meta, indent=1) + "\n")
    return out


# ---------------------------------------------------------------------------------- (b) partition FT probes
def worst_types(P, summ, n):
    """rank partition TYPES by their worst G0 cut-segment ratio, then their face pin density."""
    score = defaultdict(float)
    for o in ("vertical", "horizontal"):
        for rec in summ.get("cuts", {}).get(o, []):
            if rec.get("worst_part"):
                if rec["worst_part"] not in P.parts:
                    continue
                t = P.parts[rec["worst_part"]]["type"]
                score[t] = max(score[t], rec["worst_part_ratio"])
    dens = defaultdict(float)
    for f in summ.get("worst_faces", []):
        t = P.parts[f["part"]]["type"]
        dens[t] = max(dens[t], f["pins_per_um"])
    cands = [tn for tn, t in P.types.items() if not t.get("hard")]
    cands.sort(key=lambda tn: (score[tn], dens[tn], len(P.types[tn].get("ft_slots", []))), reverse=True)
    return [(tn, score[tn], dens[tn]) for tn in cands[:n]]


def probe_blockages(t):
    """Leaf obstructions of a partition probe.  A content leaf that the plan splits into planned hard cores
    (hard_cores[].inst == leaf inst or '<leaf inst>_*', e.g. an over-cap bankq leaf -> 3 cores) is represented by
    those cores, not by the whole leaf outline: the space between the cores is glue / routing area of the partition.
    Every other content leaf with an outline is blocked as before."""
    cores = [h for h in t.get("hard_cores", []) if "origin_um" in h and "outline_um" in h]
    out, covered = [], set()
    for c in t.get("contents", []):
        if "origin_um" not in c or "outline_um" not in c:
            continue
        sub = [h for h in cores if h["inst"] == c["inst"] or h["inst"].startswith(c["inst"] + "_")]
        if sub:
            covered.update(h["inst"] for h in sub)
            out += [dict(h, obs_max=c.get("obs_max", h.get("obs_max", "M5"))) for h in sub]
        else:
            out.append(c)
    return out


def part_probe(P, tn, out, adjust=0.5, mem=32):
    t = P.types[tn]
    w, h = t["outline_um"]
    inst = next(n for n, p in P.parts.items() if p["type"] == tn)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pins = gen_phys.type_pins(P, tn)
    (out / "io.tcl").write_text(gen_phys.io_tcl(P, tn, pins))
    (out / "make_tracks.tcl").write_text(gen_phys.make_tracks_tcl(P))
    by_bus = defaultdict(list)
    for bus, bit, ln, x, y, f in pins:
        by_bus[bus].append((bit, x, y, f))
    width = {b: max(v[0] for v in lst) + 1 for b, lst in by_bus.items()}
    buses = {b["name"]: b for b in t.get("buses", [])}
    slots = {s["name"]: s for s in t.get("ft_slots", [])}
    ports, cells, nets, place = [], [], [], []

    def inset(x, y, f):
        return {"E": (x - FLOP_INSET_UM, y), "W": (x + FLOP_INSET_UM, y), "N": (x, y - FLOP_INSET_UM),
                "S": (x, y + FLOP_INSET_UM)}[f]
    for bus in sorted(by_bus):
        d = "input" if (bus in buses and buses[bus]["dir"] == "in") or bus.endswith("_i") and bus[:-2] in slots \
            else "output"
        ports.append(f"  {d} [{width[bus] - 1}:0] {bus}")
    tp = gen_phys.tap_pins(P, tn)
    for nm, _, _ in tp:
        ports.append(f"  input {nm}")
    # clock / reset entry: each interior tap pin (die spine drop; R4 tap grid) feeds a pre-placed tap buffer = tree root
    for nm, x, y in tp:
        cells.append(f"  {TAPBUF} tap_{nm} (.A({nm}), .Y(tapq_{nm}));")
        nets.append(f"tapq_{nm}")
        place.append((f"tap_{nm}", x + 1.0, y))
    # Wavefront IO pins are scalar interior pins emitted by io_tcl separately
    # from type_pins. Model the actual generated registered reset tree so the
    # probe contains and drives every rst_o port, including <=405-um relays.
    reset_outs = gen_phys.reset_out_pins(P, tn)
    if reset_outs:
        import reset_tree as RT
        tree = RT.for_type(P, tn)
        for nm, _, _ in reset_outs:
            ports.append(f"  output {nm}")
        prev = "arst_n"
        for j in range(RT.entry_stages(tree)):
            c, q = f"pr_reset_entry_{j}", f"pr_reset_entry_q_{j}"
            cells.append(f"  {FLOP} {c} (.D({prev}), .QN({q}));")
            nets.append(q)
            place.append((c, *tree["root"]))
            prev = q
        rename = {"rst_root_n": prev}
        for rl in tree["relays"]:
            c, q = "pr_reset_" + rl["name"], "pr_reset_" + rl["q"]
            src = rename.get(rl["d"], "pr_reset_" + rl["d"])
            cells.append(f"  {FLOP} {c} (.D({src}), .QN({q}));")
            nets.append(q)
            place.append((c, *rl["xy"]))
        for j, (nm, _, _) in enumerate(reset_outs):
            cells.append(f"  assign {nm} = pr_reset_rst_n_t{tree['n_clock_taps'] + j};")
    # functional buses: one boundary flop per pin bit beside its pin
    for bus, lst in sorted(by_bus.items()):
        if bus in buses:
            for bit, x, y, f in lst:
                c = f"bf_{bus}_{bit}"
                if buses[bus]["dir"] == "in":
                    cells.append(f"  {FLOP} {c} (.D({bus}[{bit}]), .QN(nq_{c}));")
                else:
                    cells.append(f"  {FLOP} {c} (.D(nd_{c}), .QN({bus}[{bit}]));")
                    nets.append(f"nd_{c}")
                nets.append(f"nq_{c}") if buses[bus]["dir"] == "in" else None
                place.append((c, *inset(x, y, f)))
    # ft slots: station chain per bit (data + epoch bit are all pin bits), sites from regs_um or along the route
    for sn, s in sorted(slots.items()):
        ib, ob = by_bus.get(sn + "_i", []), by_bus.get(sn + "_o", [])
        k = int(s.get("stations", 1))
        ft_bit_sites.validate_slot(s)
        pi = {bit: (x, y, f) for bit, x, y, f in ib}
        po = {bit: (x, y, f) for bit, x, y, f in ob}
        for bit in sorted(set(pi) | set(po)):
            # a bit present on one side only (the epoch bit when the other end is die IO) still gets its station
            x, y, f = pi.get(bit) or po[bit]
            xo, yo, fo = po.get(bit) or pi[bit]
            a, b = inset(x, y, f), inset(xo, yo, fo)
            seg = check.zroute(a, b, f, fo)
            L = check.plen(seg)
            prev = f"{sn}_i[{bit}]" if bit in pi else f"nd_st_{sn}_{bit}"
            if bit not in pi:
                nets.append(prev)
            for j in range(k):
                c = f"st_{sn}_{bit}_{j}"
                last = j == k - 1
                q = f"{sn}_o[{bit}]" if (last and bit in po) else f"nq_{c}"
                if q.startswith("nq_"):
                    nets.append(q)
                cells.append(f"  {FLOP} {c} (.D({prev}), .QN({q}));")
                if s.get("bit_sites_um") and j > 0:
                    # Same convention as face_flops.tcl: explicit internal
                    # stages start at1; metadata stores allocation-envelope LL.
                    xy = s["bit_sites_um"][j - 1][bit]
                    cw, ch = s["bit_site_cell_um"]
                    site = (xy[0] + cw / 2, xy[1] + ch / 2)
                elif s.get("bit_sites_um"):
                    site = a  # station0 remains registered beside its input pin
                else:
                    site = tuple(s["regs_um"][j]) if s.get("regs_um") else check.point_at(seg, L * j / k)
                place.append((c, *site))
                prev = q
    v = ["module ftprobe ("] + [",\n".join(ports)] + [");"] + \
        [f"  wire {n};" for n in sorted(set(x for x in nets if x))] + cells + ["endmodule"]
    (out / "probe.v").write_text("\n".join(v) + "\n")
    m = gen_phys.CORE_MARGIN_UM
    top = P.type_top_layer(tn)
    tcl = [f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}", "read_verilog /work/probe.v", "link_design ftprobe",
           f"initialize_floorplan -die_area {{0 0 {w:g} {h:g}}} -core_area {{{m:g} {m:g} {w - m:g} {h - m:g}}} "
           "-site asap7sc7p5t", "source /work/make_tracks.tcl", "source /work/io.tcl"]
    nobs = 0
    for c in probe_blockages(t):
        x0, y0 = c["origin_um"]
        x1, y1 = x0 + c["outline_um"][0], y0 + c["outline_um"][1]
        tcl.append(f"create_blockage -region {{{x0:g} {y0:g} {x1:g} {y1:g}}}")
        for L in lrange("M1", c.get("obs_max", "M5")):
            tcl.append(f"create_obstruction -region {{{x0:g} {y0:g} {x1:g} {y1:g}}} -layer {L}")
        nobs += 1
    for c, x, y in place:
        x = min(max(x, m), w - m - 1.0)
        y = min(max(y, m), h - m - 0.3)
        tcl.append(f"place_inst -name {c} -location {{{x:.3f} {y:.3f}}} -status PLACED")
    tcl += ["detailed_placement -max_displacement {400 400}",
            "check_placement -verbose"]
    tcl.append(grt_tail(f"M2-{top}", [(L, adjust) for L in lrange("M2", top)]))
    tcl += ["if {[catch {pin_access} e]} { puts \"OT_PA_ERROR $e\" }", "puts OT_DONE"]
    (out / "probe.tcl").write_text("\n".join(tcl) + "\n")
    (out / "run.sh").write_text(run_sh(mem, 8, "g2part"))
    os.chmod(out / "run.sh", 0o755)
    meta = dict(kind="g2-partition", die=P.name, type=tn, instance=inst, outline_um=[w, h], pins=len(pins),
                flops=len(place), leaf_blockages=nobs, adjust=adjust, route_layers=f"M2-{top}")
    (out / "probe.json").write_text(json.dumps(meta, indent=1) + "\n")
    return out


def run_probe(d):
    r = subprocess.run(["bash", str(Path(d) / "run.sh")], capture_output=True, text=True)
    res = parse_grt((Path(d) / "grt.log").read_text(errors="replace")) if (Path(d) / "grt.log").exists() else {}
    res["exit"] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "NO_EXIT"
    res.update(json.loads((Path(d) / "probe.json").read_text()))
    (Path(d) / "grt.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("die", "part", "all"):
        s = sub.add_parser(c)
        s.add_argument("plan")
        s.add_argument("--out", required=True)
        s.add_argument("--run", action="store_true")
        s.add_argument("--mem", type=int, default=0)
        if c != "die":
            s.add_argument("--types")
            s.add_argument("--worst", type=int, default=5)
            s.add_argument("--adjust", type=float, default=0.5,
                           help="GRT capacity reduction on M2..M7 for the partition's own logic (default 0.5)")
    s = sub.add_parser("parse")
    s.add_argument("log")
    a = ap.parse_args(argv)
    if a.cmd == "parse":
        print(json.dumps(parse_grt(Path(a.log).read_text(errors="replace")), indent=1))
        return 0
    raw = S.load(a.plan)
    errs = S.validate(raw)
    if errs:
        print("plan invalid (schema):\n  " + "\n  ".join(errs[:20]))
        return 1
    P = S.Plan(raw)
    out = Path(a.out)
    dirs = []
    if a.cmd in ("die", "all"):
        dirs.append(die_probe(P, out / "die", a.mem or 64))
    if a.cmd in ("part", "all"):
        if a.types:
            sel = [(t, None, None) for t in a.types.split(",")]
        else:
            R, summ = check.run(raw, plan_dir=Path(a.plan).resolve().parent)
            sel = worst_types(P, summ, a.worst)
        for tn, sc, dn in sel:
            dirs.append(part_probe(P, tn, out / f"part_{tn}", a.adjust, a.mem or 32))
            print(f"probe type {tn}: G0 segment ratio {sc}, face pins/um {dn}")
    for d in dirs:
        print(d)
    if a.run:
        rep = dict(schema="opentallas.die_plan.g2.v1", plan=str(Path(a.plan).resolve()), probes={})
        for d in dirs:
            r = run_probe(d)
            rep["probes"][d.name] = r
            print(f"{d.name}: {r.get('exit')} overflow {r.get('total_overflow')} wl {r.get('wirelength_um')} "
                  f"reach {r.get('reach')} no-access {r.get('pin_access_no_ap')} errors {r.get('errors')}")
        for d in sorted(out.iterdir()):          # keep earlier probes of this DIR (die / part runs done separately)
            if d.is_dir() and d.name not in rep["probes"] and (d / "grt.json").exists():
                rep["probes"][d.name] = json.loads((d / "grt.json").read_text())
        ok = all(r.get("done") and r.get("total_overflow") == 0 and not any(r.get("pin_access_no_ap", {}).values())
                 for r in rep["probes"].values())
        rep["verdict"] = "PASS" if ok else "FAIL"
        (out / "g2_report.json").write_text(json.dumps(rep, indent=1) + "\n")
        print(f"G2 {rep['verdict']}: {out / 'g2_report.json'}")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
