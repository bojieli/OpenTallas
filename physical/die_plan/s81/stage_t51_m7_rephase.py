#!/usr/bin/env python3
"""S81-T51-PINFIX-2 11-12 (ready12b plan-delta STAGE, not applied): re-phase the 89 native M7 clock root pins of the
t51 native split children onto the DIE M7 lattice.

Cause: the die / parent M7 tracks are offset 0.032 / pitch 0.064 (tools/die_plan/schema.ASAP7_LAYERS).  The children sit
at track_offset_um [0.108, 0.012] (delta_t51_split_1109.py: "the 89 native M7 clock root pins keep the source M7 grid"),
so in the core frame the die M7 lattice is at 0.052 (gen_core_kit_legacy.native_m7_phase) while the roots are at 0.032:
20 nm off the parent tracks, and native_m7_phase refuses to generate the kits.  The shift is DERIVED per pin from
native_m7_phase (one value for every root, else refused), never given.

Staged (written under OUT at the same repo-relative paths, the plan as OUT/plan.json):
  1. inputs/core_pins/<module>.json   the 89 M7 root rows x += shift; pinhash recomputed (delta_t51_split_1109 rule);
                                       lef -> the staged contract LEF below
  2. plan.json                         slice_station__t51 clock.taps[].lands_on[] of the roots (xy x += shift), and the
                                       tap xy when it equals a moved landing; hard_cores[].lef -> the staged LEF
  3. station_split_1106/native_root_pins.json   ports[root].rect_um x0/x1 += shift (source_rect_um unchanged: it is
                                       the source-frame metal, the size check is what the generator asserts), and
     inputs/core_lef/<module>_m7r.lef  copy of the plan LEF with the root PIN M7 RECTs x += shift (the signed view LEF
                                       itself is not edited)
  receipt.json                         counts, the shift, and the follow-ups that regeneration owns (items 4-5).

  python3 -I stage_t51_m7_rephase.py --plan PLAN.json --repo REPO --out OUTDIR [--prove-kit e=KITDIR --prove-kit w=KITDIR]
--prove-kit: regenerate the root part of the kit (native_root_pin_contract -> native_m7_phase -> kit_tracks,
native_multiport_tcl io.tcl blocks, pins.json rows) from the STAGED inputs with the generator's own functions and
compare with a built kit (rc51f); exit 1 on any difference.
"""
import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_DEFAULT = HERE.parents[2]
TYPE = "slice_station__t51"
CHILD = {"e": "s81p_slice_station__t51_ot_s81_station_t51_native_e",
         "w": "s81p_slice_station__t51_ot_s81_station_t51_native_w"}
ROOTKEY = {"e": "ot_s81_station_t51_native_e", "w": "ot_s81_station_t51_native_w"}
S81 = Path("physical/die_plan/s81")
SPLIT = S81 / "station_split_1106/native_root_pins.json"
PROFILE = S81 / "station_split_1106/root_profile.json"   # per-root tap_window_port_ps (not moved by this stage)


def gen(repo):
    sys.path.insert(0, str(Path(repo) / S81 / "cores/legacy"))
    import gen_core_kit_legacy as G
    return G


def r4(v):
    return round(v, 4)


def pinhash(rows):
    return hashlib.sha256(json.dumps(sorted((q["name"], q["layer"], q["x"], q["y"]) for q in rows)).encode()).hexdigest()[:12]


def shift_lef(text, names, d):
    """x0 / x1 of every M7 RECT inside PIN <name> for name in names; -> (text, rects moved)"""
    out, cur, layer, n = [], None, None, 0
    for line in text.split("\n"):
        t = line.split()
        if t[:1] == ["PIN"]:
            cur, layer = t[1], None
        elif cur and t[:1] == ["LAYER"]:
            layer = t[1]
        elif cur and t[:2] == ["END", cur]:
            cur, layer = None, None
        elif cur in names and layer == "M7" and t[:1] == ["RECT"]:
            x0, y0, x1, y1 = map(float, t[1:5])
            ind = line[:len(line) - len(line.lstrip())]
            line = f"{ind}RECT {x0 + d:.4f} {y0:.4f} {x1 + d:.4f} {y1:.4f} ;"
            n += 1
        out.append(line)
    return "\n".join(out), n


def derive_shift(G, hc, plan, rects):
    """per-root shift (um) onto native_m7_phase's lattice; one value for all roots"""
    ph = round(G.native_m7_phase({}, hc, plan) * 1000)        # no roots -> the core-frame die M7 phase (nm)
    s = set()
    for r in rects.values():
        cx = round((r[0] + r[2]) / 2 * 1000)
        dd = (ph - cx) % 64
        s.add(dd if dd <= 32 else dd - 64)
    if len(s) != 1:
        raise SystemExit(f"{hc['module']}: roots need different shifts {sorted(s)} nm; refusing")
    return s.pop() / 1000.0, ph / 1000.0


def check_landings(t, moved_landings, nl):
    """forwarded roots (clock.child_root_taps.forwarded_roots: source-forwarded fclk_in_* ring write clocks) and
    landed roots may lack a tap; any other moved root without a landing refuses.  -> the forwarded roots without a tap"""
    fwd = set(t["clock"].get("child_root_taps", {}).get("forwarded_roots", []))
    landed = {lo["pin"] for tp in t["clock"]["taps"] for lo in tp.get("lands_on", []) if lo.get("pin") in moved_landings}
    unlanded = sorted(p for p in moved_landings if p not in landed)
    bad = [p for p in unlanded if p.split(".", 1)[1] not in fwd]
    if bad or nl != len(landed):
        raise SystemExit(f"{TYPE}: {nl} landings for {len(landed)} landed roots; roots with neither a tap nor a "
                         f"forwarded entry: {bad[:6]}")
    return unlanded


def stage(plan_p, repo, out):
    repo, out = Path(repo), Path(out)
    G = gen(repo)
    P = json.loads(Path(plan_p).read_text())
    Q = copy.deepcopy(P)
    t = Q["partition_types"][TYPE]
    roots_doc = json.loads((repo / SPLIT).read_text())
    rec = dict(event="S81-T51-PINFIX-2 ready12b stage", plan=str(plan_p), lattice="schema.ASAP7_LAYERS M7 0.032/0.064",
               children={})
    moved_landings = {}
    for side, mod in CHILD.items():
        hc = next(c for c in t["hard_cores"] if c["module"] == mod)
        rp = roots_doc[ROOTKEY[side]]["ports"]
        rects = {k: v["rect_um"] for k, v in rp.items()}
        d, ph = derive_shift(G, hc, P, rects)
        names = set(rects)
        # 1. plan pin table
        pf = repo / S81 / hc["pins_file"]
        doc = json.loads(pf.read_text())
        n1 = 0
        for q in doc["pins"]:
            if q["name"] in names:
                assert q["layer"] == "M7" and abs(q["x"] - (rects[q["name"]][0] + rects[q["name"]][2]) / 2) < 1e-4, q
                q["x"] = r4(q["x"] + d)
                n1 += 1
        # 3b. staged contract LEF (copy of the plan LEF, root M7 rects shifted)
        lef_rel = S81 / "inputs/core_lef" / f"{mod}_m7r.lef"
        ltxt, n3l = shift_lef((repo / hc["lef"]).read_text(), names, d)
        (out / lef_rel).parent.mkdir(parents=True, exist_ok=True)
        (out / lef_rel).write_text(ltxt)
        old_ph = doc["pinhash"]
        doc["pinhash"], doc["lef"] = pinhash(doc["pins"]), str(lef_rel)
        doc["source"] += f" | S81-T51-PINFIX-2 11-12: {n1} native M7 roots {d:+.3f} um onto the die M7 lattice"
        (out / S81 / hc["pins_file"]).parent.mkdir(parents=True, exist_ok=True)
        (out / S81 / hc["pins_file"]).write_text(json.dumps(doc, indent=0) + "\n")
        # 3a. native_clock_pins spec source
        for k in names:
            r = rp[k]["rect_um"]
            rp[k]["rect_um"] = [r4(r[0] + d), r[1], r4(r[2] + d), r[3]]
        hc["lef"] = str(lef_rel)
        for k in names:
            moved_landings[f"{mod}.{k}"] = d
        rec["children"][side] = dict(module=mod, shift_um=d, core_frame_m7_phase_um=ph, roots=len(names),
                                     pins_moved=n1, lef_rects_moved=n3l, pinhash=[old_ph, doc["pinhash"]],
                                     lef=[hc_lef for hc_lef in (next(c for c in P["partition_types"][TYPE]["hard_cores"]
                                                                     if c["module"] == mod)["lef"], str(lef_rel))])
        if not (n1 == len(names) and n3l >= len(names)):
            raise SystemExit(f"{mod}: moved {n1} pins / {n3l} LEF rects for {len(names)} roots")
    # 2. parent clock taps
    nl = nt = 0
    for tp in t["clock"]["taps"]:
        old = [list(lo["xy"]) for lo in tp.get("lands_on", []) if lo.get("pin") in moved_landings]
        for lo in tp.get("lands_on", []):
            if lo.get("pin") in moved_landings:
                lo["xy"] = [r4(lo["xy"][0] + moved_landings[lo["pin"]]), lo["xy"][1]]
                nl += 1
        if old and list(tp["xy"]) in old:
            dd = next(moved_landings[lo["pin"]] for lo in tp["lands_on"] if lo.get("pin") in moved_landings)
            tp["xy"] = [r4(tp["xy"][0] + dd), tp["xy"][1]]
            nt += 1
    rec["forwarded_roots_no_tap"] = check_landings(t, moved_landings, nl)
    (out / SPLIT).parent.mkdir(parents=True, exist_ok=True)
    (out / SPLIT).write_text(json.dumps(roots_doc, indent=1) + "\n")
    (out / "plan.json").write_text(json.dumps(Q, indent=1) + "\n")
    rec.update(landings_moved=nl, tap_xy_moved=nt, follow_ups=[
        "4. superseded views: cores/views/<native_e>_signed_1109 (LEF/ETM at the source phase) and the unsigned W rc51a "
        "abstract (cores/legacy/lef/t51w_rc51a_1106): re-sign rc51e-form kits regenerated from this stage (rc51f) and "
        "publish their views; hard_cores[].lef/lib then point at the new signed views instead of inputs/core_lef/*_m7r.lef",
        "5. parent: slice_station__t51 type kit io / child abstracts and the die bind regenerate from the staged plan "
        "(landing contract / edge_clocks are parent-edge pins, unchanged)"])
    (out / "receipt.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def _find(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                yield v
            yield from _find(v, key)
    elif isinstance(o, list):
        for v in o:
            yield from _find(v, key)


def io_blocks(text):
    """BTerm name -> its native multiPORT lines in an io.tcl"""
    out, cur = {}, None
    for line in text.split("\n"):
        m = re.match(r"set ot_mp_bt \[\[ord::get_db_block\] findBTerm \{([^}]+)\}\]", line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif line.startswith("place_pin "):
            cur = None
        if cur is not None:
            out[cur].append(line)
    return out


def prove(repo, out, kits):
    """regenerate the root part of each kit from the staged inputs with the generator functions; diff vs kits"""
    repo, out = Path(repo), Path(out)
    G = gen(repo)
    Q = json.loads((out / "plan.json").read_text())
    roots_doc = json.loads((out / SPLIT).read_text())
    res, ok = {}, True
    profile = json.loads((repo / PROFILE).read_text())["children"]
    for side, kd in kits.items():
        mod = CHILD[side]
        kd = Path(kd)
        hc = next(c for c in Q["partition_types"][TYPE]["hard_cores"] if c["module"] == mod)
        pins = json.loads((out / S81 / hc["pins_file"]).read_text())["pins"]
        shapes = G.lef_pin_rects(out / hc["lef"], geometry=True)
        # the real per-root window contract (tap_window_port_ps, ps per scalar root; this stage moves no window)
        # Window source: the kit's own generated table (sdc_lint.json; the recipe spec is lost).  The repo profile is
        # checked too: it must agree on every root it lists, and the roots it lacks are reported (not filled in).
        mr = {"roots": [{"base": k, "pins": [k]} for k in roots_doc[ROOTKEY[side]]["ports"]]}
        kw = next(_find(json.loads((kd / "sdc_lint.json").read_text()), "tap_window_port_ps"))
        spec = {"native_clock_pins": roots_doc[ROOTKEY[side]], "tap_window_port_ps": kw}
        windows = G.root_window_contract(spec, mr)                                                       # refuses on error
        pw = profile[ROOTKEY[side]]["tap_window_port_ps"]
        try:
            G.root_window_contract(dict(spec, tap_window_port_ps=pw), mr)
            prof_refusal = None
        except SystemExit as e:
            prof_refusal = str(e)
        prof_missing = sorted(set(windows) - set(pw))
        win_diff = sorted(k for k in pw if k not in windows or abs(float(pw[k]) - windows[k]) > 1e-9)
        nat = G.native_root_pin_contract(spec, mr, pins, shapes, hc["outline_um"], hc.get("obs_max"))   # refuses on error
        ph = G.native_m7_phase(nat, hc, Q)                                                               # refuses on error
        tline = next(l for l in G.kit_tracks(None, ph).splitlines() if l.startswith("make_tracks M7"))
        kline = next(l for l in (kd / "make_tracks.tcl").read_text().splitlines() if l.startswith("make_tracks M7"))
        tr_ok = tline.split(";#")[0].split() == kline.split(";#")[0].split()
        kio = io_blocks((kd / "io.tcl").read_text())
        krow = {q["bus"] if q["bit"] is None else f"{q['bus']}[{q['bit']}]": q for q in json.loads((kd / "pins.json").read_text())}
        byname = {q["name"]: q for q in pins}
        io_diff, row_diff = [], []
        for k, rect in nat.items():
            if G.native_multiport_tcl(k, [rect]) != kio.get(k):
                io_diff.append(k)
            q = byname[k]
            want = dict(bus=k, bit=None, layer="M7", x=round(q["x"], 4), y=round(q["y"], 4), face="C", native_rects=[rect])
            if krow.get(k) != want:
                row_diff.append((k, want, krow.get(k)))
        res[side] = dict(roots=len(nat), root_windows=len(windows), root_window_ps_range=[min(windows.values()),
                         max(windows.values())], repo_profile_value_diff=win_diff,
                         repo_profile_missing_roots={k: windows[k] for k in prof_missing},
                         repo_profile_refusal=prof_refusal, m7_phase=ph, make_tracks_generated=tline, make_tracks_kit=kline,
                         make_tracks_equal_ignoring_comment=tr_ok, io_blocks_equal=len(nat) - len(io_diff),
                         io_diff=io_diff, pins_rows_equal=len(nat) - len(row_diff), pins_diff=row_diff[:5])
        ok &= tr_ok and not io_diff and not row_diff and not win_diff
    return ok, res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--repo", default=str(REPO_DEFAULT))
    ap.add_argument("--out", required=True)
    ap.add_argument("--prove-kit", action="append", default=[], help="SIDE=KITDIR (side e or w)")
    a = ap.parse_args(argv)
    rec = stage(a.plan, a.repo, a.out)
    print(json.dumps({k: v for k, v in rec.items() if k != "follow_ups"}, indent=1))
    if a.prove_kit:
        ok, res = prove(a.repo, a.out, dict(s.split("=", 1) for s in a.prove_kit))
        rec["proof"] = res
        (Path(a.out) / "receipt.json").write_text(json.dumps(rec, indent=1) + "\n")
        print(json.dumps(res, indent=1))
        print("PROVE", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
