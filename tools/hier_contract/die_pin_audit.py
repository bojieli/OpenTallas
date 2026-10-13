#!/usr/bin/env python3
"""Die pin-readiness audit (owner 2026-10-13: will covered or badly placed pins still break the die route?).

For every master a die instantiates that has a PUBLISHED LEF (a view directory on the given git ref):
  child_lint --strict-pockets (blocked face pins, pockets, strap / cap, PG) and the slot fit of the view against its
  contract slot (view_slot_fit: outline, pin faces, pin layers, layer cap, insertion), and one table row:
    instances | top layer used inside | pins by face / layer | pins blocked from above (count, %) | pins under their own
    stub OBS | open pockets (layer, count) | outline / layer / pin mismatches | class

Masters: every non-die slot cell of the contract, plus (--case-census) the masters a die case placed (relays, stations,
memory macros).  Views: --views-from (a pinreg_audit JSON: its tiles[].view binding is reused), else a directory on the
ref holding <master>.lef (or one *.lef / *.lef.gz with MACRO <master>) and <master>_tt.lib; ref_tile views first, then
closed / assembled views, then routes (pinreg_audit.view_rank).  LEFs are read from git (`git show REF:path`) into
--cache: the audit never depends on what a sparse worktree has checked out.

Class per master (one row may carry several findings, all listed; the class is the costliest action it needs, in the
order FIX BY PIN RE-PLAN > FIX BY VIEW > FIX AT DIE > ACCEPT: a re-route re-exports the view anyway):
  FIX BY VIEW          the abstract is wrong, the route is not: a pin's own stub written as OBS (abstract_pin_stub.py
                       moves it into the PORT) or open pockets on a top layer the DIE routes on (>= M6; pocket fill)
  FIX BY PIN RE-PLAN   the routed tile covers its own face pins on the layer above (no via access: DRT-0073 class), or
                       its pins sit on another face / layer than the slot: re-route with reroute_reason
  FIX AT DIE           the view is sound but the contract / generator does not describe it: outline, pin names
                       (aggregated vs split ports), clock entry; a slot change, a relay or a lane move; or the die binds
                       a worse view than one that is published (every published view of a master is audited: other_views)
  ACCEPT               nothing that breaks a die route (legacy M6 / M7 inside a hardened cluster, pockets on a layer the
                       die does not route on over tiles, hard-IP abstracts)

    die_pin_audit.py masters --die NAME --contract C.json [--case-census J.json] [--views-from P.json] [--ref origin/main]
                     --out DIR [--cache DIR]
writes DIR/<die>_masters.json and DIR/<die>_masters.md.  Exit 0 (an audit, not a gate).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import child_lint as CL  # noqa: E402
import slot_fit as SF  # noqa: E402
import view_slot_fit as VSF  # noqa: E402

SCHEMA = "opentallas.die_pin_audit.v1"
HARD_RE = r"asap7_memory|pdie_macros|missing_phy|hbm3e|_phy(/|$)"
DIE_ROUTE_MIN_METAL = 6      # over a tile capped at M5 the die routes on M6 and above
OUTLINE_TOL_UM = 0.05
CLASSES = ("FIX BY VIEW", "FIX BY PIN RE-PLAN", "FIX AT DIE", "ACCEPT")
RANK = ("FIX BY PIN RE-PLAN", "FIX BY VIEW", "FIX AT DIE", "ACCEPT")


def git(*a, binary=False):
    r = subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=not binary)
    return r.stdout if r.returncode == 0 else (b"" if binary else "")


def view_rank(d):
    if "/ref_tile/" in d and "/views/" in d:
        return 0
    if "/closed/" in d or "s81_die_views/views" in d or "/assembled/" in d:
        return 1
    if "qwen_die_masters/views" in d or "hbm_accel_die_views" in d:
        return 2
    return 3 if d.startswith("physical/") and "/routes/" not in d else 4


class Store:
    """published view files on a git ref"""
    def __init__(self, ref, cache):
        self.ref, self.cache = ref, Path(cache)
        self.dirs = collections.defaultdict(set)
        for f in git("ls-tree", "-r", "--name-only", ref, "--", "physical", "results/rtl").split("\n"):
            if f.endswith((".lef", ".lef.gz", "_tt.lib", "_tt.lib.gz")):
                self.dirs[os.path.dirname(f)].add(os.path.basename(f))

    def by_name(self, cell):
        c = [d for d, n in self.dirs.items() if f"{cell}.lef" in n and (f"{cell}_tt.lib" in n or f"{cell}_tt.lib.gz" in n)]
        return sorted(c, key=lambda d: (view_rank(d), d))

    def text(self, path):
        raw = git("show", f"{self.ref}:{path}", binary=True)
        if path.endswith(".gz") and raw:
            raw = gzip.decompress(raw)
        return raw.decode(errors="replace")

    def materialise(self, view, cell):
        """-> (lef path in the cache, macro name) of the view's LEF for `cell`, or (None, why)"""
        names = self.dirs.get(view) or set()
        lefs = [n for n in sorted(names) if n.endswith((".lef", ".lef.gz"))]
        pick = next((n for n in lefs if n in (f"{cell}.lef", f"{cell}.lef.gz")), None)
        text = None
        if pick is None:
            for n in lefs:
                t = self.text(f"{view}/{n}")
                if re.search(r"(?m)^\s*MACRO\s+" + re.escape(cell) + r"\s*$", t) or len(lefs) == 1:
                    pick, text = n, t
                    break
        if pick is None:
            return None, f"no LEF with MACRO {cell} in {view}"
        text = text if text is not None else self.text(f"{view}/{pick}")
        macros = re.findall(r"(?m)^\s*MACRO\s+(\S+)\s*$", text)
        if not macros:
            return None, f"{view}/{pick} holds no MACRO"
        macro = cell if cell in macros else macros[0]
        out = self.cache / view.replace("/", "__")
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{macro}.lef").write_text(text)
        for n in names:
            if n.startswith(f"{macro}_tt.lib"):
                (out / f"{macro}_tt.lib").write_text(self.text(f"{view}/{n}"))
        return out / f"{macro}.lef", macro


def pin_table(m):
    """{"E/M4": bits, ..., "interior/M6": bits}: signal pins by face and layer"""
    t = collections.Counter()
    for n, p in m["pins"].items():
        if CL.is_pg(n, p) or not p["rects"]:
            continue
        on = [(CL.face_of(r, m["W"], m["H"]), r[0]) for r in p["rects"]]
        f, lay = next(((f, lay) for f, lay in on if f), ("interior", on[0][1]))
        t[f"{f}/{lay}"] += 1
    return dict(sorted(t.items()))


def categorise(mismatches):
    cat = collections.OrderedDict()
    for b in mismatches:
        k = ("outline" if b.startswith("outline") else
             "layer" if "routing cap" in b else
             "pin_layer" if "pins may land on" in b or "slot pin layer" in b else
             "face" if "off their slot face" in b or b.startswith("clock ") else
             "names" if "slot pins not in" in b or "ports the slot does not have" in b else
             "insertion" if "insertion" in b else
             "cell" if b.startswith("slot cell") else "other")
        cat.setdefault(k, []).append(b)
    return cat


def classify(r):
    """(class, [reasons]) of a master record"""
    why = []
    if r.get("hard_ip"):
        return "ACCEPT", ["hard-IP abstract (memory / PHY macro): not judged by the routed-tile lint; pins are the macro's own"]
    fa, pk, cat = r["face"], r["pockets"], r["mismatch"]
    cls = None
    if "cell" in cat and "outline" in cat:
        # a same-family view under another macro name and outline: the slot's own master has no view yet
        defects = [f"{fa['blocked_above']} face pins blocked above" if fa["blocked_above"] else "",
                   f"{fa['blocked_same']} pins under own-stub OBS" if fa["blocked_same"] else "",
                   f"{pk['count']} open {pk['layer']} pockets" if pk.get("count") and not pk.get("marker") else "",
                   f"top layer {r['top_layer']}" if (CL.metal(r["top_layer"]) or 0) > 5 else ""]
        return "FIX BY PIN RE-PLAN", [
            f"NOT THE SLOT'S MASTER: the only published view is {r['macro']} {r['outline'][0]:g} x {r['outline'][1]:g} "
            f"(slot {r['slot_outline'][0]:g} x {r['slot_outline'][1]:g}); the slot master is a new route that must fit the slot "
            f"(slot_fit + pin_align at submit)", "family view defects the new route must not repeat: "
            + (", ".join(d for d in defects if d) or "none")]

    def put(c, w):
        nonlocal cls
        why.append(f"{c}: {w}")
        if cls is None or RANK.index(c) < RANK.index(cls):
            cls = c
    if fa["blocked_same"]:
        put("FIX BY VIEW", f"{fa['blocked_same']} face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)")
    if pk.get("count") and not pk.get("marker") and (CL.metal(pk.get("layer")) or 0) >= DIE_ROUTE_MIN_METAL:
        put("FIX BY VIEW", f"{pk['count']} open {pk['layer']} pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)")
    if fa["blocked_above"]:
        put("FIX BY PIN RE-PLAN", f"{fa['blocked_above']} of {fa['face_pins']} face pins covered by the tile's own metal on the "
                                  f"layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)")
    for f in r.get("child_lint", {}).get("fails", []):
        if f.startswith("(c)"):
            put("FIX BY PIN RE-PLAN", "child_lint " + f[:170] + " (the tile's own signals reach its strap layer: re-route under the cap)")
        elif f.startswith(("(a)", "(b)")):
            put("FIX BY VIEW" if f.startswith("(a)") else "FIX BY PIN RE-PLAN", "child_lint " + f[:170])
    if "face" in cat or "pin_layer" in cat:
        put("FIX BY PIN RE-PLAN", "pins on another face / layer than the slot: " + "; ".join((cat.get("face") or []) + (cat.get("pin_layer") or []))[:260])
    if "outline" in cat:
        put("FIX AT DIE", cat["outline"][0] + " (slot change request or a wrapper at the slot outline)")
    if "names" in cat:
        put("FIX AT DIE", "contract / generator pin names differ from the view: " + "; ".join(cat["names"])[:220])
    if "cell" in cat:
        put("FIX AT DIE", cat["cell"][0] + " (alias view: bind by the master's own name)")
    if "layer" in cat:
        if r.get("cluster_child"):
            put("ACCEPT", cat["layer"][0] + " inside a hardened cluster (the cluster's plan owns the layers)")
        else:
            put("ACCEPT", cat["layer"][0] + " (closed tile stands; die tracks it blocks: see the legacy-layer table; re-route "
                                             "only under a hot window, reroute_reason die_window)")
    if "insertion" in cat:
        put("FIX AT DIE", cat["insertion"][0] + " (die clock tap level per the clock delivery rule)")
    if pk.get("count") and not pk.get("marker") and (CL.metal(pk.get("layer")) or 0) < DIE_ROUTE_MIN_METAL:
        put("ACCEPT", f"{pk['count']} open {pk['layer']} pockets: the die does not route on {pk['layer']} over a tile")
    if cls is None:
        return "ACCEPT", ["clean: no blocked pin, no pocket on a die layer, fits its slot"]
    return cls, why


def audit_master(store, cell, info, contract_path, contract):
    r = dict(master=cell, instances=info["instances"], kinds=sorted(info["kinds"]), slot=info.get("slot"), view=info["view"],
             binding=info.get("binding"))
    lef, macro = store.materialise(info["view"], cell)
    if lef is None:
        r["error"] = macro
        return r
    r["macro"] = macro
    r["hard_ip"] = bool(re.search(HARD_RE, info["view"]))
    slot = info.get("slot")
    s = next((x for x in contract["slots"] if x.get("name") == slot), None) if slot else None
    same_cell = bool(s) and s.get("cell") == macro
    try:
        L = CL.lint(str(lef), None, contract_path if same_cell else None, slot if same_cell else None, {"d"},
                    strict_pockets=True)
    except (ValueError, KeyError, OSError) as ex:
        r["error"] = f"child_lint: {type(ex).__name__}: {ex}"
        return r
    text = lef.read_text(errors="replace")
    m = CL.parse_lef(text, macro)
    fa, pk = L["info"]["face"], L["info"].get("pockets") or {}
    sig_top = max([CL.metal(x[0]) or 0 for n, p in m["pins"].items() if not CL.is_pg(n, p) for x in p["rects"]] or [0])
    obs_top = max([CL.metal(x[0]) or 0 for x in m["obs"]] or [0])
    r.update(outline=[m["W"], m["H"]], pg_top=L["info"]["pg"]["top_layer"], top_layer=f"M{max(sig_top, obs_top)}",
             signal_pin_top=f"M{sig_top}", obs_top=f"M{obs_top}", pins=pin_table(m),
             pin_bits=sum(1 for n, p in m["pins"].items() if not CL.is_pg(n, p)),
             face=dict(face_pins=fa["face_pins"], blocked_above=fa["blocked_above"],
                       blocked_above_pct=round(100.0 * fa["blocked_above"] / fa["face_pins"], 2) if fa["face_pins"] else 0.0,
                       blocked_same=fa["blocked_same"], band_same=fa["band_same"], examples=fa["examples"][:3],
                       same_examples=fa["same_examples"][:3]),
             pockets={k: pk.get(k) for k in ("layer", "count", "marker", "area_um2", "d_um", "error") if k in pk},
             child_lint=dict(verdict=L["verdict"], fails=[x[:300] for x in L["fails"]], warns=[x[:200] for x in L["warns"]]),
             insertion_ps=next((v["max_ps"] for v in (L["info"].get("clock_insertion") or {}).values() if v), None))
    bad, notes = [], []
    if s:
        ck = (s.get("clock_entry") or {}).get("pin") or "clk"
        ck = ck if ck in m["pins"] else next((c for c in ("clk", "ck", "clock") if c in m["pins"]), ck)
        k = VSF.view_facts(lef, lef.parent, ck, [x for x in ("rst_n", "rst", "rs_n") if x in m["pins"]])
        s_cmp = dict(s)
        vcap = CL.cap_str(s.get("view_cap"))
        if vcap and (CL.metal(k["cap"]) or 0) > (CL.metal(CL.cap_str(s.get("layer_cap")) or "M0") or 0):
            s_cmp["layer_cap"] = vcap
            notes.append(f"cap {k['cap']} judged against the slot view_cap {vcap}")
        if s.get("cell") != macro:
            bad.append(f"slot cell {s.get('cell')} != view macro {macro}")
        b, n = SF.compare(k, s_cmp)
        ow, oh = float(s["outline"]["w"]), float(s["outline"]["h"])
        if abs(ow - m["W"]) <= OUTLINE_TOL_UM and abs(oh - m["H"]) <= OUTLINE_TOL_UM and any(x.startswith("outline") for x in b):
            b = [x for x in b if not x.startswith("outline")]      # the generators shave 0.024 um off an abutted slot
            n.append(f"outline {m['W']:g} x {m['H']:g} within {OUTLINE_TOL_UM} um of the slot {ow:g} x {oh:g} (abutment shave)")
        bad += b
        notes += n
        r["slot_layers"] = dict(layer_cap=CL.cap_str(s.get("layer_cap")), view_cap=vcap, pg_layer=s.get("pg_layer"),
                                signal_max_layer=s.get("signal_max_layer"))
        r["cluster_child"] = bool(s.get("parent")) and s.get("parent") != next(
            (x["name"] for x in contract["slots"] if x.get("kind") == "die"), None)
        r["slot_outline"] = [s["outline"]["w"], s["outline"]["h"]]
    else:
        notes.append("no contract slot (die-placed master of the case): outline / faces not checked against a slot")
    r["slot_fit"] = dict(status="mismatch" if bad else ("fit" if s else "no slot"), mismatches=[x[:300] for x in bad],
                         notes=[x[:200] for x in notes])
    r["mismatch"] = {k_: v for k_, v in categorise(bad).items()}
    r["class"], r["why"] = classify(r)
    return r


def collect(a):
    contract = json.loads(Path(a.contract).read_text())
    cells = collections.OrderedDict()
    for s in contract["slots"]:
        if s.get("kind") == "die":
            continue
        c = cells.setdefault(s["cell"], dict(instances=0, kinds=set(), slot=s["name"]))
        c["instances"] += 1
        c["kinds"].add(s.get("kind") or "slot")
    if a.case_census:
        for k, v in json.loads(Path(a.case_census).read_text())["masters"].items():
            if k not in cells:
                cells[k] = dict(instances=v.get("instances", 0), kinds={"die case master"}, slot=None)
    bound = {}
    for f in a.views_from or []:
        for t in json.loads(Path(f).read_text()).get("tiles", []):
            if t.get("view"):
                bound[t["cell"]] = (t["view"], t.get("binding") or "pinreg_audit")
    store = Store(a.ref, a.cache)
    out, noview = [], []
    for cell, info in cells.items():
        view, how = None, None
        if cell in bound and bound[cell][0] in store.dirs:
            view, how = bound[cell]
        else:
            c = store.by_name(cell)
            if c:
                view, how = c[0], "master name" + (f" (1 of {len(c)} views)" if len(c) > 1 else "")
        if view is None:
            noview.append(dict(master=cell, instances=info["instances"], kinds=sorted(info["kinds"])))
            continue
        row = audit_master(store, cell, dict(info, view=view, binding=how), a.contract, contract)
        alts = []
        for v2 in store.by_name(cell):
            if v2 == view:
                continue
            r2 = audit_master(store, cell, dict(info, view=v2, binding="alternative"), a.contract, contract)
            if r2.get("error"):
                continue
            alts.append(dict(view=v2, cls=r2["class"], top_layer=r2["top_layer"], blocked_above=r2["face"]["blocked_above"],
                             blocked_same=r2["face"]["blocked_same"], pockets=r2["pockets"].get("count") or 0,
                             pocket_marker=bool(r2["pockets"].get("marker")), slot_fit=r2["slot_fit"]["status"],
                             mismatch=sorted(r2["mismatch"])))
        if alts:
            row["other_views"] = alts
            better = [x for x in alts if not row.get("error") and RANK.index(x["cls"]) > RANK.index(row["class"])
                      and not ({"outline", "cell"} & set(x["mismatch"]))]
            if better and row["class"] in ("FIX BY PIN RE-PLAN", "FIX BY VIEW"):
                b_ = max(better, key=lambda x: (RANK.index(x["cls"]), -x["blocked_above"], -x["pockets"], -view_rank(x["view"])))
                row["why"].insert(0, f"FIX AT DIE: a better published view of this master exists: bind {b_['view']} "
                                     f"({b_['cls']}; top {b_['top_layer']}, blocked above {b_['blocked_above']}, pockets "
                                     f"{b_['pockets']}) instead of {view}")
                row["class_of_bound_view"] = row["class"]
                row["class"] = "FIX AT DIE" if b_["cls"] == "ACCEPT" else b_["cls"]
        out.append(row)
        print(f"  {cell}: {out[-1].get('class') or out[-1].get('error')}", file=sys.stderr)
    return contract, out, noview


def md(rec):
    L = [f"# Die pin audit: {rec['die']} (contract v{rec['contract_version']}, views {rec['ref']})", "",
         f"{rec['summary']['masters_with_lef']} masters with a published LEF ({rec['summary']['instances_with_lef']} instances) of "
         f"{rec['summary']['masters']} ({rec['summary']['instances']} instances); "
         + ", ".join(f"{k} {v['masters']} masters / {v['instances']} inst" for k, v in rec["summary"]["by_class"].items()) + ".", "",
         "| master | inst | top layer | pins by face/layer | face pins | blocked above | own-stub OBS | open pockets | slot fit | class |",
         "|---|---:|---|---|---:|---:|---:|---|---|---|"]
    for r in rec["masters"]:
        if r.get("error"):
            L.append(f"| {r['master']} | {r['instances']} | - | - | - | - | - | - | ERROR {r['error'][:80]} | - |")
            continue
        pk = r["pockets"]
        pks = "-" if not pk.get("count") else f"{pk['layer']} {pk['count']}" + (" (marked)" if pk.get("marker") else "")
        sf = r["slot_fit"]["status"] + ("" if not r["mismatch"] else ": " + ", ".join(r["mismatch"]))
        lf = sorted({f[:3] for f in r["child_lint"]["fails"]})
        sf += "" if not lf else "; lint " + " ".join(lf)
        L.append(f"| {r['master']} | {r['instances']} | {r['top_layer']} (PG {r['pg_top']}) | "
                 + " ".join(f"{k} {v}" for k, v in r["pins"].items())
                 + f" | {r['face']['face_pins']} | {r['face']['blocked_above']} ({r['face']['blocked_above_pct']:g} %) | "
                   f"{r['face']['blocked_same']} | {pks} | {sf} | {r['class']} |")
    L += ["", "## Findings per master", ""]
    for r in rec["masters"]:
        if r.get("error") or (r["class"] == "ACCEPT" and r["why"][0].startswith("clean")):
            continue
        L.append(f"- **{r['master']}** x{r['instances']} ({r['view']}): {r['class']}")
        L += [f"  - {w}" for w in r["why"]]
    L += ["", "## Masters without a published LEF (not auditable)", "",
          ", ".join(f"{x['master']} x{x['instances']}" for x in rec["no_view"]) or "none", ""]
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------------ report
def align_class(c, real):
    """class of a flagged bundle class (pin_align record `classes` row) given the masters that have a published view"""
    dm, lm = c["drv"].split(".")[0], c["load"].split(".")[0]
    n_real = (dm in real) + (lm in real)
    rigid = c.get("jog_max", 0.0) > 0 and abs(c.get("jog_max", 0.0) - c.get("jog_mean", 0.0)) <= 0.1 * c["jog_max"]
    order_bad = any(k in ("reversed", "interleaved") for k in c.get("order", {}))
    if c["kind"] == "uturn":
        return "FIX AT DIE", "u-turn: move the slot / relay so the two faces look at each other, or flip the instance"
    if n_real == 0:
        return "FIX AT DIE", "both ends are generated abstracts: the die pin plan places them (centre the port on its peer)"
    if n_real == 1:
        return "FIX AT DIE", f"one end is a closed view ({dm if dm in real else lm}): move the generated end / the relay to face its pins"
    if order_bad and c["kind"] == "straight":
        return "FIX BY PIN RE-PLAN", "both ends are closed views and the bit order is not preserved: mirror the instance at the die if legal, else re-plan one tile's pin order (reroute_reason slot_change)"
    if rigid:
        return "FIX AT DIE", "both ends are closed views with one common offset: shift the slot / relay by the jog"
    return "FIX BY PIN RE-PLAN", "both ends are closed views with different pin pitch / spread: re-plan one tile's pin range (pin_ranges; reroute_reason slot_change), or accept the jog with a lane"


def report(out, dies):
    """README.md of the audit directory from <die>_masters.json, <die>_pin_align.json, <die>_legacy_layers.json"""
    out = Path(out)
    L = ["# Die pin-readiness audit, 2026-10-13 (both ROM dies)", "",
         "Owner question: will covered or badly placed pins still break the die route?  Tools: tools/hier_contract/"
         "die_pin_audit.py (master tables: child_lint --strict-pockets + slot fit on every published LEF), pin_align.py "
         "(bundle alignment; gate in the generators' check step and slot_fit), legacy_layer_cuts.py (die tracks under "
         "M6 / M7 tiles).  Per-die detail: <die>_masters.md, <die>_pin_align.json, <die>_legacy_layers.md.", ""]
    summ = {}
    for die in dies:
        mf, pf, lf = (out / f"{die}_masters.json", out / f"{die}_pin_align.json", out / f"{die}_legacy_layers.json")
        if not mf.exists():
            continue
        M = json.loads(mf.read_text())
        ok = [r for r in M["masters"] if not r.get("error")]
        real = {r["master"] for r in ok if r.get("macro") == r["master"]}
        s = M["summary"]
        L += [f"## {die} (contract v{M['contract_version']}, views {M['ref']})", "",
              f"**Masters**: {s['masters_with_lef']} of {s['masters']} masters have a published LEF "
              f"({s['instances_with_lef']} of {s['instances']} instances). Face pins blocked from above: "
              f"{s['blocked_above_pins']} pins on {s['blocked_above_masters']} masters; own-stub OBS on {s['blocked_same_masters']} "
              f"masters; open pockets on {s['open_pocket_masters']} masters ({sum(1 for r in ok if r['pockets'].get('count') and not r['pockets'].get('marker') and (CL.metal(r['pockets'].get('layer')) or 0) >= DIE_ROUTE_MIN_METAL)} on a die layer >= M6); "
              f"slot mismatch on {s['slot_mismatch_masters']} masters.", "",
              "| class | masters | instances | masters |", "|---|---:|---:|---|"]
        for c in RANK:
            rows = [r for r in ok if r["class"] == c]
            names = ", ".join(f"{r['master']} x{r['instances']}" for r in sorted(rows, key=lambda r: -r["instances"])[:14])
            L.append(f"| {c} | {len(rows)} | {sum(r['instances'] for r in rows)} | {names}{' ...' if len(rows) > 14 else ''} |")
        summ[die] = dict(masters=s, by_class={c: [sum(1 for r in ok if r["class"] == c), sum(r["instances"] for r in ok if r["class"] == c)] for c in RANK})
        L.append("")
        if pf.exists():
            P = json.loads(pf.read_text())
            fl = [c for c in P["classes"] if c["worst"] != "OK"]
            for c in fl:
                c["class"], c["fix"] = align_class(c, real)
            ac = collections.Counter(c["class"] for c in fl)
            L += [f"**Pin alignment** ({P.get('generator', '')} {P.get('qwen_recipe') or ''}; pins: {P.get('pin_source', 'LEFs')}; "
                  f"published-view overlay on {P.get('published_view_overlay', {}).get('masters', 0)} masters / "
                  f"{P.get('published_view_overlay', {}).get('ports', 0)} ports): {P['bundles']} bundles / {P['bits']} bits "
                  f"({P['bits_without_pin']} bits without a pin). Verdict {P['verdict']}: FAIL {P['by_verdict'].get('FAIL', 0)}, WARN "
                  f"{P['by_verdict'].get('WARN', 0)}, OK {P['by_verdict'].get('OK', 0)} bundles. Jog > {P['warn_um']:g} um: "
                  f"{P['jog_over_warn']['bundles']} bundles / {P['jog_over_warn']['bits']} bits (max {P['jog_max']:.1f} um); bit order not "
                  f"preserved: {P['order_not_preserved']['bundles']} bundles / {P['order_not_preserved']['bits']} bits; kinds "
                  + ", ".join(f"{k} {v}" for k, v in P["by_kind"].items()) + f"; pin-to-pin length mean {P.get('len_mean')} / max "
                  f"{P.get('len_max')} um.", "",
                  "Jog distribution of straight bundles (max jog per bundle): "
                  + "; ".join(f"{k} um: {v['bundles']} bundles / {v['bits']} bits" for k, v in P["jog_hist_um"].items()) + ".", "",
                  f"Flagged bundle classes: {len(fl)} ({', '.join(f'{k} {v}' for k, v in ac.items())}).", "",
                  "| driver -> load | kind | bundles | bits | jog max / mean um | gap min um | jog cut max | order | len max um | verdict | class | example |",
                  "|---|---|---:|---:|---|---:|---:|---|---:|---|---|---|"]
            for c in fl[:60]:
                ex = c.get("example") or {}
                L.append(f"| {c['drv']} -> {c['load']} | {c['kind']} | {c['bundles']} | {c['bits']} | {c['jog_max']:g} / {c['jog_mean']:g} | "
                         f"{c['gap_min'] if c['gap_min'] is not None else '-'} | {c['jog_cut_max'] if c['jog_cut_max'] is not None else '-'} | "
                         + " ".join(f"{k} {v}" for k, v in c["order"].items())
                         + f" | {c['len_max']:g} | {c['worst']} | {c['class']} | {ex.get('bus', '')} {ex.get('drv', '')} -> {ex.get('load', '')} |")
            if len(fl) > 60:
                L.append(f"| ... {len(fl) - 60} more classes in {pf.name} | | | | | | | | | | | |")
            L.append("")
            summ[die]["pin_align"] = dict(verdict=P["verdict"], bundles=P["bundles"], bits=P["bits"], by_verdict=P["by_verdict"],
                                          jog_over_warn=P["jog_over_warn"], order_not_preserved=P["order_not_preserved"],
                                          jog_max=P["jog_max"], flagged_classes=len(fl), flagged_by_class=dict(ac),
                                          by_kind=P["by_kind"], bits_without_pin=P["bits_without_pin"])
            (out / f"{die}_pin_align_classes.json").write_text(json.dumps(fl, indent=1) + "\n")
        if lf.exists():
            G = json.loads(lf.read_text())
            g, w = G["summary"], G["cut_windows"]
            L += [f"**Legacy M6 / M7 tiles** (die-placed, measured view top >= M6): {g['legacy_masters']} masters / "
                  f"{g['legacy_instances']} instances, {g['legacy_area_mm2']} mm2; they block {g['legacy_m6_track_mm']} track-mm of die "
                  f"M6 and {g['legacy_m7_track_mm']} track-mm of die M7. Cut windows (260 um): {w['windows_over_limit']} positions over "
                  f"{w['limit']}, of which {w['windows_over_limit_only_because_of_legacy']} only because legacy tiles hold M6 / M7. "
                  f"Detail: {die}_legacy_layers.md.", ""]
            summ[die]["legacy"] = dict(g, windows_over_limit=w["windows_over_limit"],
                                       windows_over_only_legacy=w["windows_over_limit_only_because_of_legacy"])
    (out / "README.md").write_text("\n".join(L) + "\n")
    (out / "summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    return summ


def main(argv=None) -> int:
    if (argv if argv is not None else sys.argv[1:])[:1] == ["report"]:
        ap = argparse.ArgumentParser()
        ap.add_argument("mode")
        ap.add_argument("--out", required=True)
        ap.add_argument("--die", action="append", required=True)
        a = ap.parse_args(argv)
        print(json.dumps(report(a.out, a.die), indent=1)[:3000])
        return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["masters"])
    ap.add_argument("--die", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--case-census")
    ap.add_argument("--views-from", action="append")
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=os.path.join(os.environ.get("TMPDIR", "/tmp"), "die_pin_audit_cache"))
    a = ap.parse_args(argv)
    contract, rows, noview = collect(a)
    ok = [r for r in rows if not r.get("error")]
    by = collections.OrderedDict((c, dict(masters=0, instances=0)) for c in CLASSES)
    for r in ok:
        by[r["class"]]["masters"] += 1
        by[r["class"]]["instances"] += r["instances"]
    rec = dict(schema=SCHEMA, die=a.die, contract=a.contract, contract_version=contract.get("version"),
               ref=f"{a.ref} {git('rev-parse', '--short', a.ref).strip()}",
               summary=dict(masters=len(rows) + len(noview), instances=sum(r["instances"] for r in rows) + sum(x["instances"] for x in noview),
                            masters_with_lef=len(rows), instances_with_lef=sum(r["instances"] for r in rows), by_class=by,
                            blocked_above_masters=sum(1 for r in ok if r["face"]["blocked_above"]),
                            blocked_above_pins=sum(r["face"]["blocked_above"] for r in ok),
                            blocked_same_masters=sum(1 for r in ok if r["face"]["blocked_same"]),
                            open_pocket_masters=sum(1 for r in ok if r["pockets"].get("count") and not r["pockets"].get("marker")),
                            slot_mismatch_masters=sum(1 for r in ok if r["slot_fit"]["status"] == "mismatch"),
                            errors=len(rows) - len(ok)),
               masters=rows, no_view=noview)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.die}_masters.json").write_text(json.dumps(rec, indent=1) + "\n")
    (out / f"{a.die}_masters.md").write_text(md(rec) + "\n")
    print(json.dumps(rec["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
