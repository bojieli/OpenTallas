#!/usr/bin/env python3
"""Die-side pushdown ECO (FT-TOOL, coordinator priority 1, 10-23): drop the pushed-down channel relays, insert the
planned channel relay stages, and reconnect every pushed lane through the hosting blocks' ft ports.

    pushdown.py die SPEC_DIR --plan PLAN.json --chains CHAINS.json --dump DUMPDIR --die D --out DIR [--blocks-as-wire]

Inputs: plan.py's plan + ftspecs, chains.sh's bit-exact chains (chains_odb.py on the die ODB), the die dump (relay
master inventory: data width per master).  Output DIR/die_eco.tcl (pure odb Tcl API, works in any OpenROAD session
that holds the die block: dbInst_create / dbNet_create / iterm connect / disconnect / dbInst_destroy) and
DIR/die_eco.json (per lane: status, sub-chains, new relays, ports used, problems).

Per pushed lane and per sub-chain (one physical relay chain = one forwarded clock), in route order:
  * channel stage at t (plan lanes[].channel_regs_t): new relays of the sub-chain's family, direction token from the
    route at t (NS = moving south, as dsfd_dvrlyh_276_NS: i on N, o on S), widths chosen so the data bits are covered
    EXACTLY (coin change over the family's widths, 1-bit relays included): no open and no tied inputs.  Static inputs
    (local clock, reset, k*, en, s ...) are copied from the nearest dropped relay of the sub-chain; chained side pins
    (ck_o->ck/ckf forwarded clock, eb->ea) continue the chain.  Placed at the route point (PLACED; the die flow
    legalises relays as it does today).
  * block segment: data bits -> <blk>/ft<k>_i[b] ... <blk>/ft<k>_o[b]; side bits (eb->ea) ride as extra ft bits after
    the data bits; the forwarded clock uses ft<k>_ck_i / ft<k>_ck_o (spec path clock "forwarded").
    --blocks-as-wire skips the block ports (the net continues over the block): validates the rest of the ECO on a die
    whose abstracts do not carry ft pins yet.
  * end: B's data input bits and the chained-side tail sinks are disconnected from their old nets and driven by the
    new chain.
Then every dropped relay is destroyed, dead buffers (no load on any output) are swept to a fixpoint, and the ECO
prints OT_ECO_OPEN_INPUTS (unconnected signal inputs on relays / buffers it touched or created: must be 0) and
OT_ECO_UNDRIVEN (touched nets with loads and no driver: must be 0).
"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom  # noqa: E402

DIR_TOKENS = ("NS", "SN", "EW", "WE")
INV_MASTER = "INVx1_ASAP7_75t_R"
SPEC_SCHEMA = "opentallas.die_feedthrough.ftspec.v1"


def direction(pts, t):
    """travel direction token at distance t along a Manhattan polyline: moving south = NS (in on N, out on S)."""
    for i in range(len(pts) - 1):
        d = geom.manhattan(pts[i], pts[i + 1])
        if t <= d or i == len(pts) - 2:
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            if abs(x1 - x0) >= abs(y1 - y0):
                return "WE" if x1 >= x0 else "EW"
            return "SN" if y1 >= y0 else "NS"
        t -= d
    return "WE"


def family_key(master):
    """master -> (family, width, dir token): dsfd_dvrlyh_276_NS -> ('dsfd_dvrlyh_#_@', 276, 'NS');
    qfd_rlyh_512_NS_89x30 -> ('qfd_rlyh_#_@_89x30' ...); a 1-bit relay keeps its own family."""
    toks = master.split("_")
    w = None
    d = None
    out = []
    for t in toks:
        if w is None and t.isdigit():
            w = int(t)
            out.append("#")
        elif d is None and t in DIR_TOKENS + ("WN", "NW", "SE", "ES", "SW", "WS", "NE", "EN"):
            d = t
            out.append("@")
        else:
            out.append(t)
    return "_".join(out), w, d


class Inventory:
    """relay masters present in the die library, by family / width / direction (from the dump's masters)."""

    def __init__(self, masters):
        self.by = defaultdict(dict)     # family stem (without size suffix) -> {(width, dir): master}
        for m in masters:
            fam, w, d = family_key(m)
            if w is None:
                continue
            stem = re.sub(r"_\d+x\d+$", "", fam)
            self.by[stem][(w, d)] = m

    def pick(self, ref_master, bits, dtok):
        """exact cover of `bits` with masters of ref_master's family in the travel direction (min count).  No cover
        -> ONE master of exactly `bits` named in the family pattern (e.g. dsfd_dvrlyh_243_NS) with needed=True: the
        die flow builds that relay kit (no wider relay with open or tied inputs, owner rule).
        -> [(master, width, needed)]"""
        fam, w0, d0 = family_key(ref_master)
        stem = re.sub(r"_\d+x\d+$", "", fam)
        fam_m = self.by.get(stem, {})
        widths = sorted({w for (w, d) in fam_m if d == dtok or d is None}, reverse=True)
        named = fam.replace("#", str(bits), 1).replace("@", dtok or (d0 or ""), 1)
        if not widths:
            return [(named, bits, True)]
        # coin change (min count) -> list of widths summing to bits
        best = {0: []}
        for b in range(1, bits + 1):
            cand = None
            for w in widths:
                if w <= b and (b - w) in best:
                    c = best[b - w] + [w]
                    if cand is None or len(c) < len(cand):
                        cand = c
            if cand is not None:
                best[b] = cand
        if bits not in best:
            return [(named, bits, True)]
        out = []
        for w in best[bits]:
            opts = {d: m for (ww, d), m in fam_m.items() if ww == w}
            out.append((opts.get(dtok) or opts[None], w, False))
        return out


def load_specs(spec_dir):
    specs = {}
    for f in sorted(Path(spec_dir).glob("*.json")):
        s = json.loads(f.read_text())
        if isinstance(s, dict) and s.get("schema") == SPEC_SCHEMA:
            specs[s["block"]] = s
    return specs


def port_flipped(spec, port_name):
    """True when the port's bit order (bit k at increasing MASTER coordinate, pushdown.place_ports) runs toward
    DECREASING die coordinate under the instance orientation (MX/MY/R180/...).  The ECO then maps die rank r to port
    bit n-1-r, so a lane's bit j sits at the same die track rank in every block and channel stage of the lane: no
    criss-cross between a mirrored block and its R0 neighbour, and the bus is never reversed end to end."""
    q = next((p for p in spec["ports"] if p["name"] == port_name), None)
    if q is None:
        return False
    W, H = spec["outline"]
    o = spec.get("orient") or "R0"
    if q["face"] in ("W", "E"):
        x = 0.0 if q["face"] == "W" else W
        a, b = geom.xform(x, q["lo"], W, H, o), geom.xform(x, q["hi"], W, H, o)
    else:
        y = 0.0 if q["face"] == "S" else H
        a, b = geom.xform(q["lo"], y, W, H, o), geom.xform(q["hi"], y, W, H, o)
    dx, dy = b[0] - a[0], b[1] - a[1]
    return (dx if abs(dx) > abs(dy) else dy) < 0


def port_bit(spec, port_name, rank, width):
    """port bit index carrying die rank `rank` of a `width`-bit port."""
    return width - 1 - rank if port_flipped(spec, port_name) else rank


def clock_port(spec, path, d):
    """forwarded-clock port of an ft path (same rule as pushdown.clock_port_name)."""
    k = path["path"]
    for q in spec["ports"]:
        if q.get("path") == k and q.get("bits") == 1 and q["dir"] == d and re.search(r"_ck_[io]$", q["name"]):
            return q["name"]
    return f"ft{k}_ck_i" if d == "input" else f"ft{k}_ck_o"


def bitpin(base, k, width):
    return f"{base}[{k}]" if width > 1 else base


def gen(spec_dir, plan, chains, relay_masters, blocks_as_wire=False, data_in_pins=("i", "a", "d"),
        data_out_pins=("o", "b", "q")):
    """-> (json report, tcl text).  relay_masters: {master: {bus: nbits}} for the die's relay families."""
    specs = load_specs(spec_dir) if spec_dir else {}
    inv = Inventory(relay_masters)
    lanes = {l["id"]: l for l in plan["lanes"]}
    T = []
    rep = []
    touched_insts, touched_nets = [], set()
    n_new = 0
    n_lr = [0]
    masters_needed = defaultdict(int)
    port_use = {}
    for cl in chains["lanes"]:
        lane = lanes.get(cl["lane"])
        rec = dict(lane=cl["lane"], status=cl.get("status"), subchains=[], problems=[])
        if lane is None or not cl["subchains"]:
            rec["problems"].append("no plan lane or no droppable sub-chain: lane left on its channel relays")
            rep.append(rec)
            continue
        pts = [tuple(p) for p in lane["pts"]]
        segs = [s for s in lane["segments"] if s.get("kind") == "block"]
        elems = [("stage", t, None) for t in lane.get("channel_regs_t", [])] + [("block", s["t_in"], s) for s in segs]
        elems.sort(key=lambda e: e[1])
        for si, sc in enumerate(cl["subchains"]):
            srec = dict(index=si, bits=len(sc["bits"]), dropped=len(sc["dropped"]), new_relays=[], blocks=[])
            sc["bits"].sort(key=lambda b: (re.sub(r"\[\d+\]$", "", b["src_bit"]),
                                           int((re.search(r"\[(\d+)\]$", b["src_bit"]) or [0, -1])[1])))
            nb = len(sc["bits"])
            # current nets: data bits, chained side signals
            cur = [b["a_net"] for b in sc["bits"]]
            chained = sc.get("chained", [])
            side = [c for c in chained if c["kind"] == "side"]
            fclk = [c for c in chained if c["kind"] == "fclk"]
            cur_side = [c["head_net"] for c in side]
            cur_fclk = [c["head_net"] for c in fclk]
            if any(x is None for x in cur_side + cur_fclk):
                rec["problems"].append(f"sub-chain {si}: a chained side input of the first dropped relay is open")
            ref_master = sc["masters"][sc["dropped"][0]]
            statics = list(sc["static"].values())
            for ei, (kind, t, seg) in enumerate(elems):
                tag = f"ft_{cl['lane']}_{si}_{ei}"
                if kind == "stage":
                    x, y = geom.point_at(pts, t)
                    dtok = direction(pts, t)
                    pick = inv.pick(ref_master, nb, dtok)
                    for m, w, needed in pick:
                        if needed:
                            if m not in masters_needed:
                                T.append(f"ft_need_master {{{m}}} {{{ref_master}}} {w}")
                            masters_needed[m] += 1
                            # pins of a needed master = the reference master's pins at the new width
                            if m not in relay_masters:
                                ref = relay_masters.get(ref_master, {})
                                relay_masters[m] = {p: (w if n > 1 else n) for p, n in ref.items()}
                                relay_masters.setdefault("__outputs__", {})[m] = _outputs(relay_masters, ref_master)
                    pick = [(m, w) for m, w, _ in pick]
                    near = min(statics, key=lambda s: geom.manhattan(s["xy"], (x, y))) if statics else None
                    nxt = []
                    off = 0
                    first_inst = None
                    for ri, (m, w) in enumerate(pick):
                        inst = f"{tag}_r{ri}"
                        n_new += 1
                        first_inst = first_inst or inst
                        T.append(f"ft_inst {{{inst}}} {m} {x:.3f} {y + ri * 2.0:.3f}")
                        touched_insts.append(inst)
                        buses = relay_masters.get(m, {})
                        din = next((p for p in data_in_pins if p in buses), None)
                        dout = next((p for p in data_out_pins if p in buses), None)
                        if din is None or dout is None:
                            rec["problems"].append(f"{m}: data pins not found")
                            continue
                        for k in range(w):
                            T.append(f"ft_conn {{{cur[off + k]}}} {{{inst}}} {{{bitpin(din, k, w)}}}")
                            nn = f"{inst}_q[{k}]" if w > 1 else f"{inst}_q"
                            T.append(f"ft_conn {{{nn}}} {{{inst}}} {{{bitpin(dout, k, w)}}}")
                            nxt.append(nn)
                            touched_nets.add(nn)
                        # chained side pins: every relay of the stage takes the incoming chain; the first drives on
                        for lst, cl_ in ((cur_side, side), (cur_fclk, fclk)):
                            for j, c in enumerate(cl_):
                                if c["in_pin"] in buses and lst[j]:
                                    T.append(f"ft_conn {{{lst[j]}}} {{{inst}}} {{{c['in_pin']}}}")
                        for j, c in enumerate(side + fclk):
                            if ri == 0 and c["out_pin"] in buses:
                                nn = f"{inst}_{c['out_pin']}"
                                T.append(f"ft_conn {{{nn}}} {{{inst}}} {{{c['out_pin']}}}")
                                touched_nets.add(nn)
                        # static inputs copied from the nearest dropped relay
                        chained_in = {c["in_pin"] for c in chained}
                        for pin in buses:
                            if pin in (din,) or pin in chained_in or pin == dout or pin in [c["out_pin"] for c in chained]:
                                continue
                            if pin in _outputs(relay_masters, m):
                                continue
                            lr = (near or {}).get("local_regs", {}).get(pin)
                            if lr is not None:          # station-local register: re-create on this stage's clock
                                if not cur_fclk or not cur_fclk[0] or not lr.get("d_net"):
                                    rec["problems"].append(f"{inst}: local register for {pin} has no clock/D source")
                                    continue
                                fl = f"{inst}_lr_{pin}"
                                T.append(f"ft_inst {{{fl}}} {lr['flop_master']} {x:.3f} {y + ri * 2.0 + 1.0:.3f}")
                                T.append(f"ft_conn {{{cur_fclk[0]}}} {{{fl}}} {{CLK}}")
                                T.append(f"ft_conn {{{lr['d_net']}}} {{{fl}}} {{D}}")
                                q = f"{fl}_q"
                                T.append(f"ft_conn {{{q}}} {{{fl}}} {{{lr['flop_out']}}}")
                                if lr.get("n_inv", 0) % 2:
                                    iv = f"{fl}_inv"
                                    T.append(f"ft_inst {{{iv}}} {INV_MASTER} {x:.3f} {y + ri * 2.0 + 1.5:.3f}")
                                    T.append(f"ft_conn {{{q}}} {{{iv}}} {{A}}")
                                    q = f"{iv}_y"
                                    T.append(f"ft_conn {{{q}}} {{{iv}}} {{Y}}")
                                T.append(f"ft_conn {{{q}}} {{{inst}}} {{{pin}}}")
                                n_lr[0] += 1
                                continue
                            net = (near or {}).get("pins", {}).get(pin)
                            if net is None:
                                cands = [s["pins"].get(pin) for s in statics if s["pins"].get(pin)]
                                net = cands[0] if cands else None
                            if net is None:
                                rec["problems"].append(f"{inst}: static input {pin} has no source net (would be open)")
                                continue
                            T.append(f"ft_conn {{{net}}} {{{inst}}} {{{pin}}}")
                        off += w
                    cur = nxt
                    for j, c in enumerate(side):
                        if c["out_pin"] in relay_masters.get(pick[0][0], {}):
                            cur_side[j] = f"{first_inst}_{c['out_pin']}"
                    for j, c in enumerate(fclk):
                        if c["out_pin"] in relay_masters.get(pick[0][0], {}):
                            cur_fclk[j] = f"{first_inst}_{c['out_pin']}"
                    srec["new_relays"].append(dict(t=round(t, 1), relays=[m for m, _ in pick], xy=[round(x, 1),
                                                                                                    round(y, 1)]))
                else:
                    blkname = seg["block"]
                    if blocks_as_wire:
                        srec["blocks"].append(dict(block=blkname, mode="wire"))
                        continue
                    sp = specs.get(blkname)
                    path = None
                    for p in (sp or {}).get("paths", []):
                        if p.get("lane") == cl["lane"] or cl["lane"] in p.get("shared_lanes", []):
                            path = p
                            break
                    if path is None:
                        rec["problems"].append(f"{blkname}: no ft spec path for lane {cl['lane']}")
                        continue
                    # sub-chains of one lane share the path's bits in order: [sc0 data, sc0 side, sc1 data, ...]
                    used = port_use.setdefault((blkname, path["path"]), [0, None])
                    off0 = used[0]
                    need = nb + len(side)
                    if off0 + need > path["bits"]:
                        rec["problems"].append(f"{blkname} {path['in']}: {path['bits']} ft bits < {off0 + need} "
                                               "(data + side of all sub-chains)")
                        continue
                    used[0] += need
                    ins = cur + cur_side
                    outs = []
                    pw = path["bits"]
                    for k in range(need):
                        bi = port_bit(sp, path["in"], off0 + k, pw)
                        bo = port_bit(sp, path["out"], off0 + k, pw)
                        if bi != bo:
                            rec.setdefault("warnings", []).append(f"{blkname}: in/out ports of path {path['path']} "
                                                                  "flip differently (L path: bits cross in the block)")
                        T.append(f"ft_conn {{{ins[k]}}} {{{blkname}}} {{{path['in']}[{bi}]}}")
                        nn = f"{blkname}_{path['out']}[{bo}]"
                        T.append(f"ft_conn {{{nn}}} {{{blkname}}} {{{path['out']}[{bo}]}}")
                        outs.append(nn)
                        touched_nets.add(nn)
                    cur, cur_side = outs[:nb], outs[nb:]
                    if fclk:
                        if path.get("clock", sp.get("clock")) != "forwarded":
                            rec["problems"].append(f"{blkname}: sub-chain has a forwarded clock but the ft path is "
                                                   "block-clocked")
                        elif used[1]:
                            # parallel physical chains of one lane (S81: 4 x 276 b) become ONE station chain in the
                            # block, clocked by the first chain's forwarded clock; every chain continues on its ck_o
                            cur_fclk = [used[1]] + cur_fclk[1:]
                            rec.setdefault("notes", []).append(f"{blkname}: sub-chain {si} joins the path clock")
                        else:
                            cki, cko = clock_port(sp, path, "input"), clock_port(sp, path, "output")
                            T.append(f"ft_conn {{{cur_fclk[0]}}} {{{blkname}}} {{{cki}}}")
                            nn = f"{blkname}_{cko}"
                            T.append(f"ft_conn {{{nn}}} {{{blkname}}} {{{cko}}}")
                            used[1] = nn
                            cur_fclk = [nn] + cur_fclk[1:]
                            touched_nets.add(nn)
                    srec["blocks"].append(dict(block=blkname, path=path["path"], in_=path["in"], out=path["out"]))
            # end: B's data inputs and the side tails
            for k, b in enumerate(sc["bits"]):
                inst, pin = b["b_pin"].rsplit("/", 1)
                T.append(f"ft_conn {{{cur[k]}}} {{{inst}}} {{{pin}}}")
            for lst, cl_ in ((cur_side, side), (cur_fclk, fclk)):
                for j, c in enumerate(cl_):
                    for tsink in c["tail_sinks"]:
                        inst, pin = tsink.rsplit("/", 1)
                        if lst[j]:
                            T.append(f"ft_conn {{{lst[j]}}} {{{inst}}} {{{pin}}}")
            rec["subchains"].append(srec)
        rec["problems"] = sorted(set(rec["problems"]))
        for k_ in ("warnings", "notes"):
            if k_ in rec:
                rec[k_] = sorted(set(rec[k_]))
        rep.append(rec)
    dropped = chains.get("dropped_all", [])
    head = [
        "# GENERATED by tools/die_feedthrough/die_eco.py (pushdown.py die): feedthrough die ECO, odb Tcl API.",
        "set ftblk [ord::get_db_block]; set ftdb [ord::get_db]; set ft_touched {}",
        "proc ft_net {name} { set n [$::ftblk findNet $name]; if {$n eq \"NULL\"} { set n [odb::dbNet_create $::ftblk "
        "$name] }; return $n }",
        "# a relay width the library lacks: in --stand-in mode (validation) an abstract clone of the reference relay",
        "# with its buses cut to the width (pins only); otherwise an error naming the kit the die flow must build",
        "if {![info exists ft_stand_in]} { set ft_stand_in 0 }",
        "proc ft_need_master {name ref w} {",
        "  if {[$::ftdb findMaster $name] ne \"NULL\"} return",
        "  if {!$::ft_stand_in} { error \"FT_ECO needs relay kit $name (width $w, like $ref)\" }",
        "  set r [$::ftdb findMaster $ref]; set m [odb::dbMaster_create [$r getLib] $name]",
        "  $m setWidth [$r getWidth]; $m setHeight [$r getHeight]; $m setType [$r getType]",
        "  foreach mt [$r getMTerms] { set n [$mt getName]",
        "    if {[regexp {^(.*)\\[([0-9]+)\\]$} $n -> b k] && $k >= $w} continue",
        "    odb::dbMTerm_create $m $n [$mt getIoType] [$mt getSigType] }",
        "  $m setFrozen; puts \"FT_ECO_STAND_IN $name\" }",
        "proc ft_inst {name master x y} {",
        "  set m [$::ftdb findMaster $master]; if {$m eq \"NULL\"} { error \"FT_ECO no master $master\" }",
        "  set i [odb::dbInst_create $::ftblk $m $name]",
        "  $i setLocation [ord::microns_to_dbu $x] [ord::microns_to_dbu $y]; $i setPlacementStatus PLACED",
        "  lappend ::ft_touched $i }",
        "proc ft_conn {net inst pin} {",
        "  set i [$::ftblk findInst $inst]; if {$i eq \"NULL\"} { error \"FT_ECO no inst $inst\" }",
        "  set it [$i findITerm $pin]",
        "  if {$it eq \"NULL\" && ![string match {*\\]} $pin]} { set it [$i findITerm \"$pin\\[0\\]\"] }",
        "  if {$it eq \"NULL\" && [regexp {^(.*)\\[0\\]$} $pin -> pb]} { set it [$i findITerm $pb] }",
        "  if {$it eq \"NULL\"} { error \"FT_ECO no pin $inst/$pin\" }",
        "  if {[$it getNet] ne \"NULL\"} { $it disconnect }",
        "  $it connect [ft_net $net] }",
    ]
    tail = [
        "# drop the pushed-down relays",
        "set ft_nd 0",
        "foreach nm {" + " ".join("{" + r + "}" for r in dropped) + "} {",
        "  set i [$ftblk findInst $nm]; if {$i ne \"NULL\"} { odb::dbInst_destroy $i; incr ft_nd } }",
        "# station-local registers of the dropped relays (and their BUF/INV path): destroyed once they drive nothing",
        "set ft_lc {" + " ".join("{" + c + "}" for c in chains.get("dropped_cells", [])) + "}",
        "set ft_nl 0; set ft_sw 1",
        "while {$ft_sw} { set ft_sw 0; set rest {}",
        "  foreach nm $ft_lc { set i [$ftblk findInst $nm]; if {$i eq \"NULL\"} continue; set live 0",
        "    foreach it [$i getITerms] { if {[[$it getMTerm] getIoType] eq \"OUTPUT\"} { set n [$it getNet]",
        "      if {$n ne \"NULL\" && [llength [$n getITerms]] > 1} { set live 1 } } }",
        "    if {$live} { lappend rest $nm } else { odb::dbInst_destroy $i; incr ft_nl; set ft_sw 1 } }",
        "  set ft_lc $rest }",
        "# sweep dead buffers (no load on the output) to a fixpoint",
        "set ft_sw 1; set ft_nb 0",
        "while {$ft_sw} { set ft_sw 0",
        "  foreach i [$ftblk getInsts] {",
        "    if {![regexp {^(BUF|INV|HB[0-9]|CKBUF|CKINV)} [[$i getMaster] getName]]} continue",
        "    set live 0",
        "    foreach it [$i getITerms] { if {[[$it getMTerm] getIoType] eq \"OUTPUT\"} { set n [$it getNet]",
        "      if {$n ne \"NULL\" && ([llength [$n getITerms]] > 1 || [llength [$n getBTerms]] > 0)} { set live 1 } } }",
        "    if {!$live} { odb::dbInst_destroy $i; incr ft_nb; set ft_sw 1 } } }",
        "# checks: open inputs on the created relays, undriven touched nets",
        "set ft_open 0",
        "foreach i $ft_touched { foreach it [$i getITerms] { set mt [$it getMTerm]",
        "  if {[$mt getIoType] eq \"INPUT\" && [$mt getSigType] ni {POWER GROUND} && [$it getNet] eq \"NULL\"} {",
        "    incr ft_open; puts \"FT_ECO_OPEN [$i getName]/[$mt getName]\" } } }",
        "set ft_und 0",
        "foreach n [$ftblk getNets] { set d 0; set l 0",
        "  if {[$n getSigType] in {POWER GROUND}} continue",
        "  foreach it [$n getITerms] { if {[[$it getMTerm] getIoType] eq \"OUTPUT\"} { incr d } else { incr l } }",
        "  foreach bt [$n getBTerms] { if {[$bt getIoType] eq \"INPUT\"} { incr d } else { incr l } }",
        "  if {$l > 0 && $d == 0} { incr ft_und; if {$ft_und <= 20} { puts \"FT_ECO_UNDRIVEN [$n getName]\" } } }",
        "puts \"OT_ECO_DROPPED $ft_nd OT_ECO_LOCALREG_DROPPED $ft_nl OT_ECO_NEW [llength $ft_touched] OT_ECO_BUF_SWEPT $ft_nb "
        "OT_ECO_OPEN_INPUTS $ft_open OT_ECO_UNDRIVEN $ft_und\"",
    ]
    js = dict(schema="opentallas.die_feedthrough.die_eco.v2", lanes=rep, relays_dropped=len(dropped),
              relays_new=n_new, masters_needed=dict(masters_needed), local_regs_new=n_lr[0], cells_dropped=len(chains.get("dropped_cells", [])),
              blocks_as_wire=blocks_as_wire,
              lanes_with_problems=sum(1 for r in rep if r["problems"]))
    return js, "\n".join(head + T + tail) + "\n"


_OUT_CACHE = {}


def _outputs(relay_masters, m):
    return relay_masters.get("__outputs__", {}).get(m, set())


def relay_inventory(dump_dir, relay_re):
    """{master: {bus: nbits}} + '__outputs__' {master: {output buses}} from a dump's mpins.tsv.gz."""
    import gzip
    rre = re.compile(relay_re)
    inv = {}
    outs = defaultdict(set)
    for ln in gzip.open(Path(dump_dir) / "mpins.tsv.gz", "rt"):
        f = ln.rstrip("\n").split("\t")
        if not rre.search(f[0]):
            continue
        inv.setdefault(f[0], {})[f[1]] = int(f[3])
        if f[2] == "OUTPUT":
            outs[f[0]].add(f[1])
    inv["__outputs__"] = dict(outs)
    return inv
