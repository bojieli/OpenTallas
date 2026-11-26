#!/usr/bin/env python3
"""Merged-GDS DRC gate (ABSTRACT-EXACT 11-25, COORD/Fable: signoff.py counts DRC only from 5_route_drc.rpt, which
checks the parent against the hard-core ABSTRACTS).  A parent routed over exact-abstract views (OBS = real metal, so the
parent may route over the core on M4/M5/M6) is checked here against the REAL core geometry:

  1. every hard core's signed routed DB (6_final.odb or .def) -> GDS (platform std-cell GDS), top cell = master name
  2. the routed parent DEF -> merged.gds (hard cores filled with their real GDS), parent_only.gds (cores empty) and
     macros_only.gds (only the cores), all in the same coordinates
  3. KLayout DRC with the platform deck (ASAP7: platforms/asap7/drc/asap7.lydrc, the ORFS `make drc` deck) on all three
  4. NEW = markers of merged minus markers of the two baselines (same category and bbox).  A NEW marker on or within
     --halo-um of a hard core is an abstract/real-geometry interaction the route DRC could not see.

  python3 -I merged_gds_drc.py run --parent-def P/6_final.def --design TOP --core MASTER=CORE.odb [...] \
      --lef VIEW.lef [...] [--allow-empty REGEX] --out DIR [--image openroad/orfs:asap7lock]
      -> DIR/verdict.json; exit 0 iff PASS (no NEW marker at a hard core, no cell without GDS outside --allow-empty)
  python3 -I merged_gds_drc.py verdict --out DIR      (re-judge an existing DIR)

Generated memory macros (fakeram-style, no GDS) are named by --allow-empty: they stay empty and any NEW marker over
them is reported UNCHECKED (not gating; their LEF is the only model).  Gate use: signoff.py runs this for every type
whose plan binds an exact-abstract view (abstract_obs.exact_view_bound) and refuses SIGNED unless verdict PASS.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent
PYA = HERE / "merged_gds_drc_pya.py"
ORFS = "/OpenROAD-flow-scripts/flow"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
PLAT = ORFS + "/platforms/asap7"
STD_LEFS = [PLAT + "/lef/asap7_tech_1x_201209.lef"] + [PLAT + "/lef/asap7sc7p5t_28_%s_1x_220121a.lef" % v
                                                         for v in ("R", "L", "SL")]
STD_GDS = [PLAT + "/gds/asap7sc7p5t_28_%s_220121a.gds" % v for v in ("R", "L", "SL")]
DECK = PLAT + "/drc/asap7.lydrc"
# BEOL deck (default): the platform deck cut to the layer sections an exact-abstract view can change.  The view keeps M1-M3 as
# one blanket OBS and its FEOL is the signed core's, so the parent can only add M4-M7 / V3-V6 shapes over a core; the full
# deck spends > 1 h on FEOL checks of the std cells per block (HEAD hd_host_e: line 154 of 561 after 56 min).
BEOL_SECTIONS = ("M3", "V3", "M4", "V4", "M5", "V5", "M6", "V6", "M7")
BEOL_AWK = ('{sub(/\\r$/, "")}\n'            # the deck has CRLF line ends
            '/^info\\("DRC section"\\)/ {print; drc=1; keep=0; next}\n'
            'drc && /^###/ {keep = ($2 ~ /^(%s)$/); if (keep) print; next}\n'
            '!drc || keep {print}\n'
            'END {print "</text>"; print "</klayout-macro>"}\n' % "|".join(BEOL_SECTIONS))
GATING_ZONE = "HARDCORE"


# P-DRC-DECK-BASELINE (S81-COL-EOL 11-26, FABLE-INDEP 15:12 review of 4390177b0284).  Every NEW marker in the HARDCORE zone gates, whatever its category (M4.AUX.3,
# M5.AUX.3, Vn.AUX.1, V3.M4.AUX.2 are 0 in the baselines and appear only where parent and core geometry merge: they can be the only trace of a parent-to-core short).
# The one explicit exclusion is V4.M5.AUX.2 OUTSIDE the hard-core zone (PARENT markers: 1,669,570 on the H10 R2 ECO merged run, 2 on parent_only; the count follows the
# layout structure, hierarchical window 2 vs flattened 39072 on identical shapes, so it is not trusted either way until the run mode is settled).  The gate never counted
# PARENT markers; the exclusion is reported, and while a category is excluded a passing run is PASS-PROVISIONAL, which signoff.gate_check reads as NOT RUN: no kit passes
# on this deck until it reads 0 on a signed clean core (FLEET-OPS-R4 staged core, calib/) and the zone behaviour is proven.
EXCLUDED_OUTSIDE_HARDCORE = ("V4.M5.AUX.2",)


def gating_counts(cmp):
    """-> (gating HARDCORE markers (all categories), {category: n} gating, {excluded category: n outside the hard-core zone})"""
    per = cmp.get("per_category")
    if not isinstance(per, dict):
        return cmp.get("new_hardcore", 0), {}, {}
    cats, excl = {}, {}
    for cat, z in per.items():
        name = cat.strip("'")
        n = (z or {}).get(GATING_ZONE, 0)
        if n:
            cats[name] = n
        if name in EXCLUDED_OUTSIDE_HARDCORE:
            out = sum(v for k, v in (z or {}).items() if k != GATING_ZONE)
            if out:
                excl[name] = out
    return sum(cats.values()), cats, excl


def judge(cmp, cells):
    """-> verdict dict from compare.json + parent_cells.json"""
    problems = []
    if cells.get("missing"):
        problems.append("cells without GDS (not --allow-empty): %s" % cells["missing"][:10])
    gate, cats, excl = gating_counts(cmp)
    if gate:
        problems.append("%d NEW DRC markers at hard cores (real GDS vs abstract)" % gate)
    verdict = "FAIL" if problems else ("PASS-PROVISIONAL" if excl else "PASS")
    return dict(verdict=verdict, problems=problems, provisional=bool(excl), excluded_outside_hardcore=excl,
                new_hardcore=gate, gating_categories=cats, new_parent=cmp.get("new_parent", 0),
                new_unchecked=cmp.get("new_unchecked", 0), merged_markers=cmp.get("merged_markers"),
                hard_cores=sorted(cells.get("filled", {})), empty_allowed=sorted({r["master"] for r in
                                                                                  cells.get("empty_allowed", [])}))


def needs_gate(lef_path):
    """True when a hard-core view lets the parent route over the core on a routing layer while its lower layers keep the
    blanket form: the abstract_exact / kvpc_exact_m45 splice signature (M1 one blanket rect, some of M4-M6 detailed and
    < 80 % covered).  Generated macros (no routed DB) never need it."""
    import abstract_exact as AE
    try:
        cov = AE.coverage(lef_path, ("M1", "M4", "M5", "M6"))
    except Exception:  # noqa: BLE001
        return False
    m1, m1n = cov["M1"]
    return m1 >= AE.BLANKET_OBS_PCT and m1n <= 4 and any(cov[L][1] > 4 and cov[L][0] < AE.BLANKET_OBS_PCT
                                                       for L in ("M4", "M5", "M6"))


def build_script(a, cores, P):
    """bash for the ORFS image.  P maps the roles out / tool / lefs / pdef / core<i> to directories (docker: mount points)"""
    q = shlex.quote
    O = P["out"]
    lefs = STD_LEFS + ["%s/%d_%s" % (P["lefs"], i, os.path.basename(l)) for i, l in enumerate(a.lef)]
    lines = ["set -e", "cd %s" % q(O), "K='klayout -b -r %s/merged_gds_drc_pya.py'" % P["tool"],
             "python3 %s/util/generate_klayout_tech.py --template %s/KLayout/asap7.lyt --output %s/k.lyt "
             "--lef-files %s" % (ORFS, PLAT, O, " ".join(lefs))]
    cmap = {}
    for i, (m, src) in enumerate(cores):
        d = P["core%d" % i]
        base = "%s/%s" % (d, os.path.basename(src))
        if src.endswith(".gds"):
            cmap[m] = base
            continue
        if src.endswith(".odb"):
            lines.append("printf 'read_db %s\\nwrite_def %s/core_%s.def\\n' > %s/w%d.tcl && %s -no_init -exit "
                         "%s/w%d.tcl > %s/w%d.log 2>&1" % (base, O, m, O, i, OPENROAD, O, i, O, i))
            cdef = "%s/core_%s.def" % (O, m)
        else:
            cdef = base
        lines.append("D=$(awk '/^DESIGN /{print $2; exit}' %s); $K -rd mode=core -rd in_def=%s -rd design_name=$D "
                     "-rd master=%s -rd tech_file=%s/k.lyt -rd gds_files=%s -rd out_file=%s/core_%s.gds "
                     "> %s/core_%s.log 2>&1" % (cdef, cdef, m, O, q(" ".join(STD_GDS)), O, m, O, m))
        cmap[m] = "%s/core_%s.gds" % (O, m)
    Path(a.out, "macro_map.json").write_text(json.dumps(cmap, indent=1))
    lines.append("$K -rd mode=parent -rd in_def=%s/%s -rd design_name=%s -rd tech_file=%s/k.lyt -rd gds_files=%s "
                 "-rd macro_map=%s/macro_map.json -rd allow_empty=%s -rd out_dir=%s > %s/parent.log 2>&1"
                 % (P["pdef"], os.path.basename(a.parent_def), q(a.design), O, q(" ".join(STD_GDS)), O,
                    q(a.allow_empty or ""), O, O))
    deck = DECK
    if getattr(a, "deck", "beol") == "beol":
        Path(a.out, "beol.awk").write_text(BEOL_AWK)
        lines.append("awk -f %s/beol.awk %s > %s/beol.lydrc" % (O, DECK, O))
        deck = "%s/beol.lydrc" % O
    for g in ("merged", "parent_only", "macros_only"):
        lines.append("( klayout -b -r %s -rd in_gds=%s/%s.gds -rd report_file=%s/%s.lyrdb > %s/drc_%s.log 2>&1"
                     " && echo 0 > %s/drc_%s.rc || echo 1 > %s/drc_%s.rc ) &" % (deck, O, g, O, g, O, g, O, g, O, g))
    lines += ["wait", "for g in merged parent_only macros_only; do [ \"$(cat %s/drc_$g.rc)\" = 0 ] || "
              "{ echo DRC_FAIL $g; exit 4; }; done" % O,
              "$K -rd mode=compare -rd merged=%s/merged.lyrdb -rd parent_only=%s/parent_only.lyrdb "
              "-rd macros_only=%s/macros_only.lyrdb -rd cells_json=%s/parent_cells.json -rd halo_um=%s "
              "-rd out_file=%s/compare.json > %s/compare.log 2>&1" % (O, O, O, O, a.halo_um, O, O),
              "echo OT_MGD_DONE"]
    return "\n".join(lines) + "\n"


def run(a):
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    a.out = str(out)
    cores = []
    for c in a.core:
        m, _, src = c.partition("=")
        if not m or not src:
            raise SystemExit("--core MASTER=PATH")
        cores.append((m, os.path.realpath(src)))
    lefdir = out / "lefs"
    lefdir.mkdir(exist_ok=True)
    for i, l in enumerate(a.lef):
        dst = lefdir / ("%d_%s" % (i, os.path.basename(l)))
        dst.write_bytes(Path(l).read_bytes())
    if a.local:                                      # already inside the ORFS image (kit post-route step)
        P = dict(out=str(out), tool=str(HERE), lefs=str(lefdir), pdef=os.path.dirname(os.path.realpath(a.parent_def)))
        P.update(("core%d" % i, os.path.dirname(src)) for i, (_, src) in enumerate(cores))
        (out / "run.sh").write_text(build_script(a, cores, P))
        cmd = ["bash", str(out / "run.sh")]
    else:
        P = dict(out="/out", tool="/tool", lefs="/lefs", pdef="/pdef")
        P.update(("core%d" % i, "/core%d" % i) for i in range(len(cores)))
        (out / "run.sh").write_text(build_script(a, cores, P))
        mounts = ["-v", "%s:/out" % out, "-v", "%s:/tool:ro" % HERE, "-v", "%s:/lefs:ro" % lefdir,
                  "-v", "%s:/pdef:ro" % os.path.dirname(os.path.realpath(a.parent_def))]
        for i, (_, src) in enumerate(cores):
            mounts += ["-v", "%s:/core%d:ro" % (os.path.dirname(src), i)]
        cmd = ["docker", "run", "--rm", "--memory", "%dg" % a.mem_gb, "--user", "%d:%d" % (os.getuid(), os.getgid()),
               *mounts, a.image, "bash", "/out/run.sh"]
    (out / "cmd.txt").write_text(" ".join(shlex.quote(x) for x in cmd) + "\n")
    with open(out / "run.log", "w") as fh:
        rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
    if rc or "OT_MGD_DONE" not in (out / "run.log").read_text():
        v = dict(verdict="ERROR", problems=["merged-GDS DRC run rc %d (see %s/run.log)" % (rc, out)])
        (out / "verdict.json").write_text(json.dumps(v, indent=1))
        print(json.dumps(v))
        return 2
    return verdict(a)


def verdict(a):
    out = Path(a.out)
    v = judge(json.loads((out / "compare.json").read_text()), json.loads((out / "parent_cells.json").read_text()))
    (out / "verdict.json").write_text(json.dumps(v, indent=1))
    print(json.dumps(v))
    return 0 if v["verdict"] == "PASS" else 1


def kit_plan(kit):
    """-> dict(required, gated views, cores [(master, gds)], lefs, allow_empty, parent_def, design) for a kit dir"""
    kit = Path(kit)
    lefs = sorted(str(p) for p in (kit / "macros").glob("*.lef")) if (kit / "macros").is_dir() else []
    gated = [l for l in lefs if needs_gate(l)]
    cores, empty = [], []
    for l in lefs:
        m = macro_name(l)
        g = Path(l).with_suffix(".gds")
        if g.is_file():
            cores.append((m, str(g)))
        else:
            empty.append(re.escape(m))
    design = None
    cfg = kit / "config.mk"
    if cfg.is_file():
        mm = re.search(r"^export\s+DESIGN_NAME\s*\??=\s*(\S+)", cfg.read_text(), re.M)
        design = mm.group(1) if mm else None
    defs = sorted(kit.glob("run/results/asap7/*/base/6_final.def"))
    return dict(required=bool(gated), gated=gated, cores=cores, lefs=lefs, allow_empty="|".join(empty) or "",
                parent_def=str(defs[-1]) if defs else None, design=design)


def macro_name(lef):
    with open(lef) as fh:
        for ln in fh:
            mm = re.match(r"MACRO\s+(\S+)", ln)
            if mm:
                return mm.group(1)
    return Path(lef).stem


def kit_run(a):
    """kit post-route step: NOT-REQUIRED (no exact-abstract view bound) or the gate on 6_final.def"""
    kp = kit_plan(a.kit)
    out = Path(a.out or Path(a.kit) / "merged_gds_drc")
    out.mkdir(parents=True, exist_ok=True)
    if not kp["required"]:
        (out / "verdict.json").write_text(json.dumps(dict(verdict="NOT-REQUIRED", **kp), indent=1))
        return 0
    miss = [Path(g).name for g in kp["gated"] if not Path(g).with_suffix(".gds").is_file()]
    if miss or not kp["parent_def"] or not kp["design"]:
        v = dict(verdict="ERROR", problems=["exact-abstract view without its core GDS: %s" % miss] if miss else
                 ["no 6_final.def / DESIGN_NAME in the kit"], **kp)
        (out / "verdict.json").write_text(json.dumps(v, indent=1))
        print(json.dumps(v)[:400])
        return 2
    ns = argparse.Namespace(parent_def=kp["parent_def"], design=kp["design"], core=["%s=%s" % c for c in kp["cores"]],
                            lef=kp["lefs"], allow_empty=kp["allow_empty"], halo_um=a.halo_um, out=str(out),
                            image=a.image, mem_gb=a.mem_gb, local=a.local, deck=a.deck)
    return run(ns)


def core_gds(a):
    """signed core DB -> <master>.gds (top cell = master; std cells from the platform GDS), published beside an exact-abstract
    view so kits can run the merged-GDS gate without the signed archive"""
    out = Path(a.out).resolve()
    work = out.parent / (out.name + ".work")
    work.mkdir(parents=True, exist_ok=True)
    src = os.path.realpath(a.db)
    lefs = STD_LEFS + ["/lefs/%s" % os.path.basename(l) for l in a.lef]
    lefdir = work / "lefs"
    lefdir.mkdir(exist_ok=True)
    for l in a.lef:
        (lefdir / os.path.basename(l)).write_bytes(Path(l).read_bytes())
    sh = ["set -e", "python3 %s/util/generate_klayout_tech.py --template %s/KLayout/asap7.lyt --output /w/k.lyt --lef-files %s"
          % (ORFS, PLAT, " ".join(lefs))]
    if src.endswith(".odb"):
        sh.append("printf 'read_db /src/%s\\nwrite_def /w/core.def\\n' > /w/w.tcl && %s -no_init -exit /w/w.tcl > /w/w.log 2>&1"
                  % (os.path.basename(src), OPENROAD))
        d = "/w/core.def"
    else:
        d = "/src/" + os.path.basename(src)
    sh.append("D=$(awk '/^DESIGN /{print $2; exit}' %s); klayout -b -r /tool/merged_gds_drc_pya.py -rd mode=core -rd in_def=%s "
              "-rd design_name=$D -rd master=%s -rd tech_file=/w/k.lyt -rd gds_files=%s -rd out_file=/w/core.gds > /w/core.log 2>&1"
              % (d, d, a.master, shlex.quote(" ".join(STD_GDS))))
    sh.append("echo OT_CORE_GDS_DONE")
    (work / "run.sh").write_text("\n".join(sh) + "\n")
    cmd = ["docker", "run", "--rm", "--memory", "%dg" % a.mem_gb, "--user", "%d:%d" % (os.getuid(), os.getgid()),
           "-v", "%s:/w" % work, "-v", "%s:/tool:ro" % HERE, "-v", "%s:/lefs:ro" % lefdir, "-v", "%s:/src:ro" % os.path.dirname(src),
           a.image, "bash", "/w/run.sh"]
    with open(work / "run.log", "w") as fh:
        rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
    if rc or "OT_CORE_GDS_DONE" not in (work / "run.log").read_text():
        print("CORE-GDS-FAIL %s rc %d (%s)" % (a.master, rc, work))
        return 2
    os.replace(work / "core.gds", out)
    meta = json.loads((work / "core.gds.json").read_text())
    meta.update(db=src, gds=str(out))
    out.with_suffix(".gds.json").write_text(json.dumps(meta, indent=1))
    print("CORE-GDS %s %s empty %s" % (a.master, out, meta.get("empty_cells")))
    return 0


def gate_check(kit):
    """signoff.py: None when the kit binds no exact-abstract view, else dict(verdict PASS/FAIL/NOT RUN, ...)"""
    kp = kit_plan(kit)
    if not kp["required"]:
        return None
    p = Path(kit) / "merged_gds_drc" / "verdict.json"
    try:
        v = json.loads(p.read_text())
    except (OSError, ValueError):
        return dict(verdict="NOT RUN", reason="exact-abstract views %s bound; no merged-GDS DRC verdict at %s"
                    % ([Path(g).name for g in kp["gated"]], p))
    return dict(verdict=v.get("verdict") if v.get("verdict") in ("PASS", "FAIL") else "NOT RUN",
                problems=v.get("problems"), new_hardcore=v.get("new_hardcore"), new_parent=v.get("new_parent"),
                new_unchecked=v.get("new_unchecked"), gated=[Path(g).name for g in kp["gated"]], source=str(p))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--parent-def", required=True)
    r.add_argument("--design", required=True)
    r.add_argument("--core", action="append", default=[], help="MASTER=signed 6_final.odb or .def (repeat)")
    r.add_argument("--lef", action="append", default=[], help="every non-std-cell LEF the parent DEF uses (repeat)")
    r.add_argument("--allow-empty", default="", help="regex of generated macros without GDS (UNCHECKED, not gating)")
    r.add_argument("--halo-um", type=float, default=1.0)
    r.add_argument("--deck", choices=("beol", "full"), default="beol")
    r.add_argument("--out", required=True)
    r.add_argument("--image", default="openroad/orfs:asap7lock")
    r.add_argument("--mem-gb", type=int, default=64)
    r.add_argument("--local", action="store_true", help="run klayout/openroad here (inside the ORFS image), no docker")
    c = sub.add_parser("core-gds")
    c.add_argument("--db", required=True, help="signed 6_final.odb or .def")
    c.add_argument("--master", required=True)
    c.add_argument("--lef", action="append", default=[], help="LEFs of macros inside the core (SRAM ...)")
    c.add_argument("--out", required=True)
    c.add_argument("--image", default="openroad/orfs:asap7lock")
    c.add_argument("--mem-gb", type=int, default=32)
    k = sub.add_parser("kit")
    k.add_argument("--kit", required=True)
    k.add_argument("--out")
    k.add_argument("--halo-um", type=float, default=1.0)
    k.add_argument("--deck", choices=("beol", "full"), default="beol")
    k.add_argument("--image", default="openroad/orfs:asap7lock")
    k.add_argument("--mem-gb", type=int, default=64)
    k.add_argument("--local", action="store_true")
    v = sub.add_parser("verdict")
    v.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return {"run": run, "kit": kit_run, "core-gds": core_gds}.get(a.cmd, verdict)(a)


if __name__ == "__main__":
    sys.exit(main())
