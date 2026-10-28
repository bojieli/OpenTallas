#!/usr/bin/env python3
"""CORELAT-SQ-1 (COORD 10-28 02:59 RISK-SWEEP-1 ruling): early core-tap table per hard-core module of a die plan.

For every hard-core MODULE placed in PLAN (partition count > 0):
  1. placed-view identity: the plan lib, else the views/<mod>/ dir that holds the plan LEF, else every repo view
     candidate whose LEF matches the plan LEF (SIZE + pin-name set); no guessing by module name;
  2. insertion: main tools/die_plan/core_clock_contract.load (clock_contract.json > SIGNED signoff.json > routed-SPEF
     insertion.json boundary-register MEAN, never the ETM max) on the identified view, plus boundary min/max;
     SIGNED records outside the repo (autopilot closed archives, --signed) are listed with their LEF identity vs
     the placed LEF, and win only if they MATCH (else they are a re-bind candidate, not the placed view);
  3. tap: early core tap iff TT mean > common (12.3 v5.0 / early_core_taps.add_from_means rule):
     insertion_ps = TT mean, insertion_ff_ps = FF mean; budget_owner 'SIGNED ...' only for SIGNED records
     (gen_phys.signed_mean_core_taps), else 'parent_budget ...' (core_clock_contract.from_budget basis);
  4. boundary FF hold ESTIMATE (UNCHECKED model, RISK-SWEEP-1/HBM-RISK-2 form):
       comp_ff = FF clock the core's registers are aligned to (= FF mean with a mean contract/early tap);
       late = Bff_max - comp, early = comp - Bff_min;
       hold_in  = 25 - max(late, 0)  - 0.05 Bff_max   (parent -> core capture)
       hold_out = 25 - max(early, 0) - 0.05 Bff_min   (core -> parent launch)
     (+25 = 50 ps base boundary min data delay - 25 ps hold uncertainty);  *_u60 = the same with 60 ps
     uncertainty (= value - 35), INFO.
usage: corelat_table.py PLAN ROOT OUT_PREFIX [--signed SIGNED.json] [--extra EXTRA.json] [--common 250 --common-ff 202.5]
"""
import argparse, collections, glob, hashlib, json, os, re, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("root"); ap.add_argument("out")
ap.add_argument("--signed", help="json {module: [{label, signoff, lef}]} SIGNED records outside the repo")
ap.add_argument("--extra", help="json {module: {label, tt:{mean,min,max}, ff:{...}, checked, note}} non-view numbers (CTS/ETM/model)")
ap.add_argument("--bind-signed", action="store_true", help="plan binds no LEF/lib: the SIGNED record is the view to bind (die-owner ruling)")
ap.add_argument("--band", type=float, default=20.0, help="12.3 common latency band: early tap only if TT mean > common + band")
ap.add_argument("--common", type=float, default=250.0); ap.add_argument("--common-ff", type=float, default=202.5)
a = ap.parse_args()
ROOT = Path(a.root)
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import core_clock_contract as CC  # noqa: E402
import cores as C  # noqa: E402

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12] if p and Path(p).is_file() else None

def lef_sig(path, mod):
    if not path or not Path(path).is_file():
        return None
    txt = Path(path).read_text(errors="replace")
    m = re.search(r"MACRO\s+%s\b(.*?)END\s+%s\b" % (re.escape(mod), re.escape(mod)), txt, re.S)
    body = m.group(1) if m else txt
    s = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", body)
    pins, cur, pw = set(), None, False
    for ln in body.splitlines():
        w = ln.split()
        if not w:
            continue
        if w[0] == "PIN" and len(w) > 1 and cur is None:
            cur, pw = w[1], False
        elif cur is not None and w[0] == "USE" and len(w) > 1 and w[1].rstrip(";") in ("POWER", "GROUND"):
            pw = True
        elif cur is not None and w[0] == "END" and len(w) > 1 and w[1] == cur:
            if not pw and cur.upper() not in ("VDD", "VSS"):
                pins.add(cur)
            cur = None
    pins = sorted(pins)
    return dict(size=(round(float(s.group(1)), 3), round(float(s.group(2)), 3)) if s else None, npins=len(pins),
                pins_sha=hashlib.sha256("\n".join(pins).encode()).hexdigest()[:10])

def same(s1, s2):
    return bool(s1 and s2 and s1["size"] == s2["size"] and s1["pins_sha"] == s2["pins_sha"])

def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(p)

def boundary_stats(libdir):
    """insertion.json boundary n/mean/min/max per corner (+ 'all' spread)."""
    f = Path(libdir) / "insertion.json"
    if not f.is_file():
        return None
    r = json.loads(f.read_text()); out = {}
    for c in ("tt", "ff"):
        bd = (r.get(c) or {}).get("boundary") or {}; al = (r.get(c) or {}).get("all") or {}
        if bd.get("n"):
            out[c] = dict(n=bd["n"], mean=bd["mean"], min=bd["min"], max=bd["max"])
        if al.get("n"):
            out[c + "_all_spread"] = round(al["max"] - al["min"], 1)
    out["raw_source"] = r.get("raw_source"); out["parasitics"] = r.get("parasitics")
    return out

def signoff_stats(f):
    s = json.loads(Path(f).read_text()); out = dict(verdict=s.get("verdict"))
    for c in ("tt", "ff"):
        it = s.get("corners", {}).get(c, {}); ip = it.get("insertion_pinflops") or {}
        out[c] = dict(n=ip.get("n"), mean=ip.get("mean_ps", ip.get("mean")), min=ip.get("min_ps", ip.get("min")),
                      max=ip.get("max_ps", ip.get("max")), design=it.get("design"), parasitics=it.get("parasitics"),
                      clock_ports=it.get("clock_ports"))
    return out

CANDS = None
def candidates(mod):
    global CANDS
    if CANDS is None:
        CANDS = collections.defaultdict(list)
        for pat in ("physical/ref_tile/*/views/*/*.lef", "physical/s81_die_views/*/*/*.lef", "physical/qc_die_views/*/*/*.lef"):
            for f in glob.glob(str(ROOT / pat)):
                m = Path(f).parent.name
                if Path(f).name == m + ".lef":
                    CANDS[m].append(f)
    return sorted(CANDS.get(mod, []))

p = json.load(open(a.plan))
cnt = collections.Counter(x["type"] for x in p["partitions"])
mods = collections.OrderedDict()
for tn, t in p["partition_types"].items():
    if not cnt[tn]:
        continue
    for h in t.get("hard_cores", []) or []:
        m = mods.setdefault(h["module"], dict(n=0, types=set(), lefs=set(), libs=set(), insts=[]))
        m["n"] += cnt[tn]; m["types"].add(tn); m["lefs"].add(h.get("lef")); m["libs"].add(h.get("lib"))
        m["insts"].append((tn, h["inst"], cnt[tn]))
signed = json.load(open(a.signed)) if a.signed else {}
extra = json.load(open(a.extra)) if a.extra else {}

rows = []
for mod, m in sorted(mods.items(), key=lambda kv: -kv[1]["n"]):
    r = dict(module=mod, placements=m["n"], types=len(m["types"]), plan_lef=sorted(map(str, m["lefs"])),
             plan_lib=sorted(map(str, m["libs"])))
    plef = next((l for l in m["lefs"] if l), None)
    plef_abs = C.resolve(plef, ROOT) if plef else None
    psig = lef_sig(plef_abs, mod)
    r["plan_lef_sig"] = psig
    lib = next((l for l in m["libs"] if l), None); ident = None
    if lib:
        ident = "plan_lib"
    elif plef_abs and (plef_abs.parent / f"{mod}_tt.lib").is_file():
        lib = rel(plef_abs.parent / f"{mod}_tt.lib"); ident = "plan_lef_view_dir"
    else:
        match = [c for c in candidates(mod) if same(lef_sig(c, mod), psig) and (Path(c).parent / f"{mod}_tt.lib").is_file()]
        r["lef_candidates"] = [dict(lef=rel(c), sig=lef_sig(c, mod), match=same(lef_sig(c, mod), psig)) for c in candidates(mod)]
        if len(match) == 1:
            lib = rel(Path(match[0]).parent / f"{mod}_tt.lib"); ident = "lef_match_unique"
        elif len(match) > 1:
            lib = rel(Path(sorted(match, key=os.path.getmtime)[-1]).parent / f"{mod}_tt.lib"); ident = f"lef_match_{len(match)}_newest"
        else:
            ident = "NO_MATCHING_VIEW"
            for cd in r["lef_candidates"]:
                cl = Path(ROOT / cd["lef"]).parent / f"{mod}_tt.lib"
                if cl.is_file():
                    try:
                        v = sorted(CC.load(dict(inst="u", module=mod, lib=rel(cl)), ROOT, require_signed=False).items())[0][1]
                        cd["numbers_if_rebound"] = dict(tt=v["corners"]["tt"]["mean_ps"], ff=v["corners"]["ff"]["mean_ps"])
                    except Exception as e:  # noqa: BLE001
                        bsx = boundary_stats(cl.parent) or {}
                        cd["numbers_if_rebound"] = dict(tt=(bsx.get("tt") or {}).get("mean"), ff=(bsx.get("ff") or {}).get("mean"),
                                                        note="direct insertion.json; " + str(e)[-80:])
    r.update(view_lib=lib, identity=ident, view_lib_sha=sha(C.resolve(lib, ROOT)) if lib else None)
    meas = None; per_pin = None
    if lib:
        core = dict(inst="u", module=mod, lib=lib, lef=plef)
        try:
            ld = CC.load(core, ROOT, require_signed=False)
            pin, v = sorted(ld.items())[0]
            if len(ld) > 1:
                ins = json.loads((C.resolve(lib, ROOT).parent / "insertion.json").read_text()) \
                    if (C.resolve(lib, ROOT).parent / "insertion.json").is_file() else {}
                pp = []
                for pn, pv in sorted(ld.items()):
                    cm = ins.get("clock_measurements", {}).get(pn, {})
                    st = {c: dict((cm.get(c) or {}).get("boundary") or {}, mean=pv["corners"][c]["mean_ps"]) for c in ("tt", "ff")}
                    al = (cm.get("tt") or {}).get("all") or {}
                    pp.append(dict(pin=pn, tt=st["tt"], ff=st["ff"], basis=pv["corners"]["tt"]["basis"],
                                   spread_tt_all=round(al["max"] - al["min"], 1) if al.get("n") else None))
                per_pin = pp
            meas = dict(pins=sorted(ld), tt_mean=v["corners"]["tt"]["mean_ps"], ff_mean=v["corners"]["ff"]["mean_ps"],
                        basis=v["corners"]["tt"]["basis"], signed=v["signed"], contract_source=rel(v["contract_source"]),
                        n=v["corners"]["tt"]["n"])
        except Exception as e:  # noqa: BLE001
            meas = dict(error=str(e)[:200])
        bs = boundary_stats(C.resolve(lib, ROOT).parent)
        if bs and meas.get("error") and bs.get("tt") and bs.get("ff") and bs.get("parasitics") == "spef":
            # main CC.load refuses (no explicit clock-pin mapping); the routed-SPEF boundary census itself is read directly
            meas.update(tt_mean=bs["tt"]["mean"], ff_mean=bs["ff"]["mean"], basis="pin_register_mean(direct insertion.json "
                        "boundary; main CC.load refused: " + meas["error"].split(": ")[-1] + ")", signed=False,
                        contract_source=rel(C.resolve(lib, ROOT).parent / "insertion.json"), n=bs["tt"]["n"], direct=True,
                        raw_source_flag=bs.get("raw_source"))
        if bs:
            meas["boundary"] = bs
    r["view_measure"] = meas
    sr = []
    for rec in signed.get(mod, []):
        st = signoff_stats(rec["signoff"]); ssig = lef_sig(rec.get("lef"), mod) if rec.get("lef") else None
        sr.append(dict(label=rec["label"], signoff=rec["signoff"], verdict=st["verdict"], tt=st["tt"], ff=st["ff"],
                       lef=rec.get("lef"), lef_sig=ssig,
                       lef_match_placed=(same(ssig, psig) if ssig else None)))
    r["signed_records"] = sr
    # ---- choose the number ----
    src = None; tt = ff = None; checked = "UNCHECKED"
    match_signed = [s for s in sr if s["verdict"] == "SIGNED" and (s["lef_match_placed"] or (a.bind_signed and psig is None))]
    if match_signed:
        s = match_signed[0]; tt, ff = s["tt"], s["ff"]; src = f"SIGNED {s['label']} {s['signoff']} insertion_pinflops"
        checked = ("CHECKED (SIGNED record, LEF identity == placed)" if s["lef_match_placed"] else
                   "CHECKED read (SIGNED record; plan binds no view -> this is the view to BIND)")
    elif meas and meas.get("tt_mean") is not None:
        b = meas.get("boundary") or {}
        tt = dict(b.get("tt", {}), mean=meas["tt_mean"]); ff = dict(b.get("ff", {}), mean=meas["ff_mean"])
        if not b.get("tt"):  # SIGNED/contract without insertion.json: min/max from the record only
            tt.setdefault("min", None); tt.setdefault("max", None)
        src = f"{'SIGNED' if meas['signed'] else 'parent_budget'} {meas['basis']} {meas['contract_source']}"
        checked = ("CHECKED read (direct insertion.json; main loader refuses it)" if meas.get("direct") else
                   "CHECKED (main core_clock_contract.load on the placed view)") if ident in ("plan_lib", "plan_lef_view_dir", "lef_match_unique") \
            else f"UNCHECKED (view identity {ident})"
    if mod in extra:
        e = extra[mod]
        if tt is None or e.get("override"):
            tt, ff, src, checked = e["tt"], e["ff"], e["label"], e.get("checked", "UNCHECKED")
        r["extra"] = e
    if tt is None and r["signed_records"]:
        s = r["signed_records"][0]
        r["rebind_candidate"] = f"{s['label']} TT {s['tt']['mean']} FF {s['ff']['mean']} (LEF != placed)"
    r.update(source=src, label=checked, tt=tt, ff=ff)
    def taphold(tt, ff, src):
        o = {}
        early_on = tt["mean"] > a.common + a.band
        o["tap"] = dict(early=early_on, within_band=(not early_on and tt["mean"] > a.common), insertion_ps=round(tt["mean"], 2), insertion_ff_ps=round(ff["mean"], 2),
                        early_tt_ps=round(max(0.0, tt["mean"] - a.common), 1) if early_on else 0.0,
                        early_ff_ps=round(max(0.0, ff["mean"] - a.common_ff), 1) if early_on else 0.0,
                        budget_owner=("SIGNED " if src.startswith("SIGNED") else "parent_budget ") + src.split(" ", 1)[1])
        if ff.get("min") is not None and ff.get("max") is not None:
            comp = ff["mean"] if early_on else min(ff["mean"], a.common_ff); late = ff["max"] - comp; early = comp - ff["min"]
            hi = round(25 - max(late, 0) - 0.05 * ff["max"], 1); ho = round(25 - max(early, 0) - 0.05 * ff["min"], 1)
            o["hold_est"] = dict(comp_ff=round(comp, 1), late=round(late, 1), early=round(early, 1), hold_in=hi, hold_out=ho,
                                 hold_in_u60=round(hi - 35, 1), hold_out_u60=round(ho - 35, 1),
                                 verdict="PASS" if min(hi, ho) >= 0 else "FAIL", label="UNCHECKED model")
        return o
    if per_pin and src and not src.startswith("SIGNED"):
        for q in per_pin:
            q.update(taphold(q["tt"], q["ff"], src))
        r["per_pin"] = per_pin
        r["label"] = checked + f"; {len(per_pin)} clock pins -> one early tap PER PIN"
    if tt and tt.get("mean") is not None:
        r.update(taphold(tt, ff, src))
        if r.get("per_pin"):  # multi-root core: the per-pin rows ARE the table; module row = worst pin
            hs = [q["hold_est"] for q in r["per_pin"] if q.get("hold_est")]
            r["tap"] = None; r["tt"] = r["ff"] = {"mean": "per-pin"}
            r["hold_est"] = dict(hold_in=min(h["hold_in"] for h in hs), hold_out=min(h["hold_out"] for h in hs),
                                 hold_in_u60=min(h["hold_in_u60"] for h in hs), hold_out_u60=min(h["hold_out_u60"] for h in hs),
                                 verdict="PASS" if min(min(h["hold_in"], h["hold_out"]) for h in hs) >= 0 else "FAIL",
                                 label="UNCHECKED model, worst pin") if hs else None
        r["spread_tt_all"] = (meas or {}).get("boundary", {}).get("tt_all_spread") if meas else None
    rows.append(r)

json.dump(dict(plan=a.plan, plan_sha=hashlib.sha256(open(a.plan, "rb").read()).hexdigest()[:12],
               common_tt=a.common, common_ff=a.common_ff, rows=rows), open(a.out + ".json", "w"), indent=1, default=list)
with open(a.out + ".tsv", "w") as f:
    f.write("module\tplacements\tidentity\tsource\tlabel\tTT_mean\tTT_min\tTT_max\tFF_mean\tFF_min\tFF_max\tearly_TT\tearly_FF\t"
            "hold_in\thold_out\thold_in_u60\thold_out_u60\tspread_TT_all\tview_lib\n")
    for r in rows:
        t = r.get("tt") or {}; fdat = r.get("ff") or {}; tp = r.get("tap") or {}; h = r.get("hold_est") or {}
        f.write("\t".join(str(x) for x in (r["module"], r["placements"], r["identity"], r["source"], r["label"],
                t.get("mean"), t.get("min"), t.get("max"), fdat.get("mean"), fdat.get("min"), fdat.get("max"),
                tp.get("early_tt_ps"), tp.get("early_ff_ps"), h.get("hold_in"), h.get("hold_out"), h.get("hold_in_u60"),
                h.get("hold_out_u60"), r.get("spread_tt_all"), r.get("view_lib"))) + "\n")
        for q in r.get("per_pin") or []:
            t = q["tt"]; fdat = q["ff"]; tp = q.get("tap") or {}; h = q.get("hold_est") or {}
            f.write("\t".join(str(x) for x in (r["module"] + ":" + q["pin"], r["placements"], r["identity"], q["basis"], "per-pin",
                    t.get("mean"), t.get("min"), t.get("max"), fdat.get("mean"), fdat.get("min"), fdat.get("max"),
                    tp.get("early_tt_ps"), tp.get("early_ff_ps"), h.get("hold_in"), h.get("hold_out"), h.get("hold_in_u60"),
                    h.get("hold_out_u60"), q.get("spread_tt_all"), r.get("view_lib"))) + "\n")
print(a.out, len(rows), "modules")
