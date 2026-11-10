#!/usr/bin/env python3
"""DIE-S81-85 11-09 CORE-CTAP-WIDE-1109: early core taps for every grid-tapped hard-core clock pin the pair.py
--core-taps rule catches, and stale early-tap means corrected to the current view (class follow-up of ENG-CTAP-1109).

Class (OT_TAP_CORE "needs an early core tap"): a hard-core clock pin left on a GRID tap arrives at grid leg + internal
latency; once internal > common latency - CORE_TAP_MARGIN_PS (250 - 40 = 210 ps, pair.py add_core_taps) the pin cannot
meet 250 +/- 20, CTS pads the tap and hold cells land on setup paths (leaf t16 GRT TT -237.8 / FF hold -220.45,
eng__t1 FF hold -712.58).

derive (reads the views of SRC; writes the entries sidecar, no plan change):
  ADD   every (type, core, clock pin) whose kit-exact core_latency row (gen_phys.core_latency_files with the type's own
        core_mean_contract_options, i.e. the rows a kit writes) has tap 'grid' and whose DECLARED view mean > 210 ps.
        Declared mean = ENG-CTAP-1109 basis: the selected view's measured record (clock_contract.json / signoff.json /
        insertion.json, core_clock_contract.load, pin-register mean, TT and FF) else the selected view's TT/FF liberty
        max_clock_tree_path rise (ETM; no measured mean in the view).  Form = the 143 early-tap types / ENG-CTAP-1109:
        clock.taps kind core, name <inst>.<pin>, insertion_ps + insertion_ff_ps, budget_owner 'parent_budget ...',
        clock.core_taps 'early'.  Site = pair.py core_tap_xy (the clock pin's LEF centre in the type frame, moved by
        schema.tap_clear off every hard core into a channel, clear of the grid taps and every other core tap).
  FIX   every existing early core tap (single core pin, no core_group / merged ports) whose TT or FF insertion differs
        by > 0.01 ps from a MEASURED record in the selected view's own directory (pin-register mean).  The type keeps
        its kit form (gen_phys.core_mean_contract_options): owner 'parent_budget ...' only in mean-contract types.  Taps whose view
        holds no record (their value is a routed measurement made elsewhere, or a budget) are left as they are: an ETM
        max bound is not a mean and never replaces one.
        A pin that is a declared pad_clock sink (clock.pad_clock pins[].sink_pins: serdes u_dec.u_chn.clk is clocked
        by the PMA recovered clock pma_rck, not the die clock) is never tapped; it is reported (pad_clock).
        A type where tap_clear finds no channel for a caught pin (slice_station__t51: native split halves, 17 um
        gap) gets no ADD; it is reported (no_site).
  SITE  existing core taps are NOT moved: every far tap already sits on the schema.tap_clear site of its pin (the pin
        is under a macro cluster); a move onto the pin is a different (through-macro) rule, reported, not invented.
apply: PLAN_IN PLAN_OUT ENTRIES.json [REPORT.json] - text edits in the plan's own indent-1 style (only clock.taps /
        clock.core_taps of the listed types); every other type and every non-type key is asserted unchanged.
usage: delta_core_ctap_wide_1109.py derive SRC PLAN ENTRIES.json
       delta_core_ctap_wide_1109.py apply PLAN_IN PLAN_OUT ENTRIES.json [REPORT.json]"""
import copy
import json
import re
import sys
from pathlib import Path

EVENT = "CORE-CTAP-WIDE-1109"
TARGET_PS, TARGET_FF_PS, MARGIN_PS = 250.0, 202.5, 40.0
FF_TT = 0.81   # schema.FF_TT_INSERTION_RATIO, used only when the view has no FF liberty


def derive(src, plan, out):
    import contextlib
    import functools
    import io
    import os
    import tempfile
    src = Path(src).resolve()
    os.chdir(src)
    sys.path[:0] = [str(src / "tools/die_plan")]
    import cores as C
    import core_clock_contract as CC
    _lc, _lp = C.lib_clocks, C.lef_pins
    C.lib_clocks = functools.lru_cache(None)(lambda p: _lc(p))          # read-only memo: a view is parsed once
    C.lef_pins = functools.lru_cache(None)(lambda p, m=None: _lp(p, m))
    import schema as S
    import gen_phys as G
    P = S.Plan(S.load(plan))
    rule = float(P.clock["insertion_ps"]) - MARGIN_PS

    def declared(c):
        try:
            v = CC.load(c, src, require_signed=False, plan_type={})
            return {p: dict(tt=round(x["corners"]["tt"]["mean_ps"], 5), ff=round(x["corners"]["ff"]["mean_ps"], 5),
                            basis="pin_register_mean", src=str(x["contract_source"]).replace(str(src) + "/", ""))
                    for p, x in v.items()}, True
        except CC.ContractError:
            lib = C.resolve(c["lib"], src)
            ffl = lib.with_name(lib.name.replace("_tt.lib", "_ff.lib"))
            ff = C.lib_clocks(ffl) if lib.name.endswith("_tt.lib") and ffl.is_file() else {}
            return {p: dict(tt=round(x["rise"], 2), ff=round(ff[p]["rise"], 2) if p in ff else round(FF_TT * x["rise"], 2),
                            basis="lib max_clock_tree_path rise (ETM; no measured mean in the view)"
                            + ("" if p in ff else "; FF = 0.81 x TT (no FF liberty)"), src=c["lib"])
                    for p, x in C.lib_clocks(lib).items()}, False

    def site(t, c, pin, taken):
        g = C.lef_pins(C.resolve(c["lef"], src), c.get("module"))
        pp = g.get(pin) or g.get(pin.split("[")[0])
        w, h = c["outline_um"]
        x, y = pp["xy"] if pp and pp.get("xy") else (w / 2, h / 2)
        o = c.get("orient", "R0")
        x, y = {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]
        dx, dy = c.get("track_offset_um", [0.0, 0.0])
        px, py = c["origin_um"][0] + dx + x, c["origin_um"][1] + dy + y
        sx, sy = S.tap_clear(t, px, py, taken)
        return [round(sx, 4), round(sy, 4)], [round(px, 4), round(py, 4)]

    ents, report = {}, dict(rule_ps=rule, add={}, fix={}, etm_only={}, far_sites={}, errors={}, no_site={}, pad_clock={})
    for tn in sorted(P.types):
        t = P.types[tn]
        if not t.get("hard_cores"):
            continue
        kd = Path(tempfile.mkdtemp(prefix="ccw_"))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                G.core_latency_files(P, tn, kd, src, **G.core_mean_contract_options(P, tn))
            f = kd / "core_latency.json"
            rows = json.loads(f.read_text())["rows"] if f.is_file() else []
        except Exception as e:  # noqa: BLE001  (WAIT-DEP cores without a selected lib: reported, not tapped)
            report["errors"][tn] = f"{type(e).__name__}: {e}"[:300]
            rows = []
        finally:
            for f in kd.iterdir():
                f.unlink()
            kd.rmdir()
        hc = {c["inst"]: c for c in t["hard_cores"]}
        decl = {}
        ck = t.get("clock", {}) or {}
        taps = [tp for tp in ck.get("taps", []) or [] if tp.get("kind") == "core"]
        names = {tp.get("name") for tp in ck.get("taps", []) or []}
        taken = [(x, y) for _, x, y in S.tap_grid(P, tn)] + [tuple(tp["xy"]) for tp in taps if tp.get("xy")]
        add, fix = [], []
        pad_sinks = {(x["module"], x["pin"]) for p in (ck.get("pad_clock") or {}).get("pins", []) or []
                     for x in p.get("sink_pins", []) or []}
        for r in rows:
            inst = r.get("logical_inst", r["inst"])
            if r["tap"] != "grid" or inst not in hc or not hc[inst].get("lib"):
                continue
            if inst not in decl:
                decl[inst] = declared(hc[inst])
            d = decl[inst][0].get(r["pin"])
            if d is None:
                continue
            if d["tt"] <= rule:
                if r["rise_ps"] > rule:
                    report["etm_only"].setdefault(tn, []).append(dict(inst=inst, pin=r["pin"], kit_row_ps=r["rise_ps"],
                                                                      declared_tt_ps=d["tt"]))
                continue
            if (hc[inst].get("module"), r["pin"]) in pad_sinks:
                # a declared pad-clock sink (serdes u_dec.u_chn.clk = pma_rck, ot_pdie_serdes.sv) is not on the die
                # clock: an early die-clock tap would change its clock domain.  Reported, never tapped.
                report["pad_clock"].setdefault(tn, []).append(dict(inst=inst, pin=r["pin"], kit_row_ps=r["rise_ps"],
                                                                   declared_tt_ps=d["tt"]))
                continue
            name = f"{inst}.{r['pin']}"
            assert name not in names, (tn, name)
            try:
                xy, pin_xy = site(t, hc[inst], r["pin"], taken)
            except ValueError as e:   # schema.tap_clear: no channel near the pin -> the whole type is left out, reported
                report["no_site"].setdefault(tn, []).append(dict(inst=inst, pin=r["pin"], declared_tt_ps=d["tt"],
                                                                 why=str(e)[:200]))
                continue
            taken.append(tuple(xy))
            add.append(dict(name=name, module=hc[inst].get("module"), xy=xy, pin_xy=pin_xy, insertion_ps=d["tt"],
                            insertion_ff_ps=d["ff"], basis=d["basis"], src=d["src"], kit_row_ps=r["rise_ps"],
                            kit_tap_was="grid"))
        for tp in taps:
            if "core_group" in tp or tp.get("merged_clock_ports") or "insertion_ps" not in tp:
                continue
            nm = tp["name"]
            inst = max((i for i in hc if nm == i or nm.startswith(i + ".")), key=len, default=None)
            if inst is None or not hc[inst].get("lib"):
                continue
            if inst not in decl:
                decl[inst] = declared(hc[inst])
            vals, measured = decl[inst]
            pin = nm[len(inst) + 1:] if nm != inst else (next(iter(vals)) if len(vals) == 1 else None)
            if not measured or pin not in vals:
                continue
            d = vals[pin]
            ff_was = tp.get("insertion_ff_ps")
            if abs(float(tp["insertion_ps"]) - d["tt"]) <= 0.01 and (ff_was is None or abs(float(ff_was) - d["ff"]) <= 0.01):
                continue
            fix.append(dict(name=nm, module=hc[inst].get("module"), insertion_ps_was=tp["insertion_ps"],
                            insertion_ff_ps_was=ff_was, insertion_ps=d["tt"], insertion_ff_ps=d["ff"], basis=d["basis"],
                            src=d["src"], budget_owner_was=tp.get("budget_owner")))
        for tp in taps:
            nm = tp["name"]
            inst = max((i for i in hc if nm.startswith(i + ".")), key=len, default=None)
            if inst is None or "core_group" in tp or not tp.get("xy"):
                continue
            others = [xy for xy in taken if tuple(xy) != tuple(tp["xy"])]
            try:
                rule_xy, pin_xy = site(t, hc[inst], nm[len(inst) + 1:], others)
            except Exception:  # noqa: BLE001
                continue
            dist = abs(tp["xy"][0] - pin_xy[0]) + abs(tp["xy"][1] - pin_xy[1])
            if dist > 40.0:
                report["far_sites"].setdefault(tn, []).append(dict(
                    name=nm, xy=tp["xy"], pin_xy=pin_xy, manhattan_um=round(dist, 1), tap_clear_site=rule_xy,
                    tap_clear_manhattan_um=round(abs(rule_xy[0] - pin_xy[0]) + abs(rule_xy[1] - pin_xy[1]), 1)))
        if tn in report["no_site"]:
            add = []    # a partial set would leave pins of the same core on the grid: no ADD for this type
        if add or fix:
            ents[tn] = dict(add=add, fix=fix, core_taps_was=ck.get("core_taps"),
                            mode_was=G.core_mean_contract_options(P, tn))
            report["add"][tn] = len(add)
            if fix:
                report["fix"][tn] = len(fix)
    Path(out).write_text(json.dumps(dict(event=EVENT, plan=str(plan), rule_ps=rule, types=ents, census=report),
                                    indent=1) + "\n")
    print(f"{EVENT} derive: {len(ents)} types, add {sum(len(e['add']) for e in ents.values())} pins, "
          f"fix {sum(len(e['fix']) for e in ents.values())} taps; errors {sorted(report['errors'])}")


def apply(pin, pout, entries, rep_p=None):
    sys.path[:0] = [str(Path(__file__).resolve().parent)]
    from delta_romq_split_1106 import spans
    E = json.loads(Path(entries).read_text())["types"]
    text = open(pin).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    for tn, e in E.items():
        ck = raw["partition_types"][tn].setdefault("clock", {})
        assert ck.get("core_taps") == e["core_taps_was"] and ck.get("core_taps") in (None, "early"), (tn, ck.get("core_taps"))
        taps = ck.setdefault("taps", [])
        byname = {tp.get("name"): tp for tp in taps}
        for f in e["fix"]:
            tp = byname[f["name"]]
            assert tp.get("kind") == "core" and tp["insertion_ps"] == f["insertion_ps_was"], (tn, f["name"])
            tp["insertion_ps"], tp["insertion_ff_ps"] = f["insertion_ps"], f["insertion_ff_ps"]
            # a type of the legacy (plan-insertion) kit form keeps that form: a 'parent_budget' owner on its last
            # non-budget tap would switch gen_phys core_mean_contract_options to the mean contract (LP types: lnland
            # signoff.json has no per-pin means -> ContractError); the mean-contract types keep 'parent_budget'.
            pre = "parent_budget" if e["mode_was"]["mean_contract"] else "view"
            tp["budget_owner"] = f"{pre} {f['basis']} {f['src']}; {EVENT} DIE-S81-85 (was {f['insertion_ps_was']:g})"
            tp["note"] = (tp.get("note", "") + f" | {EVENT}: insertion = the selected view's measured record "
                          f"{f['insertion_ps']:g} / FF {f['insertion_ff_ps']:g} (was {f['insertion_ps_was']:g})").lstrip(" |")
        for a in e["add"]:
            assert a["name"] not in byname, (tn, a["name"])
            taps.append(dict(name=a["name"], kind="core", xy=a["xy"], insertion_ps=a["insertion_ps"],
                             insertion_ff_ps=a["insertion_ff_ps"],
                             budget_owner=f"parent_budget {a['basis']} {a['src']}; {EVENT} DIE-S81-85",
                             note=f"CORELAT-SQ-1: early core tap (12.3 v5.0) at the core clock pin (pair.py core_tap_xy / "
                                  f"schema.tap_clear); {EVENT} (pair.py --core-taps rule: internal "
                                  f"{a['insertion_ps']:g} > {TARGET_PS - MARGIN_PS:g} ps; was grid)"))
        ck["core_taps"] = "early"
    sp = spans(text)
    edits = []
    for tn, e in E.items():
        new_taps = raw["partition_types"][tn]["clock"]["taps"]
        if ("partition_types", tn, "clock", "taps") in sp:
            a, b = sp[("partition_types", tn, "clock", "taps")]
            line0 = text.rfind("\n", 0, a) + 1
            ind = re.match(r" *", text[line0:]).group(0)
            assert text[line0 + len(ind):a] == '"taps": ', (tn, text[line0:a])
            new = json.dumps(new_taps, indent=1).replace("\n", "\n" + ind)
            if e["core_taps_was"] is None:
                edits.append((line0, b, ind + '"core_taps": "early",\n' + ind + '"taps": ' + new))
            else:
                edits.append((a, b, new))
        else:
            a, b = sp[("partition_types", tn, "clock")]
            assert text[a] == "{" and e["core_taps_was"] is None, tn
            line0 = text.rfind("\n", 0, a) + 1
            ind = re.match(r" *", text[line0:]).group(0) + " "
            new = json.dumps(new_taps, indent=1).replace("\n", "\n" + ind)
            body = text[a + 1:b - 1].strip()
            edits.append((a, a + 1, "{\n" + ind + '"core_taps": "early",\n' + ind + '"taps": ' + new
                          + ("," if body else "")))
    for a, b, new in sorted(edits, reverse=True):
        text = text[:a] + new + text[b:]
    assert json.loads(text) == raw
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in raw["partition_types"]:
        if tn not in E:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    open(pout, "w").write(text)
    rep = dict(event=EVENT, types=sorted(E), add={tn: [a["name"] for a in e["add"]] for tn, e in E.items() if e["add"]},
               fix={tn: [(f["name"], f["insertion_ps_was"], f["insertion_ps"]) for f in e["fix"]]
                    for tn, e in E.items() if e["fix"]})
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")
    print(f"{EVENT} apply: {len(E)} types, add {sum(len(e['add']) for e in E.values())}, "
          f"fix {sum(len(e['fix']) for e in E.values())}")


if __name__ == "__main__":
    if sys.argv[1] == "derive":
        derive(*sys.argv[2:5])
    elif sys.argv[1] == "apply":
        apply(*sys.argv[2:6])
    else:
        sys.exit(__doc__)
