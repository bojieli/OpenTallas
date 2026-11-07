"""DQ85-SUL0 11-06 class rule (su_l0 GRT-0116): per-lane replicas of a broadcast bin register feeding a macro stack,
sited at the west mouth of each lane's channel.

usage: python3 -I sul0_apply.py KIT [--mutant]      (KIT = generated kit dir: rtl/<T>_bound.sv, macro_place.tcl,
                                                      macros/*.lef, istations.tcl; run before the flow, on a fresh kit)
Writes: rtl/<T>_bound.sv (replicas), sul0_bound_pre.sv.txt (original), sul0_replicas.json, sul0_sites.tcl and one
`source /work/sul0_sites.tcl` line in istations.tcl (before `close $is_fh`).  No-op (exit 0, "SUL0 none") when no
bin qualifies.

Cause (measured, slw_su_l0__cl76fb247e kw21 attempt_3): u_bin_x_su_c_i (766b) / u_bin_x_su_c_p1_i (765b) are read by
all four lane macros (600/600/571/504 and 160/160/189/256 bits).  Lanes 2 and 3 have their c_i pins on the SOUTH
edge at the same x (die x 310-470), so the RSMT of each broadcast bit joins the lane2 pin to the lane3 pin straight
over lane2, where only M7 is free (M1-M6 OBS): 568 nets cross lane2; a GRT run of ONLY those 568 nets is still
congested.  Rule:
 1. qualifying bin: `ot_dp_st #(.W(W)) u_bin_<B> (... .d(<D>[W-1:0]), .ea(<D>[W]), .q(<B>_q), .eq(<B>_eq))` whose
    <B>_q is read only inside port maps of instances placed by macro_place.tcl, by >= 2 of them;
 2. one replica u_bin_<B>_l<k> per reading macro, W_k = bits that macro reads, same clk/rst/D bits/epoch:
    data_cycles 0, each lane pin sees the identical value in the identical cycle (slice proof: sul0_eqproof.py);
 3. replica flops FIRM (face_flops.tcl ff_put_near) at x = macro x0 - 3.6 um: pins on the macro WEST edge -> at the
    pin's y; pins on the SOUTH edge -> column block over the macro's own south channel (gap below it), 0.27-um rows,
    1.2-um columns westward.  The D net of every bit then branches only inside the west logic strip and each Q is
    a 2-pin net east along its own channel; no net joins two lanes over a macro.
"""
import json, re, sys
from pathlib import Path

ROW, COL, MOUTH = 0.27, 1.2, 3.6


def replicate(t, macros, mutant=False):
    """-> (new text, map {B: {lK: {inst, lane, width, bits}}}).  macros: instance names (u_laneN) placed as macros."""
    lines = t.split("\n")
    inst_re = re.compile(r"^\s*(\w+) (\w+) \(")
    bin_re = re.compile(r"^(\s*)ot_dp_st #\(\.W\((\d+)\)\) u_bin_(\w+) \(\.clk\((\w+)\), \.rst_n\((\w+)\), "
                        r"\.d\((\w+)\[(\d+):0\]\), \.ea\((\w+)\[(\d+)\]\), \.q\((\w+)\), \.eq\((\w+)\)\);\s*$")
    mline = {}
    for i, l in enumerate(lines):
        m = inst_re.match(l)
        if m and m.group(2) in macros:
            mline[m.group(2)] = i
    out_map = {}
    for bi, l in list(enumerate(lines)):
        m = bin_re.match(l)
        if not m:
            continue
        ind, W, B, clk, rst, dn, dhi, ean, eab, q, eq = m.groups()
        W, dhi, eab = int(W), int(dhi), int(eab)
        if not (dn == ean and dhi == W - 1 and eab == W):
            continue
        users = [i for i, x in enumerate(lines) if re.search(r"\b%s\b" % q, x) and i != bi]
        decl = [i for i in users if re.match(r"\s*wire\s+\[\d+:0\]\s+%s;\s*$" % q, lines[i])]
        if len(decl) != 1 or [i for i in users if i not in decl and i not in mline.values()]:
            continue
        readers = [n for n, i in sorted(mline.items()) if re.search(r"\b%s\[" % q, lines[i])]
        if len(readers) < 2:
            continue
        new, out_map[B] = [], {}
        for k, inst in enumerate(readers):
            i = mline[inst]
            bits = sorted({int(b) for b in re.findall(r"\b%s\[(\d+)\]" % q, lines[i])})
            assert all(0 <= b < W for b in bits), (B, inst)
            j_of = {b: j for j, b in enumerate(bits)}
            tag = re.sub(r"^u_", "", inst).replace("lane", "l")       # u_lane3 -> l3
            rq = f"{q}_{tag}"
            lines[i] = re.sub(r"\b%s\[(\d+)\]" % q, lambda mm: f"{rq}[{j_of[int(mm.group(1))]}]", lines[i])
            dbits = list(bits)
            if mutant and inst == readers[-1]:
                dbits[0], dbits[1] = dbits[1], dbits[0]
            d = "{" + ", ".join(f"{dn}[{b}]" for b in reversed(dbits)) + "}"
            new += [f"{ind}wire [{len(bits)-1}:0] {rq};", f"{ind}wire {eq}_{tag};",
                    f"{ind}ot_dp_st #(.W({len(bits)})) u_bin_{B}_{tag} (.clk({clk}), .rst_n({rst}), .d({d}), "
                    f".ea({dn}[{W}]), .q({rq}), .eq({eq}_{tag}));  // DQ85-SUL0 per-lane replica of u_bin_{B}"]
            out_map[B][tag] = {"inst": f"u_bin_{B}_{tag}", "lane": inst, "width": len(bits), "bits": bits, "q": rq}
        new.append(f"{ind}assign {eq} = {eq}_{re.sub(r'^u_', '', readers[0]).replace('lane', 'l')};"
                   "  // DQ85-SUL0: epoch flop of the first replica")
        lines[bi] = "\n".join(new)
        lines[decl[0]] = f"    // DQ85-SUL0: {q} replaced by the per-lane replicas {q}_l<k>"
    return "\n".join(lines), out_map


def lef_pins(f):
    t = f.read_text()
    pins = {}
    for m in re.finditer(r"^  PIN (\S+)\n(.*?)^  END \1", t, re.M | re.S):
        r = re.search(r"RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)", m.group(2))
        if r:
            a, b, c, d = map(float, r.groups())
            pins[m.group(1)] = ((a + c) / 2, (b + d) / 2)
    s = re.search(r"SIZE ([\d.]+) BY ([\d.]+)", t)
    return pins, float(s.group(1)), float(s.group(2))


def sites(K, t, rmap, org, masters, core_y0=4.32):
    out = ["# GENERATED by sul0_apply.py (DQ85-SUL0 11-06): per-lane bin replicas FIRM at the west mouth of their lane channel.",
           "# Sourced at the end of istations.tcl (inside face_flops.tcl, PRE_GLOBAL_PLACE): uses ff_put_near / ff_blk / ff_dbu.",
           "set sul0_sites [dict create]"]
    stats, lines = {}, t.split("\n")
    sizes = {}
    for inst in org:
        sizes[inst] = lef_pins(K / "macros" / f"{masters[inst]}.lef")
    for inst, (ox, oy) in sorted(org.items(), key=lambda a: a[1][1]):
        reps = {B: v[tag] for B, v in rmap.items() for tag in v if v[tag]["lane"] == inst}
        if not reps:
            continue
        pins, W, H = sizes[inst]
        below = max([p[1] + sizes[i][2] for i, p in org.items() if p[1] < oy and p[0] < ox + W and ox < p[0] + sizes[i][1]]
                    + [core_y0])
        line = next(l for l in lines if re.match(r"^\s*\w+ %s \(" % inst, l))
        west, south = [], []
        for port, body in re.findall(r"\.(\w+)\((\{.*?\}|[^(){}]*)\)", line):
            items = [x.strip() for x in body.strip("{}").split(",")]
            n = len(items)
            for p, it in enumerate(items):
                for B, r in reps.items():
                    m = re.match(r"%s\[(\d+)\]$" % re.escape(r["q"]), it)
                    if not m:
                        continue
                    pin = f"{port}[{n - 1 - p}]" if n > 1 or f"{port}[0]" in pins else port
                    px, py = pins[pin]
                    name = f"u_bound.{r['inst']}/q[{m.group(1)}]"
                    (west if px < 1.0 else south).append((name, px, py))
        xm = ox - MOUTH
        for name, px, py in west:
            out.append(f"dict set sul0_sites {{{name}}} {{{xm:.3f} {oy + py:.3f}}}")
        y0, y1 = below + 1.5, oy - 1.5
        nrow = max(1, int((y1 - y0) / ROW))
        south.sort(key=lambda e: -e[1])
        for i, (name, px, py) in enumerate(south):
            c, r = divmod(i, nrow)
            out.append(f"dict set sul0_sites {{{name}}} {{{xm - COL * c:.3f} {y1 - ROW * r:.3f}}}")
        stats[inst] = {"west": len(west), "south": len(south), "channel": [round(y0, 2), round(y1, 2)],
                       "x_mouth": round(xm, 3), "cols": -(-len(south) // nrow) if south else 0}
    out += [
        "set sul0_n 0; set sul0_miss 0",
        "foreach i [$ff_blk getInsts] {",
        "  set nm [string map {\\\\ {}} [$i getName]]",
        "  if {![regexp {^(u_bound\\.u_bin_\\w+_l[0-9]+/q\\[[0-9]+\\])} $nm -> key]} continue",
        "  if {![string match \"*DFF*\" [[$i getMaster] getName]] || ![dict exists $sul0_sites $key]} continue",
        "  lassign [dict get $sul0_sites $key] sx sy",
        "  set got [ff_put_near $i [expr {round($sx * $ff_dbu)}] [expr {round($sy * $ff_dbu)}]]",
        "  if {$got eq \"\"} { incr sul0_miss; continue }",
        "  puts $is_fh \"[$i getName]\\tsul0_replica\\t[expr {[lindex $got 0] / double($ff_dbu)}]\\t[expr {[lindex $got 1] / double($ff_dbu)}]\\t-\"",
        "  incr sul0_n",
        "}",
        "puts \"OT_SUL0_REPLICAS placed $sul0_n of [dict size $sul0_sites] lane replica flops at their channel mouths (miss $sul0_miss)\"",
        "if {$sul0_n != [dict size $sul0_sites]} { error \"OT_SUL0_REPLICAS: $sul0_n of [dict size $sul0_sites] replica flops sited\" }",
    ]
    return "\n".join(out) + "\n", stats


def main(argv):
    K = Path(argv[1]).resolve()
    mutant = "--mutant" in argv
    mp = (K / "macro_place.tcl").read_text()
    org = {m.group(1): (float(m.group(2)), float(m.group(3)))
           for m in re.finditer(r"u_bound\.(\w+)\} -location \{([\d.]+) ([\d.]+)\} -orientation R0", mp)}
    bfs = list((K / "rtl").glob("*_bound.sv"))
    assert len(bfs) == 1, bfs
    bf = bfs[0]
    t0 = bf.read_text()
    if "DQ85-SUL0" in t0:
        raise SystemExit("sul0_apply: kit already carries the SUL0 replicas (run on a fresh kit)")
    masters = {}
    for inst in org:
        m = re.search(r"^\s*(\w+) %s \(" % inst, t0, re.M)
        assert m, inst
        masters[inst] = m.group(1)
    t1, rmap = replicate(t0, set(org), mutant)
    if not rmap:
        print("SUL0 none: no broadcast bin read only by >= 2 placed macros")
        return 0
    tcl, stats = sites(K, t1, rmap, org, masters)
    ist = (K / "istations.tcl").read_text()
    a = "\nclose $is_fh\n"
    assert ist.count(a) == 1 and "sul0_sites" not in ist
    (K / "sul0_bound_pre.sv.txt").write_text(t0)
    bf.write_text(t1)
    (K / "sul0_replicas.json").write_text(json.dumps(rmap, indent=1))
    (K / "sul0_sites.tcl").write_text(tcl)
    (K / "istations.tcl").write_text(ist.replace(a, "\n# DQ85-SUL0 11-06: per-lane bin replicas at their channel mouths\n"
                                                  "source /work/sul0_sites.tcl" + a))
    for B, v in rmap.items():
        print(f"REPLICA u_bin_{B} -> " + ", ".join(f"{k}:{r['width']}" for k, r in v.items()))
    print("SITES " + json.dumps(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
