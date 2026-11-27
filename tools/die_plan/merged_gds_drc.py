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
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from xml.etree import ElementTree
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


# P-DRC-DECK-BASELINE (S81-COL-EOL 11-26, COORD ruling after FABLE-INDEP reviews of 4390177b0284 / 6e153c0fc444).  The deck gates on FLATTENED WINDOWS only: every hard-core
# instance bbox + WINDOW_MARGIN_UM of merged.gds, parent_only.gds and macros_only.gds is clipped, flattened and run through the unchanged deck.  The hierarchical (deep mode)
# full-chip run under-reports (a V6.S spacing rule reads 0 hierarchical and 1,440 flattened on identical shapes), so it never gates: --hier keeps it as a report only.
# A merged marker is NEW unless a marker of the SAME CATEGORY sits at the same LOCATION in the parent_only or macros_only window (all four bbox corners within one GDS database unit; never a
# count).  Nothing is excluded by category: V4.M5.AUX.2 and the other AUX rules gate like every other category; a baseline-equal PG via cancels by location.
# A parent shape overlapping core metal merges into one polygon and gives no deck marker, so a geometric SHORT check runs on the same windows (mode=shorts): on every metal and
# via layer, parent_only shapes AND macros_only shapes overlap = NEW SHORT.<layer>, minus the overlap inside the core's own pin-purpose shapes (datatype 251: the legal landing of a
# parent route on a pin).  It sees geometry only, not nets: a parent pad on a pin of the wrong net is a connectivity question for LVS, not for this gate.
FLAT_MODE = "flat-windows-location-v1"
WINDOW_MARGIN_UM = 5.0
# F6 (FABLE-INDEP re-review 11-27): the gate is only valid on the calibrated BEOL deck.  A deck whose awk cut stops matching section headers has zero rules, every report is empty and the
# run would PASS; so the generated beol.lydrc is pinned by sha256 (calibration deck d8b963c69872, H10 R2 windows #16/#26/#32 + su_smr seeded fixture) and a mismatch aborts the run.
PINNED_BEOL_DECK_SHA256 = "d8b963c69872510159604162dd0c0585d97ea58e51940b2cabffed20fdd50ea9"
DEFAULT_HALO_UM = 1.0          # F5: the only halo the gate accepts (verdicts record it; gate_check compares)
MAX_HALO_UM = WINDOW_MARGIN_UM  # no marker exists outside the window, so a larger halo is meaningless and a negative one empties the HARDCORE zone


def tool_sha256():
    return hashlib.sha256(Path(__file__).read_bytes() + PYA.read_bytes()).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_run_args(a, masters):
    """F5: refuse parameters that can turn the gate into a vacuous PASS."""
    halo = float(a.halo_um)
    if not (0.0 <= halo <= MAX_HALO_UM):
        raise SystemExit("--halo-um must be within 0..%g (got %g)" % (MAX_HALO_UM, halo))
    if a.allow_empty:
        try:
            rx = re.compile(a.allow_empty)
        except re.error as exc:
            raise SystemExit("--allow-empty is not a valid regex: %s" % exc)
        hit = sorted(m for m in masters if rx.match(m))
        if hit:
            raise SystemExit("--allow-empty matches hard-core master(s) %s: a core with GDS can never be allowed empty" % hit)
    if getattr(a, "deck", "beol") not in ("beol", "full"):
        raise SystemExit("--deck must be beol or full")
_NUM = re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?")


def parse_lyrdb(path, dbu):
    """Yield each report marker's category and full bounding box in GDS grid units."""
    items = None
    events = iter(ElementTree.iterparse(path, events=("start", "end")))
    _, root = next(events)
    if root.tag != "report-database":
        raise ValueError(f"Expected a KLayout report database in {path}")
    for event, element in events:
        if event == "start" and element.tag == "items":
            items = element
        if event != "end" or element.tag != "item":
            continue
        category = element.findtext("category", "").strip("'")
        if not category:
            raise ValueError(f"Marker without category in {path}")
        found_geometry = False
        for value in element.findall("./values/value"):
            kind, sep, coordinates = (value.text or "").partition(":")
            if not sep or kind not in {"box", "polygon", "edge", "edge-pair", "path"}:
                continue
            points = [round(float(number) / dbu) for number in _NUM.findall(coordinates)]
            if len(points) < 2 or len(points) % 2:
                raise ValueError(f"Invalid {kind} marker in {path}: {value.text}")
            xs, ys = points[::2], points[1::2]
            found_geometry = True
            yield category, (min(xs), min(ys), max(xs), max(ys))
        if not found_geometry or items is None:
            raise ValueError(f"Marker {category} without geometry inside items in {path}")
        items.remove(element)
    if items is None:
        raise ValueError(f"Missing report items in {path}")


def subtract(markers, baselines):
    """Yield markers without a same-category baseline match within one DBU on every edge."""
    grid = {}
    for category, box in baselines:
        grid.setdefault((category, box[0] // 2, box[1] // 2), set()).add(box)
    for category, box in markers:
        gx, gy = box[0] // 2, box[1] // 2
        candidates = (candidate for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                      for candidate in grid.get((category, gx + dx, gy + dy), ()))
        if not any(all(abs(a - b) <= 1 for a, b in zip(box, candidate)) for candidate in candidates):
            yield category, box


def zone_of(b, cells, halo):
    for rec in cells.get("hard_core_insts", []):
        x0, y0, x1, y1 = rec["bbox"]
        if b[0] < x1 + halo and b[2] > x0 - halo and b[1] < y1 + halo and b[3] > y0 - halo:
            return "HARDCORE", rec["master"]
    for rec in cells.get("empty_allowed", []):
        x0, y0, x1, y1 = rec["bbox"]
        if b[0] < x1 and b[2] > x0 and b[1] < y1 and b[3] > y0:
            return "UNCHECKED", rec["master"]
    return "PARENT", None


def window_compare(out, cells, halo=1.0):
    """Compare matching flat windows, retaining every unique new marker's location."""
    win_dir = Path(out) / "win"
    kinds = ("merged", "parent_only", "macros_only")
    windows = [json.loads((win_dir / f"{kind}_windows.json").read_text()) for kind in kinds]
    dbu = cells["dbu"]
    if dbu <= 0:
        raise ValueError("A positive GDS DBU is required")
    expected = []
    for index, core in enumerate(cells["hard_core_insts"]):
        x0, y0, x1, y1 = core["bbox"]
        box = [x0 - WINDOW_MARGIN_UM, y0 - WINDOW_MARGIN_UM,
               x1 + WINDOW_MARGIN_UM, y1 + WINDOW_MARGIN_UM]
        expected.append((index, core["master"], tuple(round(value / dbu) for value in box)))
    if not expected or any([
        (window["i"], window["master"], tuple(round(value / dbu) for value in window["bbox"]))
        for window in group
    ] != expected for group in windows):
        raise ValueError("Merged and baseline windows must match every hard-core instance in order")
    counts = dict.fromkeys(kinds, 0)
    zones = dict.fromkeys(("HARDCORE", "UNCHECKED", "PARENT"), 0)
    seen, sample, per_category = set(), [], {}
    locations = Path(out) / "new_markers.jsonl"
    pending = locations.with_suffix(".tmp")

    with pending.open("w") as stream:
        for window in windows[0]:
            index = window["i"]
            reports = [list(parse_lyrdb(win_dir / f"{kind}_{index}.lyrdb", dbu)) for kind in kinds]
            for kind, report in zip(kinds, reports):
                counts[kind] += len(report)
            shorts = json.loads((win_dir / f"shorts_{index}.json").read_text())
            markers = list(subtract(reports[0], reports[1] + reports[2]))
            markers.extend((f"SHORT.{layer}", tuple(round(v / dbu) for v in box))
                           for layer, boxes in shorts.items() for box in boxes)
            for category, box in markers:
                key = category, box
                if key in seen:
                    continue
                seen.add(key)
                bbox = [round(value * dbu, 10) for value in box]
                zone, master = zone_of(bbox, cells, halo)
                marker = dict(category=category, bbox=bbox, bbox_dbu=box, count=1, zone=zone,
                              master=master, window=index)
                stream.write(json.dumps(marker, separators=(",", ":")) + "\n")
                if len(sample) < 2000:
                    sample.append(marker)
                category_counts = per_category.setdefault(category, {})
                category_counts[zone] = category_counts.get(zone, 0) + 1
                zones[zone] += 1
    pending.replace(locations)
    return dict(mode=FLAT_MODE, windows=len(windows[0]), dbu=dbu, tolerance_dbu=1,
                margin_um=WINDOW_MARGIN_UM, halo_um=halo, merged_markers=counts["merged"],
                parent_only_markers=counts["parent_only"], macros_only_markers=counts["macros_only"],
                new_markers=len(seen), new_hardcore=zones["HARDCORE"],
                new_unchecked=zones["UNCHECKED"], new_parent=zones["PARENT"],
                per_category=per_category, new=sample, locations=locations.name)


def gating_counts(cmp):
    """-> (gating HARDCORE markers, {category: n}); nothing is excluded"""
    per = cmp.get("per_category")
    if not isinstance(per, dict):
        return cmp.get("new_hardcore", 0), {}
    cats = {c.strip("'"): (z or {}).get(GATING_ZONE, 0) for c, z in per.items() if (z or {}).get(GATING_ZONE, 0)}
    return sum(cats.values()), cats


def judge(cmp, cells, hier=None):
    """-> verdict dict from compare.json (flat windows) + parent_cells.json; hier = the report-only hierarchical compare, if it was run"""
    problems = []
    if cells.get("missing"):
        problems.append("cells without GDS (not --allow-empty): %s" % cells["missing"][:10])
    gate, cats = gating_counts(cmp)
    if gate:
        problems.append("%d NEW DRC markers at hard cores (real GDS vs abstract; flat windows, by category+location)" % gate)
    v = dict(verdict="FAIL" if problems else "PASS", problems=problems, mode=cmp.get("mode", "legacy"), new_hardcore=gate, gating_categories=cats,
             new_parent=cmp.get("new_parent", 0), new_unchecked=cmp.get("new_unchecked", 0), merged_markers=cmp.get("merged_markers"),
             hard_cores=sorted(cells.get("filled", {})),
             empty_allowed=sorted({r["master"] for r in cells.get("empty_allowed", [])}))
    if cmp.get("mode") != FLAT_MODE:
        v["verdict"] = "FAIL" if problems else "NOT-FLAT"      # a hierarchical-only compare never passes
    if hier:
        v["hierarchical_report_only"] = dict(new_hardcore=hier.get("new_hardcore"), new_parent=hier.get("new_parent"))
    return v


def needs_gate(lef_path):
    """True when a hard-core view lets the parent route over the core on a routing layer while its lower layers keep the
    blanket form: the abstract_exact / kvpc_exact_m45 splice signature (M1 one blanket rect, some of M4-M6 detailed and
    < 80 % covered).  Generated macros (no routed DB) never need it."""
    import abstract_exact as AE
    try:
        cov = AE.coverage(lef_path, ("M1", "M4", "M5", "M6"))
    except Exception:  # noqa: BLE001
        return True      # F5: an unreadable view must not turn the gate into NOT-REQUIRED
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
        lines.append(deck_pin_line(O))
        deck = "%s/beol.lydrc" % O
    lines += window_lines(O, P["tool"], deck)
    if getattr(a, "hier", False):          # report only: the deep-mode full-chip run under-reports and never gates
        for g in ("merged", "parent_only", "macros_only"):
            lines.append("( klayout -b -r %s -rd in_gds=%s/%s.gds -rd report_file=%s/%s.lyrdb > %s/drc_%s.log 2>&1"
                         " && echo 0 > %s/drc_%s.rc || echo 1 > %s/drc_%s.rc ) &" % (deck, O, g, O, g, O, g, O, g, O, g))
        lines += ["wait", "for g in merged parent_only macros_only; do [ \"$(cat %s/drc_$g.rc)\" = 0 ] || "
                  "{ echo DRC_FAIL $g; exit 4; }; done" % O,
                  "$K -rd mode=compare -rd merged=%s/merged.lyrdb -rd parent_only=%s/parent_only.lyrdb "
                  "-rd macros_only=%s/macros_only.lyrdb -rd cells_json=%s/parent_cells.json -rd halo_um=%s "
                  "-rd out_file=%s/compare.json > %s/compare.log 2>&1" % (O, O, O, O, a.halo_um, O, O)]
    lines.append("echo OT_MGD_DONE")
    return "\n".join(lines) + "\n"


def deck_pin_line(O):
    """bash: abort (rc 5) unless the generated BEOL deck is the pinned calibration deck"""
    return ("echo '%s  %s/beol.lydrc' | sha256sum -c - > %s/deck_pin.log 2>&1 || { echo DECK_SHA_MISMATCH; exit 5; }"
            % (PINNED_BEOL_DECK_SHA256, O, O))


def window_lines(O, tool, deck, jobs=6):
    """bash lines: clip + flatten the three GDS to the hard-core windows, then the deck on every window (xargs -P)"""
    L = ["mkdir -p %s/win" % O]
    for g in ("merged", "parent_only", "macros_only"):
        L.append("klayout -b -r %s/merged_gds_drc_pya.py -rd mode=window -rd in_gds=%s/%s.gds -rd cells_json=%s/parent_cells.json -rd margin_um=%g "
                 "-rd out_prefix=%s/win/%s > %s/win/%s.clip.log 2>&1" % (tool, O, g, O, WINDOW_MARGIN_UM, O, g, O, g))
    L.append("ls %s/win/merged_*.gds %s/win/parent_only_*.gds %s/win/macros_only_*.gds > %s/win/jobs.txt" % (O, O, O, O))
    L.append("cat %s/win/jobs.txt | xargs -P %d -I{} bash -c 'f={}; klayout -b -r %s -rd in_gds=$f -rd report_file=${f%%.gds}.lyrdb > ${f%%.gds}.log 2>&1'"
             % (O, jobs, deck))
    L.append("klayout -b -r %s/merged_gds_drc_pya.py -rd mode=shorts -rd win_dir=%s/win > %s/win/shorts.log 2>&1" % (tool, O, O))
    L.append("echo OT_MGD_WIN_DONE")
    return L


def run(a):
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    a.out = str(out)
    for stale in ("verdict.json", "run_meta.json", "compare_windows.json", "new_markers.jsonl", "beol.lydrc", "deck_pin.log", "run_complete"):
        (out / stale).unlink(missing_ok=True)          # F4: a crashed run can never leave a previous verdict behind
    cores = []
    for c in a.core:
        m, _, src = c.partition("=")
        if not m or not src:
            raise SystemExit("--core MASTER=PATH")
        cores.append((m, os.path.realpath(src)))
    validate_run_args(a, [m for m, _ in cores])
    meta = dict(parent_def=os.path.realpath(a.parent_def), parent_def_sha256=sha256_file(a.parent_def), allow_empty=a.allow_empty or "",
                halo_um=float(a.halo_um), deck=getattr(a, "deck", "beol"), cores=sorted(m for m, _ in cores),
                tool_sha256=tool_sha256(), core_sha256={m: sha256_file(src) for m, src in cores})
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1))
    try:
        return _run(a, out, cores)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        v = dict(verdict="ERROR", problems=["merged-GDS DRC run crashed: %r" % (exc,)])
        (out / "verdict.json").write_text(json.dumps(v, indent=1))
        print(json.dumps(v))
        return 2


def _run(a, out, cores):
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
    (out / "run_complete").write_text("OT_MGD_DONE\n")        # N3: _verdict judges only a run that finished
    return verdict(a)


def verdict(a):
    out = Path(a.out)
    try:
        return _verdict(a, out)
    except Exception as exc:  # noqa: BLE001   F4: any crash is ERROR, never a surviving old verdict
        v = dict(verdict="ERROR", problems=["verdict crashed: %r" % (exc,)])
        (out / "verdict.json").write_text(json.dumps(v, indent=1))
        print(json.dumps(v))
        return 2


def _bind(v, out):
    """F4/F6: bind the verdict to the inputs it was computed from (parent DEF sha, halo, allow-empty, deck sha); gate_check refuses a verdict whose binding is absent or stale"""
    meta_path = out / "run_meta.json"
    if meta_path.is_file():
        v.update(json.loads(meta_path.read_text()))
    deck = out / "beol.lydrc"
    v["deck_sha256"] = sha256_file(deck) if deck.is_file() else None
    return v


def _verdict(a, out):
    (out / "verdict.json").unlink(missing_ok=True)
    if (out / "run_meta.json").is_file() and not (out / "run_complete").is_file():
        raise ValueError("run did not complete (no run_complete sentinel): window evidence may be stale")
    cells = json.loads((out / "parent_cells.json").read_text())
    hier = json.loads((out / "compare.json").read_text()) if (out / "compare.json").is_file() else None
    if (out / "win" / "merged_windows.json").is_file():
        try:
            cmp = window_compare(out, cells, getattr(a, "halo_um", 1.0))
        except (OSError, ValueError, KeyError, ElementTree.ParseError) as exc:
            v = dict(verdict="ERROR", problems=[f"Incomplete flat-window evidence: {exc}"])
        else:
            (out / "compare_windows.json").write_text(json.dumps(cmp, indent=1))
            v = judge(cmp, cells, hier)
    else:
        v = judge(hier or {}, cells)
    _bind(v, out)
    if v["verdict"] == "PASS" and not (out / "run_meta.json").is_file():
        v["verdict"] = "NOT-BOUND"        # N4: a re-judged legacy dir has no parent-DEF/core/deck binding: evidence only, never a PASS
        v["problems"] = list(v.get("problems") or []) + ["no run_meta.json: verdict is not bound to a parent DEF / core GDS"]
    if v["verdict"] == "PASS" and v.get("deck_sha256") != PINNED_BEOL_DECK_SHA256:
        v["verdict"] = "FAIL"
        v["problems"] = list(v.get("problems") or []) + ["BEOL deck is not the pinned calibration deck (sha256 %s)" % v.get("deck_sha256")]
    (out / "verdict.json").write_text(json.dumps(v, indent=1))
    print(json.dumps(v))
    return 0 if v["verdict"] == "PASS" else 1


def selftest(a):
    """Run the signed-core control and cross-boundary M4 overlap / V6 spacing seeds."""
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    core = os.path.realpath(a.core_gds)
    if a.local:
        P = dict(out=str(out), tool=str(HERE), core=os.path.dirname(core))
    else:
        P = dict(out="/out", tool="/tool", core="/core")
    deck_dir = out / "deck"
    deck_dir.mkdir(exist_ok=True)
    (deck_dir / "beol.awk").write_text(BEOL_AWK)
    O = P["out"]
    lines = ["set -e", "cd %s" % O,
             "klayout -b -r %s/merged_gds_drc_pya.py -rd mode=selftest -rd core_gds=%s/%s -rd out_dir=%s > %s/selftest.log 2>&1"
             % (P["tool"], P["core"], os.path.basename(core), O, O),
             "awk -f %s/deck/beol.awk %s > %s/deck/beol.lydrc" % (O, DECK, O),
             deck_pin_line("%s/deck" % O)]
    for v in ("clean", "seeded"):
        lines += window_lines("%s/%s" % (O, v), P["tool"], "%s/deck/beol.lydrc" % O)
    lines.append("echo OT_MGD_SELFTEST_DONE")
    (out / "run.sh").write_text("\n".join(lines) + "\n")
    if a.local:
        cmd = ["bash", str(out / "run.sh")]
    else:
        cmd = ["docker", "run", "--rm", "--memory", "%dg" % a.mem_gb, "--user", "%d:%d" % (os.getuid(), os.getgid()), "-v", "%s:/out" % out,
               "-v", "%s:/tool:ro" % HERE, "-v", "%s:/core:ro" % os.path.dirname(core), a.image, "bash", "/out/run.sh"]
    with open(out / "run.log", "w") as fh:
        rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
    if rc or "OT_MGD_SELFTEST_DONE" not in (out / "run.log").read_text():
        print(json.dumps(dict(verdict="ERROR", problems=["selftest run rc %d (see %s/run.log)" % (rc, out)])))
        return 2
    res = {}
    for v in ("clean", "seeded"):
        cells = json.loads((out / v / "parent_cells.json").read_text())
        cmp = window_compare(out / v, cells, 1.0)
        res[v] = dict(new_hardcore=cmp["new_hardcore"], per_category=cmp["per_category"], merged=cmp["merged_markers"],
                      parent_only=cmp["parent_only_markers"], macros_only=cmp["macros_only_markers"])
    seeded_dir = out / "seeded"
    targets = json.loads((seeded_dir / "seed_targets.json").read_text())
    if set(targets) != {"SHORT.M4", "V6.S.1-2-3", "SHORT.M8"}:
        raise ValueError("Calibration requires every cross-boundary seed target (M4 overlap + zero-gap abutment, V6.S, M8 overlap)")
    targets = {c: (v if isinstance(v[0], list) else [v]) for c, v in targets.items()}     # old fixtures: one box per category
    detected = {"%s#%d" % (c, i): False for c, boxes in targets.items() for i in range(len(boxes))}
    with (seeded_dir / "new_markers.jsonl").open() as markers:
        for line in markers:
            marker = json.loads(line)
            category = marker["category"]
            if marker["zone"] != GATING_ZONE or category not in targets:
                continue
            a, b, c, d = marker["bbox_dbu"]
            for i, (x0, y0, x1, y1) in enumerate(targets[category]):
                if a <= x1 + 1 and c >= x0 - 1 and b <= y1 + 1 and d >= y0 - 1:
                    detected["%s#%d" % (category, i)] = True
    ok = res["clean"]["new_hardcore"] == 0 and all(detected.values())
    res["seeded"]["detected_at_seed"] = detected
    res["verdict"] = "PASS" if ok else "FAIL"
    (out / "selftest.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res))
    return 0 if ok else 1


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
                            lef=kp["lefs"], allow_empty=kp["allow_empty"], halo_um=a.halo_um, out=str(out), hier=getattr(a, "hier", False),
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


def _binding_ok(v, kp):
    """F4/F5/F6: a PASS counts only for THIS parent DEF, the pinned deck, the fixed halo and the kit-derived allow-empty regex"""
    try:
        return (kp.get("parent_def") is not None and v.get("parent_def_sha256") == sha256_file(kp["parent_def"])
                and v.get("deck_sha256") == PINNED_BEOL_DECK_SHA256 and v.get("deck") == "beol"
                and v.get("halo_um") == DEFAULT_HALO_UM and v.get("allow_empty") == (kp.get("allow_empty") or "")
                and v.get("tool_sha256") == tool_sha256()                                   # N2: tool and core GDS content bound too
                and v.get("core_sha256") == {m: sha256_file(g) for m, g in kp.get("cores", [])})
    except OSError:
        return False


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
    verdict = v.get("verdict")
    if verdict != "FAIL" and (verdict != "PASS" or v.get("mode") != FLAT_MODE or not _binding_ok(v, kp)):
        verdict = "NOT RUN"
    return dict(verdict=verdict,
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
    r.add_argument("--hier", action="store_true", help="also run the hierarchical full-chip deck (report only, never gates)")
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
    k.add_argument("--hier", action="store_true")
    t = sub.add_parser("selftest")
    t.add_argument("--core-gds", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--image", default="openroad/orfs:asap7lock")
    t.add_argument("--mem-gb", type=int, default=32)
    t.add_argument("--local", action="store_true")
    v = sub.add_parser("verdict")
    v.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return {"run": run, "kit": kit_run, "core-gds": core_gds, "selftest": selftest}.get(a.cmd, verdict)(a)


if __name__ == "__main__":
    sys.exit(main())
