"""Cut a two-partition proof plan out of a full die plan (CP1: abutment / planned-channel proof).

    python3 tools/die_plan/pair.py PLAN.json --parts A,B --out DIR [--channel UM] [--name NAME]

- The new die is the bounding box of partitions A and B, translated to (0, 0).
- --channel UM moves the partition with the larger coordinate along the shared axis by UM, which must be a multiple of
  die.grid_um. Every A<->B port is then routed across a planned die.channels entry; types, pins and kits are unchanged.
- Every other port of A or B becomes die IO on the same face window, so pins and pin tables are identical to the full
  plan. A port that runs from the far partition through the near one is still a single pair-die IO port, because both
  faces lie on the pair die edge.
- Partition contents are replaced by one generated proof leaf per type (`<module>_proof_leaf`, written to DIR/leaves.sv).
  It registers every functional in-bus and drives every functional out-bus from a registered XOR fold of the inputs.
  The leaf is a vehicle for the boundary, face and channel proof only. It is not the partition's real logic.
- Without --cores, hard cores (`hard_cores[]`) are dropped with the contents: the proof netlist does not instantiate them.
- Lanes are rebuilt by following ft slots. Latency is left for `gen.py latency`.
- CP2 (hard cores): --cores instantiates every hard_cores[] module in the proof leaf (black box: the kit gets its
  LEF / liberty through gen_phys.type_macros -> ADDITIONAL_LEFS / ADDITIONAL_LIBS), clock pins (liberty
  `clock : true`, else LEF USE CLOCK) on clk, every other core pin driven from / captured by its own stub flop; the
  plan's hard_cores[].inst becomes `u_leaf.<last name>` (the flattened kit instance place_macro finds).
  --core-views DIR fills hard_cores[].lef / .lib (TT) where lib is null (DIR from fetch_core_views.sh).
  --core-taps adds an EARLY clock tap (clock.taps kind core, insertion_ps = TT max_clock_tree_path) for every core
  clock pin whose internal latency > common latency - 40 ps, and sets clock.core_taps = 'early' (gen_phys: port
  clk_c<k>, source latency -(insertion - common) in the kit SDC and the die STA).
- The pair keeps the full die's spine geometry (clock.spine.die_root_um, die_outline_um, part_die_origin_um) for the
  die STA branch model (spine.py); clock.spine.root_um is the pair's own (routing) root.
"""
import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
from schema import DIE_PART, OPP  # noqa: E402


def along_axis(face):
    return 1 if face in "EW" else 0     # E/W face: the along-face (window) coordinate is y


def _fold(dst, w, src, n):
    """`dst <= dst ^ fold(src)`: every one of the n src bits reaches some dst bit (K = ceil(n / w) slices of a
    replicated src), so no captured core output is optimised away."""
    if not n:
        return f"    always @(posedge clk) {dst} <= ~{dst};"
    k = max(1, -(-n // w))
    rep = -(-k * w // n)
    lines = [f"    wire [{rep * n - 1}:0] {dst}_x = {{{rep}{{{src}}}}};"]
    terms = " ^ ".join(f"{dst}_x[{i * w} +: {w}]" for i in range(k))
    lines.append(f"    always @(posedge clk) {dst} <= {dst} ^ {terms};")
    return "\n".join(lines)


def core_ports(core, root=None):
    """(inputs, outputs, clocks) of a hard core from its LEF (PIN / DIRECTION / USE) and liberty (clock : true):
    inputs / outputs [(pin, width or 0 for a scalar)], clocks [pin].  Raises when the views are missing."""
    import cores as C
    if not core.get("lef") or not C.resolve(core["lef"], root).is_file():
        raise SystemExit(f"--cores: core {core['inst']} ({core.get('module')}) has no LEF view "
                         f"({core.get('lef')}); pass --core-views")
    pins = C.lef_pins(C.resolve(core["lef"], root), core.get("module"))
    cks = set(C.clock_pins(core, root))
    if not cks:
        raise SystemExit(f"--cores: core {core['inst']}: no clock pin (lib clock : true / LEF USE CLOCK)")
    miss = cks - set(pins)
    if miss:
        raise SystemExit(f"--cores: core {core['inst']}: lib clock pins {sorted(miss)} not in the LEF")
    ins, outs = [], []
    for n, p in sorted(pins.items()):
        if p["use"] in ("POWER", "GROUND") or n in cks:
            continue
        if p["dir"] == "INPUT":
            ins.append((n, p["width"]))
        elif p["dir"] == "OUTPUT":
            outs.append((n, p["width"]))
        else:
            raise SystemExit(f"--cores: core {core['inst']} pin {n}: direction {p['dir']} not supported")
    return ins, outs, sorted(cks)


def proof_leaf(module, ins, outs, cores=()):
    """ins/outs: [(bus, width)].  Registered: every out bit = XOR of a rotated fold of all input bits.
    cores: [(leaf inst, core module, core ins, core outs, clock pins)] (CP2, --cores): each hard core is instantiated
    as a black box (its liberty view in the kit), every clock pin on clk, every input pin driven by its own stub flop
    and every output pin captured by its own stub flop (reg-to-core / core-to-reg paths; the core is a real clock
    sink).  Stub flops are local: core outputs -> capture flops -> XOR fold -> the same core's input flops."""
    name = f"{module}_proof_leaf"
    decl = ["input wire clk"] + [f"input wire [{w - 1}:0] {b}" for b, w in ins] + \
        [f"output reg [{w - 1}:0] {b}" for b, w in outs]
    body = []
    tot = sum(w for _, w in ins)
    if tot:
        body.append(f"    wire [{tot - 1}:0] cat = {{{', '.join(b for b, _ in ins)}}};")
        body.append(f"    reg [{tot - 1}:0] q;")
        body.append("    always @(posedge clk) q <= cat;")
    for k, (b, w) in enumerate(outs):
        if not tot:
            body.append(f"    always @(posedge clk) {b} <= ~{b};")
            continue
        # fold q into w bits: bit i = q[i % tot] ^ q[(i + k + 1) * 7 % tot]
        terms = ", ".join(f"q[{(i % tot)}] ^ q[{((i + k + 1) * 7) % tot}]" for i in reversed(range(w)))
        body.append(f"    always @(posedge clk) {b} <= {{{terms}}};")
    for inst, cmod, cin, cout, cks in cores:
        ni = sum(max(1, w) for _, w in cin)
        no = sum(max(1, w) for _, w in cout)
        body.append(f"    // hard core {inst} ({cmod}): {ni} input / {no} output pin flops, clocks {' '.join(cks)}")
        if ni:
            body.append(f"    reg [{ni - 1}:0] {inst}_ci;")
        if no:
            body.append(f"    wire [{no - 1}:0] {inst}_cw;")
            body.append(f"    reg [{no - 1}:0] {inst}_co;")
            body.append(f"    always @(posedge clk) {inst}_co <= {inst}_cw;")
        conn = [f".{c}(clk)" for c in cks]
        o = 0
        for n, w in cin:
            conn.append(f".{n}({inst}_ci[{o + max(1, w) - 1}:{o}])" if w else f".{n}({inst}_ci[{o}])")
            o += max(1, w)
        o = 0
        for n, w in cout:
            conn.append(f".{n}({inst}_cw[{o + max(1, w) - 1}:{o}])" if w else f".{n}({inst}_cw[{o}])")
            o += max(1, w)
        # keep: the stub loop (core -> capture flops -> fold -> input flops -> core) reaches no leaf output, so without
        # it Yosys sweeps the core and every stub flop (CP2 probe 10-23: no core left after opt)
        body.append(f"    (* keep *) {cmod} {inst} (\n        " + ",\n        ".join(conn) + "\n    );")
        if ni:
            body.append(_fold(f"{inst}_ci", ni, f"{inst}_co", no))
        elif no:
            # no inputs to fold into: the captured outputs drive a parity flop each cycle (kept, observable)
            body.append(f"    (* keep *) reg {inst}_par;")
            body.append(f"    always @(posedge clk) {inst}_par <= ^{inst}_co;")
    return f"module {name} (\n    " + ",\n    ".join(decl) + "\n);\n" + "\n".join(body) + "\nendmodule\n", name


CORE_TAP_MARGIN_PS = 40.0   # a core clock pin hung straight off a tap port still sees ~a buffer + wire (>= ~20-40 ps)


def core_tap_xy(t, core, pin, taken, root=None):
    """type-frame site of an early core tap: the core's clock pin (LEF rect centre, core frame, R0/MX/MY/R180 in the
    core outline) moved off every hard core into a channel (schema.tap_clear)."""
    import cores as C
    p = C.lef_pins(C.resolve(core["lef"], root), core.get("module"))[pin]
    cw, ch = core["outline_um"]
    x, y = p["xy"] or (cw / 2, ch / 2)
    o = core.get("orient", "R0")
    x, y = {"R0": (x, y), "MX": (x, ch - y), "MY": (cw - x, y), "R180": (cw - x, ch - y)}[o]
    ox, oy = core.get("track_offset_um", [0.0, 0.0])
    x, y = core["origin_um"][0] + ox + x, core["origin_um"][1] + oy + y
    return S.tap_clear(t, x, y, taken)


def add_core_taps(P, tn, t, target_ps, root=None):
    """CP2: an EARLY dedicated tap (clock.taps[] kind 'core', insertion_ps = the core's internal clock latency, QC
    convention) for every hard-core clock pin whose internal latency (TT max_clock_tree_path, rise) leaves no room on a
    grid tap: latency > target - CORE_TAP_MARGIN_PS.  The type's clock.core_taps = 'early' switches them on in the
    kit (port clk_c<k>, spine delivers it (latency - target) early).  Returns [(tap name, latency)]."""
    import cores as C
    ck = t.setdefault("clock", {})
    taps = [tp for tp in ck.get("taps", []) if tp.get("kind") != "core"]
    taken = [(x, y) for _, x, y in S.tap_grid(P, tn)]
    added = []
    for c in t.get("hard_cores", []):
        for pin, v in sorted(C.clock_pins(c, root).items()):
            if v["rise"] <= target_ps - CORE_TAP_MARGIN_PS:
                continue
            x, y = core_tap_xy(t, c, pin, taken, root)
            taken.append((x, y))
            nm = f"{c['inst']}.{pin}"
            taps.append(dict(name=nm, xy=[round(x, 4), round(y, 4)], kind="core", orient=c.get("orient", "R0"),
                             insertion_ps=round(v["rise"], 1), insertion_tol_ps=float(P.clock["insertion_tol_ps"]),
                             budget_owner=f"{c.get('module')} TT lib max_clock_tree_path rise ({pin}); pair.py --core-taps"))
            added.append((nm, round(v["rise"], 1)))
    if added:
        ck["taps"] = taps
        ck["core_taps"] = "early"
    return added


def extract(raw, parts, channel_um=0.0, name=None, cores=False, core_taps=False, plan_dir=None, root=None):
    """cores: instantiate every hard core of each type in its proof leaf (CP2); core_taps: early core taps
    (add_core_taps); plan_dir: the source plan's directory (relative hard_cores[].pins_file become absolute)."""
    P = S.Plan(raw)
    A, B = parts
    ra, rb = P.rect(A), P.rect(B)
    # shared face / axis
    if abs(ra[2] - rb[0]) < 1e-6 or abs(rb[2] - ra[0]) < 1e-6:
        ax = 0
    elif abs(ra[3] - rb[1]) < 1e-6 or abs(rb[3] - ra[1]) < 1e-6:
        ax = 1
    else:
        raise SystemExit(f"{A} and {B} do not abut")
    far = B if (rb[ax] > ra[ax]) else A
    g = P.grid
    if channel_um and abs(channel_um / g - round(channel_um / g)) > 1e-6:
        raise SystemExit(f"--channel {channel_um} is not a multiple of the die lattice {g}")
    x0, y0 = min(ra[0], rb[0]), min(ra[1], rb[1])
    x1, y1 = max(ra[2], rb[2]), max(ra[3], rb[3])
    shift = {A: [0.0, 0.0], B: [0.0, 0.0]}
    shift[far][ax] = channel_um
    W = x1 - x0 + (channel_um if ax == 0 else 0.0)
    H = y1 - y0 + (channel_um if ax == 1 else 0.0)
    die = copy.deepcopy(P.die)
    die["name"] = name or f"pair_{A}_{B}"
    die["label"] = f"CP1 pair {A} | {B} from {P.name}" + (f", planned channel {channel_um:g} um" if channel_um
                                                         else ", abutted")
    die["outline_um"] = [round(W, 4), round(H, 4)]
    die["channels"] = []
    types = {}
    leaves = ["`timescale 1ns/1ps", "`default_nettype none",
              f"// GENERATED by tools/die_plan/pair.py: proof leaves for the CP1 pair {A}/{B} of {P.name}.",
              "// Vehicle for the boundary / face / channel proof only; not the partitions' real logic."]
    for p in (A, B):
        tn = P.parts[p]["type"]
        if tn in types:
            continue
        t = copy.deepcopy(P.types[tn])
        ins = [(b["name"], b["width"]) for b in t.get("buses", []) if b["dir"] == "in"]
        outs = [(b["name"], b["width"]) for b in t.get("buses", []) if b["dir"] == "out"]
        lcores = []
        if cores:
            seen = set()
            for c in t.get("hard_cores", []):
                li = re.sub(r"[^A-Za-z0-9_]", "_", c["inst"].split(".")[-1])
                if li in seen or li == "q" or li == "cat":
                    raise SystemExit(f"type {tn}: hard core leaf instance name {li} not unique")
                seen.add(li)
                cin, cout, cks = core_ports(c, root)
                lcores.append((li, c.get("module", c["inst"]), cin, cout, cks))
                c["note"] = (c.get("note", "") + f" CP2 proof leaf core (was {c['inst']})").strip()
                c["inst"] = f"u_leaf.{li}"
        elif t.get("hard_cores"):
            print(f"pair.py: WARNING type {tn} has {len(t['hard_cores'])} hard_cores but --cores is off: the kit "
                  "places macros the proof leaf does not instantiate", file=sys.stderr)
        for c in t.get("hard_cores", []):
            if c.get("pins_file") and plan_dir and not Path(c["pins_file"]).is_absolute():
                c["pins_file"] = str((Path(plan_dir) / c["pins_file"]).resolve())
        v, lname = proof_leaf(t["module"], ins, outs, lcores)
        leaves.append(v)
        for b in t.get("buses", []):
            b["leaf"] = f"u_leaf.{b['name']}"
        t["contents"] = [{"inst": "u_leaf", "module": lname, "status": "new", "bind": {"clk": "clk"},
                          "note": "CP1 proof leaf (pair.py)"}]
        t["sources"] = ["leaves.sv"]
        t.pop("kit", None)
        # CP1-R10 (10-24): the proof leaf replaces ALL contents, hard cores included.  S81 v4.7+ types carry
        # hard_cores[] with LEF views; kept, the kit's macro_place.tcl places instances the proof netlist does not
        # have (ORFS stops in floorplan).  Dropped with a note, so the pair kit is the seam vehicle only.
        hc = None if cores else t.pop("hard_cores", None)      # CP2 --cores keeps them (black boxes in the leaf)
        if not cores:
            # Dedicated early taps refer to the hard cores removed from this proof leaf.
            ck = t.get("clock", {})
            if "taps" in ck:
                ck["taps"] = [tap for tap in ck["taps"] if tap.get("kind") != "core"]
            ck.pop("core_taps", None)
        if hc:
            t["note"] = (t.get("note", "") + f" [pair.py: {len(hc)} hard_cores dropped, proof leaf only]").strip()
        types[tn] = t
    leaves.append("`default_nettype wire")
    newparts = []
    for p in (A, B):
        q = copy.deepcopy(P.parts[p])
        ox, oy = q["origin_um"]
        q["origin_um"] = [round(ox - x0 + shift[p][0], 4), round(oy - y0 + shift[p][1], 4)]
        newparts.append(q)
    # ports
    ports, xing = [], []
    off = {p: (x0 - shift[p][0], y0 - shift[p][1]) for p in (A, B)}
    for pid, pr in P.ports.items():
        ends = {pr["src"]["part"], pr["dst"]["part"]}
        if not ends & {A, B}:
            continue
        q = {k: copy.deepcopy(pr[k]) for k in ("id", "width", "face", "layers", "window_um", "order", "epoch", "note")
             if k in pr}
        q["src"], q["dst"] = dict(pr["src"]), dict(pr["dst"])
        inside = [e for e in ("src", "dst") if pr[e]["part"] in (A, B)]
        ref = pr[inside[0]]["part"]
        a = along_axis(pr["face"])
        q["window_um"] = [round(v - off[ref][a], 4) for v in pr["window_um"]]
        if len(inside) == 1:
            o = "dst" if inside[0] == "src" else "src"
            if pr[o]["part"] != DIE_PART:
                q[o] = {"part": DIE_PART, "bus": f"io_{pid}"}
                if o == "src":                       # @die src: face = the dst's die-edge face
                    q["face"] = OPP[pr["face"]]
                q["epoch"] = False
                q["note"] = f"pair.py: was {pr[o]['part']}.{pr[o]['bus']}"
        elif channel_um:
            xing.append(pid)
        q.pop("geom_from", None)
        ports.append(q)
    if channel_um and xing:
        lay = sorted({ln for q in ports if q["id"] in xing for ln in q["layers"]}, key=lambda s: int(s[1:]))
        die["channels"].append({"name": f"ch_{A}_{B}", "between": [A, B], "width_um": channel_um, "layers": lay,
                                "ports": xing, "reason": "CP1-B planned channel: A<->B buses routed at die level"})
    # lanes: follow ft slots (port dst = slot _i -> the port whose src is the same slot's _o on that partition)
    by_src = {(q["src"]["part"], q["src"]["bus"]): q["id"] for q in ports}
    slot_in = {}
    for q in ports:
        d = q["dst"]
        if d["part"] != DIE_PART and d["bus"].endswith("_i"):
            sn = d["bus"][:-2]
            if any(s["name"] == sn for s in types[P.parts[d["part"]]["type"]].get("ft_slots", [])):
                slot_in[q["id"]] = (d["part"], sn + "_o")
    feeds = {by_src[v] for v in slot_in.values() if v in by_src}
    lanes = []
    for q in ports:
        if q["id"] in feeds:
            continue
        chain = [q["id"]]
        while chain[-1] in slot_in and slot_in[chain[-1]] in by_src:
            chain.append(by_src[slot_in[chain[-1]]])
        lanes.append({"id": chain[0], "ports": chain})
    out = {"schema": raw["schema"], "note": f"CP1 pair cut from {P.name} by tools/die_plan/pair.py",
           "die": die, "partition_types": types, "partitions": newparts, "ports": ports, "lanes": lanes,
           "clock": copy.deepcopy(raw["clock"]), "reset": copy.deepcopy(raw["reset"]),
           "census": {"none": f"CP1 proof pair cut from {P.name}: census coverage is checked on the full plan"}}
    if "budgets" in raw:
        out["budgets"] = copy.deepcopy(raw["budgets"])
    sp = out["clock"].setdefault("spine", {})
    # CP2 spine branch model (spine.py): keep the FULL die's spine geometry, so the pair die STA can model each
    # partition tap's branch from the real die root (the pair's own root below only routes the pair die)
    sp["die_root_um"] = list(sp.get("die_root_um") or sp.get("root_um") or [P.W / 2, P.H / 2])
    sp["die_outline_um"] = list(sp.get("die_outline_um") or [P.W, P.H])
    prev = sp.get("part_die_origin_um", {})
    sp["part_die_origin_um"] = {p: list(prev.get(p, P.parts[p]["origin_um"])) for p in (A, B)}
    sp["root_um"] = [round(math.floor(W / 2 / g) * g, 4), round(math.floor(H / 2 / g) * g, 4)]
    if core_taps:
        Q = S.Plan(out)
        out["core_taps_added"] = {tn: add_core_taps(Q, tn, t, float(Q.clock["insertion_ps"]), root)
                                  for tn, t in out["partition_types"].items()}
    return out, "\n".join(leaves) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--parts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--channel", type=float, default=0.0)
    ap.add_argument("--name")
    ap.add_argument("--cores", action="store_true",
                    help="CP2: the proof leaf instantiates every hard core (black box, clock pins on clk, stub flops "
                         "on every core pin); kits place them from hard_cores[].lef/.lib")
    ap.add_argument("--core-views", metavar="DIR",
                    help="fill hard_cores[].lef/.lib (TT) from DIR/<tile>/views/<module>/ where lib is null "
                         "(fetch_core_views.sh writes this layout)")
    ap.add_argument("--core-taps", action="store_true",
                    help="early dedicated clock taps (clock.taps kind core) for core clock pins whose internal "
                         "latency leaves no room under the common latency")
    a = ap.parse_args(argv)
    raw = S.load(a.plan)
    if a.core_views:
        import cores as C
        done, miss = C.fill_views(raw, a.core_views)
        print(f"core views: {len(done)} hard_cores filled from {a.core_views}" +
              (f"; MISSING {miss[:8]}" if miss else ""))
        if miss and a.cores:
            want = {P_["type"] for P_ in raw["partitions"] if P_["name"] in a.parts.split(",")}
            bad = [m for m in miss if m[0] in want]
            if bad:
                print(f"--cores: no views for {bad}")
                return 1
    errs = S.validate(raw)
    if errs:
        print("plan invalid:\n  " + "\n  ".join(errs[:20]))
        return 1
    plan, leaves = extract(raw, a.parts.split(","), a.channel, a.name, cores=a.cores, core_taps=a.core_taps,
                           plan_dir=str(Path(a.plan).resolve().parent))
    added = plan.pop("core_taps_added", None)
    if added:
        for tn, lst in added.items():
            print(f"core taps {tn}: " + (", ".join(f"{n} ({ps:g} ps)" for n, ps in lst) or "none"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for t in plan["partition_types"].values():        # absolute: the kit generators resolve sources under --rtl-root
        t["sources"] = [str((out / "leaves.sv").resolve())]
    (out / "pair_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    (out / "leaves.sv").write_text(leaves)
    errs = S.validate(plan)
    print(f"{out / 'pair_plan.json'}: {len(plan['ports'])} ports, {len(plan['lanes'])} lanes, "
          f"die {plan['die']['outline_um']}, channels {len(plan['die']['channels'])}; schema "
          + ("PASS" if not errs else "FAIL\n  " + "\n  ".join(errs[:20])))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
