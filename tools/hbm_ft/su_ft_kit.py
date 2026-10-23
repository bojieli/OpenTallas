#!/usr/bin/env python3
"""FT-HBM-SU: in-place feedthrough variant of an HBM block kit module (no wrapper hierarchy).

Same method as tools/s81_dv/ft/frame_ft_kit.py (FT-S81): the kit module text is copied, renamed to the variant, the ft
ports are appended to its port list and the ft stations to its body, each insertion fenced by "// >>> FT-HBM ft" /
"// <<< FT-HBM ft" lines.  Removing the fenced lines and renaming the module back reproduces the kit file byte for
byte (`check`), so the block logic is provably unmodified and every name-bound contract of the base kit (children,
landings, lp.py record, place.tcl) still holds.

The ft stations are the die relay itself: per ft path k (ftspec.v1 "paths"), `stages` instances ft<k>_s<j> of
ot_hbm_rly #(.W(bits), .RS_RELAY(1)) (rtl/hbm_accel/die_glue/ot_hbm_rly.sv, the function of every hbfd_rly die relay:
r <= i on posedge ck, asynchronous clear), chained ft<k>_i -> s0 -> ... -> ft<k>_o, so the first and last register sit
at the in / out pins (pin-register rule) and the ones between are <= reach apart (FT-TOOL plan).  They run on their own
root ck_ft (the die clock of the lanes they carry) and reset from rs_ft through one ot_rst_relay (<= 32 loads a region),
so they never touch the block's own clocks or resets.

    su_ft_kit.py gen   --kit KIT.sv --kit-top TOP --ftspec SPEC.json --out OUT.sv
    su_ft_kit.py check --kit KIT.sv --kit-top TOP --variant-sv OUT.sv --variant NAME   (prints FT_KIT_CHECK PASS|FAIL)
"""
import argparse, hashlib, json, re, sys

BEGIN, END = "// >>> FT-HBM ft", "// <<< FT-HBM ft"
MAX_LOADS = 32


def module_span(text, name):
    m = re.search(rf"^module {re.escape(name)}\b", text, re.M)
    if not m:
        raise SystemExit(f"module {name} not found")
    e = re.compile(r"^endmodule\b", re.M).search(text, m.end())
    return m.start(), e.start()


def station_loads(w):         # ot_hbm_rly RS_RELAY=1: rs -> ot_rst_relay(REGIONS=G): 2 sync + G relay flops
    return 2 + (w + 255) // 256


def gen(a):
    kit = open(a.kit).read()
    spec = json.load(open(a.ftspec))
    var = spec["variant"]
    paths = sorted(spec["paths"], key=lambda p: p["path"])
    ports = [("input", 1, "ck_ft"), ("input", 1, "rs_ft")]
    for p in paths:
        ports += [("input", p["bits"], p["in"]), ("output", p["bits"], p["out"])]
    # reset regions: pack stations so each region output drives <= MAX_LOADS async-clear / sync pins
    regions, cur = [], []
    for p in paths:
        for j in range(p["stages"]):
            l = station_loads(p["bits"])
            if cur and sum(x[2] for x in cur) + l > MAX_LOADS:
                regions.append(cur); cur = []
            cur.append((p["path"], j, l))
    if cur:
        regions.append(cur)
    R = len(regions)
    reg_of = {(k, j): r for r, g in enumerate(regions) for (k, j, _) in g}
    body = [f"    // {len(paths)} ft paths, {sum(p['bits'] for p in paths)} bits, "
            f"{sum(p['stages'] for p in paths)} stations ({sum(p['bits'] * p['stages'] for p in paths)} flops), {R} reset regions",
            f"    wire [{R - 1}:0] ft_rn;"]
    per = MAX_LOADS - 2                       # regions one relay can drive (its rst_n_in: 2 sync + REGIONS tree flops)
    if R <= per:
        body.append(f"    ot_rst_relay #(.REGIONS({R}), .SYNC_STAGES(2), .TREE_STAGES(1)) u_ft_rst (.clk(ck_ft), .rst_n_in(rs_ft), .rst_n(ft_rn));")
    else:                                     # two levels: rs_ft -> u_ft_rst (one region per group) -> u_ft_rst_<m>
        G = (R + per - 1) // per
        if G > per:
            raise SystemExit(f"{R} reset regions need a third relay level")
        body += [f"    wire [{G - 1}:0] ft_rg;",
                 f"    ot_rst_relay #(.REGIONS({G}), .SYNC_STAGES(2), .TREE_STAGES(1)) u_ft_rst (.clk(ck_ft), .rst_n_in(rs_ft), .rst_n(ft_rg));"]
        for m in range(G):
            lo, hi = m * per, min(R, (m + 1) * per)
            body.append(f"    ot_rst_relay #(.REGIONS({hi - lo}), .SYNC_STAGES(2), .TREE_STAGES(1)) u_ft_rst_{m} "
                        f"(.clk(ck_ft), .rst_n_in(ft_rg[{m}]), .rst_n(ft_rn[{hi - 1}:{lo}]));")
    for p in paths:
        k, w, n = p["path"], p["bits"], p["stages"]
        body.append(f"    // ft{k}: {p['src']} -> {p['dst']}, {w} b, {n} regs over {p['len_um']} um "
                    f"(regs_um {p['regs_um']}), {p['rep_sites']} repeater sites")
        nets = [p["in"]] + [f"ft{k}_p{j}" for j in range(1, n)] + [p["out"]]
        for j in range(1, n):
            body.append(f"    wire [{w - 1}:0] ft{k}_p{j};")
        for j in range(n):
            body.append(f"    ot_hbm_rly #(.W({w}), .RS_RELAY(1)) ft{k}_s{j} (.ck(ck_ft), .rs(ft_rn[{reg_of[(k, j)]}]), "
                        f".i({nets[j]}), .o({nets[j + 1]}));")
    ks, ke = module_span(kit, a.kit_top)
    mod = kit[ks:ke]
    h = mod.index("\n);")
    decl = [f"    {d} wire {'[%d:0] ' % (w - 1) if w > 1 else ''}{n}" for d, w, n in ports]
    new_mod = (mod[:h] + ",\n" + BEGIN + " ports\n" + ",\n".join(decl) + "\n" + END + " ports"
               + mod[h:] + BEGIN + f" stations (tools/hbm_ft/su_ft_kit.py from {a.ftspec})\n"
               + "\n".join(body) + "\n" + END + " stations\n")
    new_mod = re.sub(rf"^module {re.escape(a.kit_top)}\b", f"module {var}", new_mod, count=1, flags=re.M)
    sha = hashlib.sha256(kit.encode()).hexdigest()
    out = (f"{BEGIN} header\n// GENERATED by tools/hbm_ft/su_ft_kit.py: {a.kit_top} of {a.kit} (sha256 {sha}) renamed "
           f"{var} + ft ports/stations from {a.ftspec}; block logic unmodified (su_ft_kit.py check).\n"
           f"{END} header\n" + kit[:ks] + new_mod + kit[ke:])
    open(a.out, "w").write(out)
    print(a.out, len(paths), "ft paths", R, "reset regions")


def strip_ft(text):
    out, skip = [], False
    for l in text.split("\n"):
        if l.startswith(BEGIN):
            skip = True
            continue
        if l.startswith(END):
            skip = False
            continue
        if not skip:
            out.append(l)
    return "\n".join(out)


def check(a):
    kit = open(a.kit).read()
    v = strip_ft(open(a.variant_sv).read())
    v = re.sub(rf"^module {re.escape(a.variant)}\b", f"module {a.kit_top}", v, count=1, flags=re.M)
    ks, _ = module_span(kit, a.kit_top)
    h = kit.index("\n);", ks)
    ok = v == kit[:h] + "," + kit[h:]
    print("FT_KIT_CHECK " + ("PASS block logic byte-identical to " if ok else "FAIL differs from ") + a.kit)
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("gen")
    for k in ("--kit", "--kit-top", "--ftspec", "--out"):
        g.add_argument(k, required=True)
    c = sp.add_parser("check")
    for k in ("--kit", "--kit-top", "--variant-sv", "--variant"):
        c.add_argument(k, required=True)
    a = ap.parse_args()
    gen(a) if a.cmd == "gen" else check(a)


if __name__ == "__main__":
    main()
