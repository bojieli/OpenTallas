#!/usr/bin/env python3
"""Flow canary regression verdict vs a recorded per-reference BASELINE (COORD CANARY GATING RULING 2026-10-25 14:38).

A flow canary detects FLOW REGRESSIONS.  It gates on the reference partition's result vs its recorded baseline (same
die + item), never on an absolute PASS of the reference design: absolute failures of a reference (s81 t12 / KV io_ft
insertion 226-229 vs 250, QC coll_ftm FF hold -136, HBM TKM taps 522) are DESIGN items owned by their lanes.

Metrics, each in the context it was measured in (a GRT-context number is never compared with a routed one):
  grt     ins_tt / ins_ff      post-CTS gate pin-register mean insertion (postcts_gate_{tt,ff}.json), with its bound
          hold_ff_wns / _ep    OT_HOLD_GATE FF WNS + failing endpoints
          overflow             5_1_grt.log final congestion report, total overflow
          drv                  5_1_grt.json max slew + max cap violation counts
  signoff setup_tt_wns, hold_ff_wns / hold_ff_ep, ins_tt / ins_ff (routed pin-register mean + bound), drv (slew + cap)
Tolerances (ruling): insertion 5 ps (distance from the bound when both runs have one, else absolute change), WNS 10 ps,
hold failing endpoints +5 %, overflow 0 new, DRV 0 new.  Flow-correctness stages (lint, LEC, face cover, rc file,
tcl errors ...) that PASSed in the baseline run must still PASS.  A run that reaches less than the baseline (no GRT /
no sign-off) is a REGRESSION unless it stopped at the flow's own design gate (post-CTS insertion gate or structural
hold gate) with that gate's metrics within tolerance: then the later metrics are NOT REACHED (design stop) and listed.

Verdicts: NO-REGRESSION, REGRESSION, INFO (this run set the baseline; non-gating), NO-BASELINE (no baseline and this run
cannot set one: Tcl crash or no metric at all; it holds rows).

Baseline store: <canary runs root>/baselines/<die>__<item>.json, written once (atomic create); a reference with no
baseline sets it from its first usable completed run (INFO).  Source preference, recorded per context:
'canary-passed-main' (an absolute canary PASS on main), else 'reference-run' (the golden record's sign-off run, sign-off
context) and 'canary-run-info' (the first completed run, GRT context).  Re-baseline only by hand after a reviewed
design change:  baseline.py set --root R --run RUN [--signoff-ref signoff.json --signoff-ref-kind reference-run] --force
"""
import argparse
import glob
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

SCHEMA = "opentallas.flow_canary.baseline.v1"
TOL = {"ins_ps": 5.0, "wns_ps": 10.0, "hold_ep_frac": 0.05, "overflow": 0, "drv": 0}
# stages whose PASS/FAIL is a flow-correctness fact; grt_gate / route / rcx / signoff / vclk_basis are design results or
# reach, judged through the metrics
FLOW_STAGES = ("lint", "sdc_lint", "selrange", "synth", "lec", "face_guard", "face_cover", "reg_fanout", "rc_file",
               "cts", "tcl_errors")
HOLD_RE = re.compile(r"^OT_HOLD_GATE\s+(PASS|FAIL)\s+FF\s+wns_ps\s+(-?[0-9.]+)\s+endpoints\s+(\d+)", re.M)
GATE_RE = re.compile(r"^OT_POSTCTS_GATE\s+(TT|FF)\b.*?\bmean\s+(-?[0-9.]+)\s+bound\s+(-?[0-9.]+).*?\b(PASS|FAIL)\s*$",
                     re.M)
OVF_RE = re.compile(r"^Total\s+\d+\s+\d+\s+[0-9.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", re.M)


def jload(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def read(p):
    try:
        return Path(p).read_text(errors="replace")
    except Exception:
        return ""


def _num(v):
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _first(pattern):
    g = sorted(glob.glob(pattern))
    return g[-1] if g else None


# ---------------------------------------------------------------------------------------------------------- metrics
def signoff_metrics(so):
    """sign-off context metrics from a signoff.json (opentallas.signoff.v1)"""
    if not so:
        return {}
    c = so.get("checks") or {}
    cor = so.get("corners") or {}
    pol = so.get("policy") or {}
    m = {}
    s, h = (c.get("setup_tt") or {}), (c.get("hold_ff") or {})
    if _num(s.get("wns_ps")) is not None:
        m["setup_tt_wns"] = _num(s.get("wns_ps"))
    if _num(h.get("wns_ps")) is not None:
        m["hold_ff_wns"] = _num(h.get("wns_ps"))
        ep = _num(h.get("violators"))
        if ep is None:
            ep = _num((cor.get("ff") or {}).get("sdc_nviol_min"))
        if ep is not None:
            m["hold_ff_ep"] = ep
    bound = pol.get("insertion_bound") or {}
    target = _num((c.get("clock") or {}).get("insertion_target_ps"))
    for k in ("tt", "ff"):
        mean = _num(((cor.get(k) or {}).get("insertion_pinflops") or {}).get("mean"))
        if mean is not None:
            m["ins_" + k] = mean
            b = _num(bound.get(k))
            if b is None and k == "tt":
                b = target
            if b is not None:
                m["ins_" + k + "_bound"] = b
    drv = (c.get("drv") or {}).get("by_corner")
    if isinstance(drv, dict) and drv:
        m["drv"] = sum((_num(v.get("slew")) or 0) + (_num(v.get("cap")) or 0) for v in drv.values() if isinstance(v, dict))
    return m


def grt_metrics(kit):
    kit = Path(kit)
    m = {}
    for k in ("tt", "ff"):
        g = jload(kit / f"postcts_gate_{k}.json")
        if g and _num(g.get("pinreg_mean_ps")) is not None:
            m["ins_" + k] = _num(g["pinreg_mean_ps"])
            if _num(g.get("bound_ps")) is not None:
                m["ins_" + k + "_bound"] = _num(g["bound_ps"])
    if "ins_tt" not in m and "ins_ff" not in m:
        for c, mean, bound, _v in GATE_RE.findall(read(kit / "postcts_gate_TT.log") + "\n" + read(kit / "postcts_gate_FF.log")):
            m["ins_" + c.lower()] = float(mean)
            m["ins_" + c.lower() + "_bound"] = float(bound)
    hg = HOLD_RE.findall(read(kit / "hold_gate.log"))
    if hg:
        m["hold_ff_wns"], m["hold_ff_ep"] = float(hg[-1][1]), float(hg[-1][2])
    log = _first(f"{kit}/run/logs/asap7/*/base/5_1_grt.log")
    if log:
        txt = read(log)
        i = txt.rfind("Final congestion report")
        o = OVF_RE.findall(txt[i:] if i >= 0 else txt)
        if o:
            m["overflow"] = float(o[0][2])
    gj = jload(_first(f"{kit}/run/logs/asap7/*/base/5_1_grt.json") or "/nonexistent")
    if gj and any(k in gj for k in ("globalroute__timing__drv__max_slew", "globalroute__timing__drv__max_cap")):
        m["drv"] = (_num(gj.get("globalroute__timing__drv__max_slew")) or 0) + (_num(gj.get("globalroute__timing__drv__max_cap")) or 0)
    return m


def design_stop(kit):
    """the flow stopped itself at a design gate (not a crash): post-CTS insertion gate FAIL or structural hold gate"""
    kit = Path(kit)
    why = []
    if (kit / "FAIL_POSTCTS").is_file():
        why.append("post-CTS insertion gate (FAIL_POSTCTS)")
    hg = HOLD_RE.findall(read(kit / "hold_gate.log"))
    if hg and hg[-1][0] == "FAIL":
        why.append("structural FF hold gate")
    return "; ".join(why)


def run_metrics(run):
    """metrics of one canary run dir (reads the kit files, so it also works for canary.json written before metrics)"""
    run = Path(run)
    meta = jload(run / "canary_meta.json") or {}
    res = jload(run / "canary.json") or {}
    kit = Path(meta.get("kit") or res.get("kit") or (run / "kit"))
    spec = meta.get("spec") or {}
    sop = sorted(glob.glob(f"{kit}/signoff*/signoff.json"), key=os.path.getmtime)
    so = jload(sop[-1]) if sop else None
    stages = {k: (v or {}).get("verdict") for k, v in (res.get("stages") or {}).items()}
    return dict(run=str(run), die=spec.get("die") or res.get("die"), item=spec.get("item") or res.get("item"),
                src=meta.get("src_commit") or res.get("src"), verdict=res.get("verdict"),
                contexts={"grt": grt_metrics(kit), "signoff": signoff_metrics(so)}, stages=stages,
                design_stop=design_stop(kit), signoff_path=sop[-1] if sop else None)


# ------------------------------------------------------------------------------------------------------- comparison
def _cmp(ctx, key, b, c, bm, cm):
    """one metric row: verdict REGRESSED / OK"""
    if key in ("ins_tt", "ins_ff"):
        bb, cb = bm.get(key + "_bound"), cm.get(key + "_bound")
        if bb is not None and cb is not None:
            worse = abs(c - cb) - abs(b - bb)
            how = f"|ins-bound| {abs(b - bb):.2f} -> {abs(c - cb):.2f} (tol {TOL['ins_ps']:g})"
        else:
            worse = abs(c - b)
            how = f"change {c - b:+.2f} (tol {TOL['ins_ps']:g}, no bound)"
        bad = worse > TOL["ins_ps"]
    elif key.endswith("_wns"):
        bad = c < b - TOL["wns_ps"]
        how = f"{c - b:+.2f} ps (tol -{TOL['wns_ps']:g})"
    elif key == "hold_ff_ep":
        bad = c > b * (1 + TOL["hold_ep_frac"])
        how = f"{c:g} vs {b:g} (tol +{TOL['hold_ep_frac'] * 100:g} %)"
    else:  # overflow, drv: 0 new
        bad = c > b
        how = f"{c:g} vs {b:g} (0 new)"
    return dict(ctx=ctx, metric=key, base=b, cur=c, verdict="REGRESSED" if bad else "OK", how=how)


def compare(base, cur):
    """(verdict, rows, notes): verdict NO-REGRESSION / REGRESSION of run metrics `cur` vs baseline `base`"""
    rows, notes, bad = [], [], []
    stop = cur.get("design_stop") or ""
    compared = 0
    for ctx in ("grt", "signoff"):
        bm = (base.get("contexts") or {}).get(ctx) or {}
        cm = (cur.get("contexts") or {}).get(ctx) or {}
        keys = [k for k in bm if not k.endswith("_bound") and k not in ("from", "src", "run", "kind", "path")]
        for k in keys:
            if bm.get(k) is None:
                continue
            if cm.get(k) is None:
                if stop:      # the flow stopped itself at a design gate; judged by the gate's own metrics below
                    rows.append(dict(ctx=ctx, metric=k, base=bm[k], cur=None, verdict="NOT REACHED",
                                     how="design stop: " + stop))
                else:
                    r = dict(ctx=ctx, metric=k, base=bm[k], cur=None, verdict="REGRESSED",
                             how="not measured; the baseline run measured it")
                    rows.append(r)
                    bad.append(r)
                continue
            r = _cmp(ctx, k, float(bm[k]), float(cm[k]), bm, cm)
            compared += 1
            rows.append(r)
            if r["verdict"] == "REGRESSED":
                bad.append(r)
    for s in FLOW_STAGES:
        b, c = (base.get("stages") or {}).get(s), (cur.get("stages") or {}).get(s)
        if b == "PASS" and c not in (None, "PASS"):
            r = dict(ctx="stage", metric=s, base=b, cur=c, verdict="REGRESSED", how="flow stage PASSed in the baseline run")
            rows.append(r)
            bad.append(r)
    if not compared and not bad:
        has_base = any((base.get("contexts") or {}).get(x) for x in ("grt", "signoff"))
        if has_base:
            bad.append(dict(ctx="-", metric="-", verdict="REGRESSED", how="no metric comparable with the baseline"))
            rows.append(bad[-1])
        elif cur.get("verdict") != "PASS":
            bad.append(dict(ctx="-", metric="-", verdict="REGRESSED",
                            how="baseline holds no metrics and this run is no absolute PASS: nothing to compare"))
            rows.append(bad[-1])
    if stop:
        notes.append("design stop: " + stop + " (a DESIGN item of the reference's lane, not a flow regression)")
    return ("REGRESSION" if bad else "NO-REGRESSION"), rows, notes


# ----------------------------------------------------------------------------------------------------------- store
def _safe(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(s or "none"))


def store_path(root, die, item):
    return Path(root) / "baselines" / f"{_safe(die)}__{_safe(item)}.json"


def load(root, die, item):
    return jload(store_path(root, die, item))


def write(root, rec, force=False):
    """atomic create (never overwrites unless force); returns (written, record now on disk)"""
    p = store_path(root, rec["die"], rec["item"])
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".tmp_")
    os.fchmod(fd, 0o644)
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(rec, indent=1) + "\n")
    try:
        if force:
            os.replace(tmp, p)
            return True, rec
        try:
            os.link(tmp, p)
            return True, rec
        except FileExistsError:
            return False, jload(p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def usable(m):
    """can this completed run set a baseline?  never a Tcl crash; it needs a metric or an absolute canary PASS"""
    if (m.get("stages") or {}).get("tcl_errors") == "FAIL":
        return False, "Tcl errors (flow crash)"
    if any((m.get("contexts") or {}).get(c) for c in ("grt", "signoff")) or m.get("verdict") == "PASS":
        return True, ""
    return False, "no metric measured (flow stopped before GRT)"


def make_record(m, kind, note="", signoff_ref=None, signoff_kind=None):
    ctx = {}
    for c in ("grt", "signoff"):
        v = dict((m.get("contexts") or {}).get(c) or {})
        if v:
            v["from"] = dict(kind=kind, run=m.get("run"), src=m.get("src"))
        ctx[c] = v
    # the reference run's sign-off record replaces the run's own (preference: canary-passed main > reference run >
    # first run); never for an absolute canary PASS
    if signoff_ref is not None and kind != "canary-passed-main":
        v = signoff_metrics(signoff_ref.get("so"))
        if v:
            v["from"] = dict(kind=signoff_kind or "reference-run", path=signoff_ref.get("path"))
            ctx["signoff"] = v
    return dict(schema=SCHEMA, die=m.get("die"), item=m.get("item"), set_at=time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                source=dict(kind=kind, run=m.get("run"), src=m.get("src"), note=note), verdict=m.get("verdict"),
                contexts=ctx, stages={k: v for k, v in (m.get("stages") or {}).items() if k in FLOW_STAGES},
                tolerances=TOL)


def golden_ref(spec):
    """the reference run's sign-off record named by the spec golden (local path part of 'source', or inputs copy)"""
    g = (spec or {}).get("golden") or {}
    cands = []
    for tok in re.findall(r"(/srv/\S+?signoff\.json|/srv/\S+?\.json)", g.get("source") or ""):
        cands.append(tok)
    inputs = ((spec or {}).get("vars") or {}).get("inputs")
    if inputs:
        cands.append(str(Path(inputs) / "golden_signoff.json"))
    for p in cands:
        so = jload(p)
        if so and (so.get("checks") or {}):
            return dict(so=so, path=p)
    if g.get("setup_tt_wns") is not None or g.get("hold_ff_wns") is not None:
        checks = {}
        if g.get("setup_tt_wns") is not None:
            checks["setup_tt"] = {"wns_ps": g["setup_tt_wns"]}
        if g.get("hold_ff_wns") is not None:
            checks["hold_ff"] = {"wns_ps": g["hold_ff_wns"]}
        return dict(so={"checks": checks}, path="canaries.json golden (" + (g.get("source") or "")[:120] + ")")
    return None


def verdict(run, root, spec=None, seed=True):
    """regression verdict of one COMPLETED canary run: dict(verdict, why, rows, notes, baseline)"""
    m = run_metrics(run)
    die, item = m["die"], m["item"]
    base = load(root, die, item)
    if base is None:
        ok, why = usable(m)
        if not ok:
            return dict(verdict="NO-BASELINE", why=f"no baseline for {die}/{item} and this run cannot set one: {why}",
                        rows=[], notes=[], baseline=None, metrics=m)
        if m.get("verdict") == "PASS":
            rec = make_record(m, "canary-passed-main", "first completed run of the reference is an absolute canary PASS")
        else:
            rec = make_record(m, "canary-run-info", "no canary-passed main for this reference: first completed run "
                              "sets the GRT context (INFO, non-gating)",
                              signoff_ref=golden_ref(spec or (jload(Path(run) / "canary_meta.json") or {}).get("spec")),
                              signoff_kind="reference-run")
        if seed:
            _, base = write(root, rec)
        else:
            base = rec
    v, rows, notes = compare(base, m)
    bad = [r for r in rows if r["verdict"] == "REGRESSED"]
    src = base.get("source") or {}
    if bad:
        why = "; ".join(f"{r['ctx']} {r['metric']} {r.get('base')} -> {r.get('cur')} {r['how']}" for r in bad[:4])
    elif src.get("run") == m["run"]:
        # the run that set the baseline (its own contexts compare equal; a reference-run context still counts)
        v, why = "INFO", f"this run set the baseline ({src.get('kind')}{'' if seed else ', dry'}); non-gating"
    else:
        why = f"within tolerance of baseline {src.get('kind')} {src.get('run')}"
    return dict(verdict=v, why=why, rows=rows, notes=notes, baseline=base, metrics=m)


# ------------------------------------------------------------------------------------------------------------- CLI
def cmd_set(a):
    m = run_metrics(a.run)
    ref = None
    if a.signoff_ref:
        so = jload(a.signoff_ref)
        if not so:
            print(f"cannot read {a.signoff_ref}")
            return 2
        ref = dict(so=so, path=a.signoff_ref)
    rec = make_record(m, a.kind, a.note or "", signoff_ref=ref, signoff_kind=a.signoff_ref_kind)
    wrote, on_disk = write(a.root, rec, force=a.force)
    print(("BASELINE SET " if wrote else "BASELINE EXISTS (use --force) ") + str(store_path(a.root, m["die"], m["item"])))
    print(json.dumps(on_disk if not wrote else rec, indent=1)[:3000])
    return 0 if wrote else 1


def cmd_show(a):
    for p in sorted(glob.glob(f"{a.root}/baselines/*.json")):
        print(p)
        print(json.dumps(jload(p), indent=1)[:2000])
    return 0


def cmd_verdict(a):
    v = verdict(a.run, a.root, seed=not a.dry)
    print(f"CANARY_REGRESSION {v['verdict']} {a.run}: {v['why']}")
    for r in v["rows"]:
        print(f"  {r['verdict']:12s} {r['ctx']:8s} {r['metric']:14s} base {r.get('base')} cur {r.get('cur')}  {r['how']}")
    for n in v["notes"]:
        print("  note:", n)
    return 0 if v["verdict"] in ("NO-REGRESSION", "INFO") else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set")
    s.add_argument("--root", required=True)
    s.add_argument("--run", required=True)
    s.add_argument("--kind", required=True, choices=("canary-passed-main", "reference-run", "canary-run-info"))
    s.add_argument("--note")
    s.add_argument("--signoff-ref", help="reference run signoff.json: the sign-off context (replaces the run's own)")
    s.add_argument("--signoff-ref-kind", default="reference-run")
    s.add_argument("--force", action="store_true")
    v = sub.add_parser("verdict")
    v.add_argument("--root", required=True)
    v.add_argument("--run", required=True)
    v.add_argument("--dry", action="store_true", help="never write a baseline")
    w = sub.add_parser("show")
    w.add_argument("--root", required=True)
    a = ap.parse_args(argv)
    return dict(set=cmd_set, verdict=cmd_verdict, show=cmd_show)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
