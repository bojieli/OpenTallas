#!/usr/bin/env python3
"""DIE-QC-58B (COORD 10-31 22:5x ruling (3) variant B): derive an A0 ICG=1 (single tile-root gate, DIE-QC-16 form)
kit from a GEOM-reviewed ICG=2 (B-hop) A0 kit.  Generated, never hand-edited: every change is listed in DERIVE.json.

Changes (only these):
  * VERILOG_TOP_PARAMS ICG 2 -> ICG 1 (config.mk + rtl_lint.ys chparam); RTL is byte-identical to origin/main.
  * graph homes: the 100 g_icg.g_hop.* rows (37 hop ICGs + relayed enable registers h[*]) are removed (absent in the
    ICG=1 netlist); the one root gate g_icg.g_root.u_icg takes the home of the former ck-entry gate u_hop_ck/u_icg
    (the gate that already drove the body clock ck_g).  All other homes (body/face registers, relay, dr, go_h) kept.
  * IO frame = the DECLARED A0 frame (COORD DIE-QC-18): config OT_VCLK_TT/FF, constraint.sdc / vclk_ff.sdc
    set_clock_latency -source, sdc_lint.json insertion_ps / insertion_ff_ps.
  * CTS_ARGS = DIE-QC-57d V3 (-balance_levels -wire_unit 25 -distance_between_buffers 100) on the kit's base args.
  * optional --lec-hints: the main nb_t[6:0] loaded=0 hints (Codex QC NL parent proof); without them both tiles' LEC
    stops at 7 nb compare points (synthesis drops nb_t[6:0], which are always 0).
       derive_icg1_kit.py --prune KIT nk|nl NETLIST   (after synth: drop homes of cells synthesis removed)
usage: derive_icg1_kit.py SRC DST --tile nk|nl --tt PS --ff PS --suffix SUF [--lec-hints HINTS.json]
"""
import argparse, json, os, re, shutil, hashlib, sys

V3 = "-balance_levels -wire_unit 25 -distance_between_buffers 100"
SKIP = {"run", "__pycache__", "lec", "FAIL_PREFLOOR", "image.txt"}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def sub1(text, pat, rep, what, count=1):
    new, n = re.subn(pat, rep, text, flags=re.M)
    if n != count:
        sys.exit(f"derive: {what}: expected {count} match(es) of {pat!r}, got {n}")
    return new


def prune(kit, tile, netlist):
    """Post-synth step: drop graph homes whose cell is absent from the kit's own synth netlist (graph_homes.tcl
    errors on any missing name).  Every dropped name is listed in DERIVE.json; nothing is added or moved."""
    names = set(re.findall(r"\\(\S+)", open(netlist).read())) | set(re.findall(r"^\s*\S+\s+([A-Za-z_][\w.$]*)\s*\(", open(netlist).read(), re.M))
    gh = os.path.join(kit, f"{tile}_graph_homes.tsv"); rows = open(gh).read().splitlines()
    # the derive-added homes (root gate, B2 en_q) are always kept: an ICG=1 / ICG_EREG netlist has them by construction
    # and --prune may be fed an earlier (pre-B2) synth netlist of the same tile
    added = {"g_icg.g_root.u_icg", "g_icg.g_root.g_er.en_q$_DFF_PN1_"}
    keep, drop = [], []
    for r in rows:
        n = r.split("\t")[0].replace("\\[", "[").replace("\\]", "]")
        (keep if n in names or n in added else drop).append(r)
    open(gh, "w").write("\n".join(keep) + "\n")
    dj = os.path.join(kit, "DERIVE.json"); d = json.load(open(dj))
    d.setdefault("changes", []).append(f"{os.path.basename(gh)}: post-synth prune -{len(drop)} homes absent from {os.path.basename(netlist)}")
    d["pruned_homes"] = [r.split("\t")[0] for r in drop]
    d["sha16"][os.path.basename(gh)] = sha(gh)
    json.dump(d, open(dj, "w"), indent=1)
    print(f"prune: kept {len(keep)} dropped {len(drop)}: {[r.split(chr(9))[0] for r in drop][:10]}")


EPI_OLD = "  if {$w >= -100.0 && $n <= 2000} { return }\n"
EPI_NEW = EPI_OLD + (
    "  # DIE-QC-58B kit-local (COORD 21:2x (3)(a)): with ws >= -100 the endpoint count is INFO; sign-off FF hold >= 0 stays the gate\n"
    "  if {$w >= -100.0 && [info exists ::env(OT_HOLD_EP_INFO)] && $::env(OT_HOLD_EP_INFO) eq \"1\"} {\n"
    "    puts [format \"OT_HOLD_EP_INFO stage=%s: FF hold ws %.2f ps >= -100, %d failing endpoints > 2000 = INFO (COORD 21:2x (3)(a)) -> repair proceeds\" [ot_hold_stage] $w $n]\n"
    "    return\n  }\n")


def hold_ep_info(kit):
    """B2 (DIE-QC-58 ruling, COORD 21:2x (3)(a)): the structural hold endpoint cap becomes INFO when ws >= -100 ps
    (kit-local, opt-in OT_HOLD_EP_INFO = 1); ws >= -100 and sign-off FF hold >= 0 stay gates."""
    p = os.path.join(kit, "orfs_hold_mm.tcl"); s = open(p).read()
    if "OT_HOLD_EP_INFO" not in s:
        if s.count(EPI_OLD) != 1:
            sys.exit("derive: structural hold gate line not found in orfs_hold_mm.tcl")
        open(p, "w").write(s.replace(EPI_OLD, EPI_NEW))
    c = os.path.join(kit, "config.mk"); t = open(c).read()
    if "OT_HOLD_EP_INFO" not in t:
        open(c, "a").write("# DIE-QC-58B: structural hold endpoint cap = INFO when ws >= -100 (COORD 21:2x (3)(a), DIE-QC-58 ruling)\n"
                           "export OT_HOLD_EP_INFO = 1\n")
    dj = os.path.join(kit, "DERIVE.json"); d = json.load(open(dj))
    d.setdefault("changes", []).append("orfs_hold_mm.tcl + config.mk: OT_HOLD_EP_INFO = 1 (endpoint cap INFO when ws >= -100)")
    d["sha16"]["orfs_hold_mm.tcl"] = sha(p); d["sha16"]["config.mk"] = sha(c)
    json.dump(d, open(dj, "w"), indent=1)
    print("hold_ep_info: applied")


def grt50(kit):
    """GEOM-99 PASS-COND (A0 root gate): GRT >= 50 congestion iterations with the clock nets included (the kit GRT
    routes 4_cts incl. clock); 0 overflow is checked on 5_1_grt.log before detail route."""
    c = os.path.join(kit, "config.mk"); t = open(c).read()
    if "GLOBAL_ROUTE_ARGS" not in t:
        open(c, "a").write("# DIE-QC-58B: GEOM-99 PASS-COND, GRT >= 50 iterations (ORFS default 30)\n"
                           "export GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose -congestion_iterations 50\n")
    dj = os.path.join(kit, "DERIVE.json"); d = json.load(open(dj))
    d.setdefault("changes", []).append("config.mk: GLOBAL_ROUTE_ARGS -congestion_iterations 50 (GEOM-99 PASS-COND)")
    d["sha16"]["config.mk"] = sha(c); json.dump(d, open(dj, "w"), indent=1)
    print("grt50: applied")


def face_lift(kit):
    """DIE-QC-59 NK variant: face-branch clock latency lift to the declared FF frame (face_lift.tcl next to this script):
    after CTS, before the structural hold gate, each port-face leaf clock group below OT_VCLK_FF gets a buffer chain on
    its face sinks only, grown and re-measured per round in the synchronized FF scene (kit-local, OT_FACE_LIFT = 1)."""
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_lift.tcl")
    dst = os.path.join(kit, "face_lift.tcl"); shutil.copyfile(src, dst)
    p = os.path.join(kit, "orfs_hold_mm.tcl"); s = open(p).read()
    if "face_lift.tcl" not in s:
        open(p, "a").write("source /work/face_lift.tcl\n")
    c = os.path.join(kit, "config.mk"); t = open(c).read()
    if "OT_FACE_LIFT" not in t:
        open(c, "a").write("# DIE-QC-58B: face-branch clock latency lift to the declared FF frame (DIE-QC-59 NK variant)\n"
                           "export OT_FACE_LIFT = 1\n")
    dj = os.path.join(kit, "DERIVE.json"); d = json.load(open(dj))
    d.setdefault("changes", []).append("face_lift.tcl + orfs_hold_mm.tcl source + config.mk OT_FACE_LIFT = 1")
    for f in ("face_lift.tcl", "orfs_hold_mm.tcl", "config.mk"):
        d["sha16"][f] = sha(os.path.join(kit, f))
    json.dump(d, open(dj, "w"), indent=1)
    print("face_lift: applied")


def dpl_retry(kit):
    """NL B2 e1 DPL-0033 after a met CTS hold repair: legalization retry on a failing check_placement (dpl_retry.tcl next
    to this script; sourced from the kit orfs_hold_mm.tcl, so it covers every stage that loads the helper)."""
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dpl_retry.tcl")
    dst = os.path.join(kit, "dpl_retry.tcl"); shutil.copyfile(src, dst)
    p = os.path.join(kit, "orfs_hold_mm.tcl"); s = open(p).read()
    if "dpl_retry.tcl" not in s:
        open(p, "a").write("source /work/dpl_retry.tcl\n")
    dj = os.path.join(kit, "DERIVE.json"); d = json.load(open(dj))
    d.setdefault("changes", []).append("dpl_retry.tcl + orfs_hold_mm.tcl source (check_placement legalization retry)")
    for f in ("dpl_retry.tcl", "orfs_hold_mm.tcl"):
        d["sha16"][f] = sha(os.path.join(kit, f))
    json.dump(d, open(dj, "w"), indent=1)
    print("dpl_retry: applied")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--prune":
        return prune(sys.argv[2], sys.argv[3], sys.argv[4])
    if len(sys.argv) > 1 and sys.argv[1] == "--dpl-retry":
        return dpl_retry(sys.argv[2])
    if len(sys.argv) > 1 and sys.argv[1] == "--face-lift":
        return face_lift(sys.argv[2])
    if len(sys.argv) > 1 and sys.argv[1] == "--grt50":
        return grt50(sys.argv[2])
    if len(sys.argv) > 1 and sys.argv[1] == "--hold-ep-info":
        return hold_ep_info(sys.argv[2])
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--tile", choices=["nk", "nl"], required=True)
    ap.add_argument("--tt", type=float, required=True); ap.add_argument("--ff", type=float, required=True)
    ap.add_argument("--suffix", required=True)
    ap.add_argument("--lec-hints", help="untrusted LEC register hints copied to KIT/lec_hints.json (proved by lec.py "
                    "induction, never a waiver); A0: results/codex_qc_a0_2340/parent_zero_proof/hints.json (nb_t[6:0])")
    ap.add_argument("--ereg", metavar="RTL_A0C", help="B2: ICG_EREG 1 (registered root-gate enable beside the gate); copies "
                    "this qfd_tile_<t>_a0c.sv (the branch RTL with the opt-in ICG_EREG param) into KIT/rtl and homes en_q "
                    "next to the root gate")
    ap.add_argument("--no-dpl-retry", action="store_true", help="omit the default-on check_placement legalization retry")
    ap.add_argument("--cts-extra", default="", help="B2: extra clock_tree_synthesis args appended after V3")
    a = ap.parse_args()
    if os.path.exists(a.dst):
        sys.exit(f"derive: {a.dst} exists")
    shutil.copytree(a.src, a.dst, ignore=lambda d, names: [n for n in names if n in SKIP or (d == a.src and n.endswith(".log"))])
    log = []
    cfg = os.path.join(a.dst, "config.mk"); t = open(cfg).read()
    old_nick = re.search(r"^export DESIGN_NICKNAME = (\S+)$", t, re.M).group(1)
    nick = f"kq_qfd_tile_{a.tile}_a0c_{a.suffix}"
    t = sub1(t, r"^export DESIGN_NICKNAME = \S+$", f"export DESIGN_NICKNAME = {nick}", "nickname")
    t = sub1(t, r"^(export VERILOG_TOP_PARAMS = .*\bICG) 2\b", r"\1 1", "ICG param")
    t = sub1(t, r"^export OT_VCLK_TT = \S+$", f"export OT_VCLK_TT = {a.tt}", "OT_VCLK_TT")
    t = sub1(t, r"^export OT_VCLK_FF = \S+$", f"export OT_VCLK_FF = {a.ff}", "OT_VCLK_FF")
    t = re.sub(r"(TT setup vclk) [0-9.]+( / scene BC \(mode ff\) FF hold vclk) [0-9.]+", rf"\g<1> {a.tt}\g<2> {a.ff}", t)
    base = re.findall(r"^(?:override )?export CTS_ARGS = (.*)$", t, re.M)[-1]
    t += (f"\n# DIE-QC-58B (COORD 10-31 ruling 3 variant B): ICG=1 single tile-root gate (DIE-QC-16 form), declared A0 frame\n"
          f"# {a.tt}/{a.ff}, CTS = DIE-QC-57d V3 tree knobs. GENERATED by derive_icg1_kit.py from {old_nick}.\n"
          f"override export CTS_ARGS = {base} {V3}{(' ' + a.cts_extra) if a.cts_extra else ''}\n")
    if a.ereg:
        t = sub1(t, r"^(export VERILOG_TOP_PARAMS = .*\bICG 1)\b", r"\1 ICG_EREG 1", "ICG_EREG param")
    open(cfg, "w").write(t)
    log.append(f"config.mk: nickname, ICG 2->1, OT_VCLK_TT/FF, CTS_ARGS V3{(' + ' + a.cts_extra) if a.cts_extra else ''}"
               f"{', ICG_EREG 1' if a.ereg else ''}")
    for f, v in (("constraint.sdc", a.tt), ("vclk_ff.sdc", a.ff)):
        p = os.path.join(a.dst, f); s = open(p).read()
        s = sub1(s, r"^set_clock_latency -source \S+ \[get_clocks vclk\]$", f"set_clock_latency -source {v} [get_clocks vclk]", f)
        open(p, "w").write(s); log.append(f"{f}: vclk source latency {v}")
    p = os.path.join(a.dst, "sdc_lint.json"); j = json.load(open(p))
    j["insertion_ps"] = a.tt; j["insertion_ff_ps"] = a.ff
    json.dump(j, open(p, "w"), indent=1); log.append(f"sdc_lint.json: insertion {a.tt}/{a.ff}")
    p = os.path.join(a.dst, "clock_binding.json"); j = json.load(open(p))
    if j["insertion_ps"]["tt"] != a.tt or j["insertion_ps"]["ff"] != a.ff:
        j["insertion_ps"] = {"tt": a.tt, "ff": a.ff}
        b = (f"DECLARED A0 frame {a.tt} TT / {a.ff} FF (COORD DIE-QC-18 measured A0 frame; DIE-QC-57d: the old 250/202.5 "
             f"wrapper frame was stale for this tile); DIE-QC-58B derive_icg1_kit.py")
        j["basis"] = {"tt": b, "ff": b}
        json.dump(j, open(p, "w"), indent=1); log.append(f"clock_binding.json: insertion {a.tt}/{a.ff}")
    p = os.path.join(a.dst, "rtl_lint.ys"); s = open(p).read()
    s = sub1(s, r"(chparam .*-set ICG) 2\b", r"\1 1", "rtl_lint chparam")
    if a.ereg:
        s = sub1(s, r"(chparam .*-set ICG 1)\b", r"\1 -set ICG_EREG 1", "rtl_lint chparam ICG_EREG")
    open(p, "w").write(s)
    log.append("rtl_lint.ys: chparam ICG 1" + (" ICG_EREG 1" if a.ereg else ""))
    gh = os.path.join(a.dst, f"{a.tile}_graph_homes.tsv"); rows = open(gh).read().splitlines()
    hop = [r for r in rows if r.startswith("g_icg.g_hop.")]
    ck = [r for r in hop if r.split("\t")[0] == "g_icg.g_hop.u_hop_ck/u_icg"]
    if len(ck) != 1:
        sys.exit("derive: u_hop_ck/u_icg home not found")
    f = ck[0].split("\t"); f[0] = "g_icg.g_root.u_icg"
    keep = [r for r in rows if not r.startswith("g_icg.g_hop.")] + ["\t".join(f)]
    if a.ereg:   # en_q 2 um from the gate (same row): enable wire ~2 um, en_q CLK on the ungated root next to the gate CLK
        e = list(f); e[0] = "g_icg.g_root.g_er.en_q$_DFF_PN1_"; e[1] = f"{float(f[1]) + 2.0:.3f}"; keep.append("\t".join(e))
    open(gh, "w").write("\n".join(keep) + "\n")
    log.append(f"{os.path.basename(gh)}: -{len(hop)} g_hop rows, +g_icg.g_root.u_icg at ({f[1]},{f[2]})"
               + (" +g_er.en_q 2 um east" if a.ereg else ""))
    if a.ereg:
        d = os.path.join(a.dst, "rtl", f"qfd_tile_{a.tile}_a0c.sv")
        if "ICG_EREG" not in open(a.ereg).read():
            sys.exit("derive: --ereg RTL has no ICG_EREG param")
        shutil.copyfile(a.ereg, d); log.append(f"rtl/qfd_tile_{a.tile}_a0c.sv: ICG_EREG RTL from {a.ereg} (sha16 {sha(a.ereg)})")
    if a.lec_hints:
        shutil.copyfile(a.lec_hints, os.path.join(a.dst, "lec_hints.json"))
        log.append(f"lec_hints.json: copied from {a.lec_hints} (sha16 {sha(a.lec_hints)})")
    json.dump({"tool": "derive_icg1_kit.py", "lane": "DIE-QC-58B", "src": os.path.abspath(a.src), "src_nickname": old_nick,
               "dst_nickname": nick, "tile": a.tile, "frame_tt_ps": a.tt, "frame_ff_ps": a.ff, "cts_args_added": (V3 + " " + a.cts_extra).strip(),
               "ereg": bool(a.ereg),
               "changes": log, "sha16": {n: sha(os.path.join(a.dst, n)) for n in
                                          ("config.mk", "constraint.sdc", "vclk_ff.sdc", "sdc_lint.json", "rtl_lint.ys",
                                           f"{a.tile}_graph_homes.tsv", f"rtl/qfd_tile_{a.tile}_a0c.sv")}},
              open(os.path.join(a.dst, "DERIVE.json"), "w"), indent=1)
    print("\n".join(log))
    # class fix, default-on (DIE-QC-59 11-01): CTS legalization retry after a met hold repair (NL e1 DPL-0033)
    if not a.no_dpl_retry:
        dpl_retry(a.dst)


if __name__ == "__main__":
    main()
