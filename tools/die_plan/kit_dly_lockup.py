#!/usr/bin/env python3
"""kit_dly_lockup.py -- FABLE-FIX-KV-PV XTAP-C 11-20: lockup form for generated zero-logic delay lines (kit RTL post-pass, opt-in).

Why (measured, kv3_pv_v8 v8b post-CTS FF hold, 52,111 ends): 159,831 flops of the type sit in ot_dp_dly / ot_dp_dly_keep pad
delay lines (142,464 zero-logic stage -> stage transfers).  47,549 hold ends cross a kit clock tap: 37.6k inside one delay
instance, 4.3k tail copy -> hard-core pin (worst -135.1), 1.0k trunk -> tail copy.  A tap crossing loses the tap window
(74.9 ps in the kit, 163 ps measured regular spread on the die tree) with no CRPR, so real wire on the hop cannot cover it
and hold buffers on 50k ends do not close (repair_timing: no iteration in 4 h on a 539k-cell kit).

Form (0 cycles, existing cells only: ot_dp_dly, ot_dp_dly_keep, ot_dp_lk):
  1. SPLIT   a selected delay instance with D > SEG becomes ceil(D / SEG) chained instances <name>_sg<j> of the same module
             (stage counts differ by at most 1, sum = D).  A segment is the tap group and the placement station
             (clock_taps tap_chain_affinity joins the stages of one instance; dly_spread OT_DLY_SPREAD_SEG=1 puts the
             stages of one segment on one station).
  2. LATCH   one transparent-low ot_dp_lk u_fl_* (TYPE-SAFE-1 hop lockup: clock_taps.tcl hangs it on the tap of the flop
             that drives its D, LEC latch_to_wire) on
               - every segment boundary                                   u_fl_<base>_sg<j>
               - the d input of a selected instance fed by another one    u_fl_<base>_i
               - the q output of a selected instance read by a hard core  u_fl_<base>_o   (its other readers see the
                 latched net and get no input latch of their own)
             launch -> latch stays inside one tap; latch -> capture gains T/2 of hold.
  3. TAIL    a landing-pad tail copy (`// landing pad tail copy for core <tag>` statement of the bind) is split into TAIL_GROUPS
             groups whatever SEG says; default 0 = one group per stage, because the bind sizes K from the trunk end -> pin route,
             so every stage hop of the farthest copy is a real transport hop (D25e form: 8 cores on one trunk end, hops to 412 um).
             G > 0 = G groups (fewer latches; only where every copy route fits G hops).  tail_copy_anchor.tcl sites group g at
             (g+1)/G of the route, the last group at the pin.  The bound statement stays as a comment line, so gen_phys lists the copy under its bound name
             and K (tail_copies.tsv); tail_copy_anchor.tcl maps <copy>_sg<j> back to it.
  4. UNCHAIN a pad trunk piece fed by another pad trunk's end (bind TRUNK-CHAIN form: `// landing pad trunk` statements, one chain per
             bit, the deeper pad's piece = pad difference, often 1 stage) becomes an independent trunk of the full depth from the
             chain's source.  The chained piece has to cross from one pad's trunk end to the other's in D stages: kv3_pv_v8
             D25e form, 32 ctl_cmd pieces of 1-2 stages between trunk ends about 1 mm apart.  Same depth, +229 flops there;
             the copies are kept cells (ot_dp_dly_keep), so Yosys cannot fold them back.  --no-unchain keeps the chain.
  5. PAD STATIONS (pad_min_stations N > 0, FABLE-FIX-KV-PV-R2 11-20): a pad line that is not a tail copy (u_pd<N>_* trunk or
             single-reader pad) is cut so that it has at least min(D, N) segments: segment size min(SEG, max(1, D // N)).  A segment
             is ONE placement station, so a sparse transport line needs a boundary per transport hop: kv3_pv_v8 astk owner
             response, D 7..11 over 3.1 to 3.6 mm, SEG 8 gave 2 stations and a 1,404-um hop (v8j / v8m / v8c dly_spread max_hop,
             TT setup -8,203 with the wrong-side inverter, about -1,000 without).  Dense lines (D >= SEG x N) are unchanged.
  Never latched: an input fed by a port, by logic or by a hard core (a launch-clock latch on a core tap is not a lockup:
  v8b dry ECO, 613 pair ts -> join ends at -946 ps), and an output read only by logic.

Plan key: budgets.r_dly_lockup {type base: {"seg": 8, "tail_groups": 0}} (gen_phys.dly_lockup_cfg: the kit's staged bound RTL
is post-processed at GEN, hard cores = the kit's macro modules; the kit gets OT_DLY_SPREAD_SEG, tap_chain_affinity and
OT_TAP_CAP_RECHECK=0).

Usage: kit_dly_lockup.py RTL.sv [--out OUT.sv] [--report R.json] [--seg 8] [--inst-re RE] [--cores CORE_CLOCKS.json]
                         [--core-re RE] [--guard NAME] [--tail-groups 0] [--no-unchain] [--pad-min-stations 0]
  --cores   kit_core_clocks.json of the kit ({"rows": [{"instance": ...}]}): the hard-core instances
  --guard   put the latches under `ifdef NAME (else plain wires); default: unguarded
Never run = no change.  The split alone (no latch) is the same circuit: D stages in the same order on the same clock.
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kit_zl_lockup import LkError, _close, conns, instances  # noqa: E402

DLY = ("ot_dp_dly", "ot_dp_dly_keep")
DEFAULT_RE = r"u_(?:pd\d+|d\d+|lpad)_\w+"
IDENT = re.compile(r"[A-Za-z_]\w*")


def _param(params, key, default=1):
    m = re.search(r"\.%s\(\s*(\d+)\s*\)" % key, params)
    return int(m.group(1)) if m else default


def seg_sizes(d, seg):
    """stage counts of the segments of a D-stage line, at most `seg` each, as equal as possible, sum D"""
    n = max(1, math.ceil(d / seg))
    return [d // n + (1 if j < d % n else 0) for j in range(n)]


TAIL_MARK = "landing pad tail copy for core"
TRUNK_MARK = "landing pad trunk"
PAD_RE = re.compile(r"u_pd\d+_")


def apply(txt, seg=8, inst_re=DEFAULT_RE, cores=(), core_re=None, guard=None, tail_groups=0, core_types=(), unchain=True,
          pad_min_stations=0):
    if seg < 1:
        raise LkError("seg must be >= 1")
    mod = re.search(r"\bmodule\s+\w+\s*(#\((?:[^()]|\([^()]*\))*\))?\s*\(", txt)
    if not mod:
        raise LkError("no module header")
    hdr_end = txt.index(";", _close(txt, mod.end() - 1)) + 1
    body = txt[hdr_end:]
    rx = re.compile(inst_re)
    crx = re.compile(core_re) if core_re else None
    cores = set(cores)
    core_types = set(core_types)
    insts = instances(body)
    names = {i[2] for i in insts}
    sel, qdrv = {}, {}
    skipped = dict(expr=0, port=0)
    for mt, params, name, s, e, lp in insts:
        if mt not in DLY or not rx.fullmatch(name):
            continue
        cs = conns(body, lp, e)
        if "d" not in cs or "q" not in cs or not IDENT.fullmatch(cs["q"][0]):
            skipped["expr"] += 1
            continue
        end = body.index(";", e) + 1
        eol = body.find("\n", end)
        rest = body[end:eol if eol >= 0 else len(body)]
        sel[name] = dict(mt=mt, W=_param(params, "W"), D=_param(params, "D"), d=cs["d"][0], q=cs["q"][0], clk=cs.get("clk", ("clk",))[0],
                         span=(s, end), tail=TAIL_MARK in rest, trunk=TRUNK_MARK in rest, unch=0, stmt=body[s:end].strip() + rest.rstrip(), base=re.sub(r"\W", "_", name[2:] if name.startswith("u_") else name))
        if cs["q"][0] in qdrv:
            raise LkError(f"two selected instances drive {cs['q'][0]}")
        qdrv[cs["q"][0]] = name
    # UNCHAIN: a trunk piece fed by another trunk's end restarts from the source of the chain with the summed depth
    nunch = unch_stages = 0
    if unchain:
        orig = {n: (x["D"], x["d"]) for n, x in sel.items()}

        def parent(n, dexpr):
            m = IDENT.match(dexpr.strip())
            a = qdrv.get(m.group(0)) if m else None
            if not a or not sel[a]["trunk"] or sel[a]["W"] != sel[n]["W"]:
                return None
            ok = dexpr.strip() == sel[a]["q"] or (sel[a]["W"] == 1 and dexpr.strip() == sel[a]["q"] + "[0]")
            return a if ok else None
        for n, x in sel.items():
            if not x["trunk"]:
                continue
            extra, dexpr, seen = 0, x["d"], {n}
            a = parent(n, dexpr)
            while a and a not in seen:
                seen.add(a)
                extra += orig[a][0]
                dexpr = orig[a][1]
                a = parent(n, dexpr)
            if extra:
                x["D"] += extra
                x["d"] = dexpr
                x["unch"] = extra
                nunch += 1
                unch_stages += extra * x["W"]
    # readers of every selected q net: hard cores (out latch) / other instances
    core_read = set()
    for mt, params, name, s, e, lp in insts:
        if not (name in cores or mt in core_types or (crx and crx.fullmatch(name))):
            continue
        for port, (expr, _a, _b) in conns(body, lp, e).items():
            for w in set(IDENT.findall(expr)):
                if w in qdrv:
                    core_read.add(w)
    for x in sel.values():
        x["out"] = x["q"] in core_read
    for x in sel.values():
        m = IDENT.match(x["d"].strip())
        src = qdrv.get(m.group(0)) if m else None
        x["src"] = src
        x["in"] = bool(src) and not sel[src]["out"]
    decl, lat, edits, used = [], [], [], set(names)

    def fresh(n):
        if n in used:
            raise LkError(f"name collision: {n}")
        used.add(n)
        return n

    def wire(n, w):
        decl.append(f"    wire [{w - 1}:0] {fresh(n)};")
        return n

    nsplit = nseg = 0
    for name, x in sel.items():
        W, base = x["W"], x["base"]
        seg_x = seg
        if pad_min_stations > 0 and not x["tail"] and PAD_RE.match(name):
            seg_x = min(seg, max(1, x["D"] // pad_min_stations))
        sizes = seg_sizes(x["D"], seg_x)
        if x["tail"]:
            g = x["D"] if tail_groups <= 0 else min(x["D"], tail_groups)
            sizes = [x["D"] // g + (1 if j < x["D"] % g else 0) for j in range(g)]
        d0 = x["d"]
        if x["in"]:
            d0 = wire(f"fl_{base}_i", W)
            lat.append(dict(inst=fresh(f"u_fl_{base}_i"), W=W, d=x["d"], q=d0, kind="in", of=name, clk=x["clk"]))
        qn = x["q"]
        if x["out"]:
            qn = wire(f"{x['q']}__pl", W)
            lat.append(dict(inst=fresh(f"u_fl_{base}_o"), W=W, d=qn, q=x["q"], kind="out", of=name, clk=x["clk"]))
        if len(sizes) == 1 and not x["in"] and not x["out"] and not x["unch"]:
            continue
        ind = re.match(r"[ \t]*", body[x["span"][0]:]).group(0)
        lines = [f"{ind}// kit_dly_lockup, as bound: {x['stmt']}"] if x["tail"] else []
        cur = d0
        for j, dj in enumerate(sizes):
            last = j == len(sizes) - 1
            iname = name if len(sizes) == 1 else fresh(f"{name}_sg{j}")
            out = qn if last else wire(f"{base}_sgq{j}", W)
            lines.append(f"{ind}{x['mt']} #(.W({W}), .D({dj})) {iname} (.clk({x['clk']}), .d({cur}), .q({out}));")
            if not last:
                cur = wire(f"fl_{base}_sg{j + 1}", W)
                lat.append(dict(inst=fresh(f"u_fl_{base}_sg{j + 1}"), W=W, d=out, q=cur, kind="seg", of=name, clk=x["clk"]))
        if len(sizes) > 1:
            nsplit += 1
            nseg += len(sizes)
        edits.append((x["span"][0], x["span"][1], "\n".join(lines) + f"  // kit_dly_lockup: {name} D {x['D']}" + (f" (unchained, +{x['unch']} stages)" if x["unch"] else "")))
    if not lat and not edits:
        return txt, [], dict(selected=len(sel), split=0, segments=0, skipped=skipped)
    for a, b, new in sorted(edits, reverse=True):
        body = body[:a] + new + body[b:]
    head = [f"    // kit_dly_lockup (FABLE-FIX-KV-PV XTAP-C 11-20): {len(sel)} delay instances, {nsplit} split into {nseg} segments "
            f"(<= {seg} stages), {len(lat)} lockup latches, {sum(l['W'] for l in lat)} bits"]
    tail = []
    if guard:
        tail.append(f"`ifdef {guard}")
    tail.append("    // transparent-low lockup latches (ot_dp_lk), 0 cycles; clock_taps.tcl hangs each u_fl_* on its launch flop's tap")
    tail += [f"    ot_dp_lk #(.W({l['W']})) {l['inst']} (.clk({l['clk']}), .d({l['d']}), .q({l['q']}));" for l in lat]
    if guard:
        tail.append("`else")
        tail += [f"    assign {l['q']} = {l['d']};" for l in lat]
        tail.append("`endif")
    body = "\n" + "\n".join(head + decl) + body
    body, n = re.subn(r"(\n\s*endmodule\b)", lambda m: "\n" + "\n".join(tail) + m.group(1), body, count=1)
    if n != 1:
        raise LkError("no endmodule")
    stats = dict(selected=len(sel), split=nsplit, segments=nseg, skipped=skipped,
                 latches=len(lat), bits=sum(l["W"] for l in lat),
                 by_kind={k: sum(l["W"] for l in lat if l["kind"] == k) for k in ("seg", "in", "out")},
                 stages=sum(x["W"] * x["D"] for x in sel.values()), unchained=nunch, unchained_stages=unch_stages)
    return txt[:hdr_end] + body, lat, stats


def apply_kit(rtl_dir, seg=8, tail_groups=0, core_types=(), cores=(), unchain=True, pad_min_stations=0):
    """gen_phys entry (budgets.r_dly_lockup): the post-pass on every staged *_bound.sv of the kit that instantiates a delay cell.
    Returns {file: stats}; writes each file in place (tmp + rename)."""
    out = {}
    for f in sorted(Path(rtl_dir).glob("*_bound.sv")):
        src = f.read_text()
        if "ot_dp_dly" not in src:
            continue
        txt, lat, stats = apply(src, seg=seg, tail_groups=tail_groups, core_types=core_types, cores=cores, unchain=unchain,
                                pad_min_stations=pad_min_stations)
        if txt != src:
            tmp = f.with_name(f.name + ".dlk_tmp")
            tmp.write_text(txt)
            tmp.replace(f)
        out[f.name] = stats
    return out


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        raise SystemExit(__doc__)

    def opt(k, d=None):
        return argv[argv.index(k) + 1] if k in argv else d
    rtl = Path(argv[0])
    out = Path(opt("--out", str(rtl)))
    cores = []
    if opt("--cores"):
        cores = [r["instance"] for r in json.loads(Path(opt("--cores")).read_text())["rows"]]
    txt, lat, stats = apply(rtl.read_text(), seg=int(opt("--seg", "8")), inst_re=opt("--inst-re", DEFAULT_RE), cores=cores,
                            core_re=opt("--core-re"), guard=opt("--guard"),
                            tail_groups=int(opt("--tail-groups", "0")), unchain="--no-unchain" not in argv,
                            pad_min_stations=int(opt("--pad-min-stations", "0")))
    tmp = out.with_name(out.name + ".dlk_tmp")
    tmp.write_text(txt)
    tmp.replace(out)
    if opt("--report"):
        Path(opt("--report")).write_text(json.dumps(dict(rtl=str(out), stats=stats, entries=lat), indent=1))
    print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
