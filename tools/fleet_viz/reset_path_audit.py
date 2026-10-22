#!/usr/bin/env python3
"""RESET-PATH AUDIT (ROOT-RST 2026-10-19): every current-die element (Qwen compute, Qwen KV/system, S81, HBM) whose
worst NATIVE CAPTURE pin or worst routed SETUP path starts at a reset input.

Tile after tile failed because rst_n reached internal flops / hard children unregistered through a buffer tree
(qkd_hr_core_order host_rst_n capture 386.9, qkd_kvs_attn rst_n 383.3, qkd_astk_rly_296 277.4, ot_s81_kp4_dec rst_n
648 ps through 11 buffers -> TT -70).  The standard (owner: regional reset with registered relays, pin registers on every
pin): 2 registered stages at the face, then equal-depth fan-out (ref_tile "reset_landing"; pre_route_gate refuses an
unlanded reset since d4c49c8d3).  This lists the elements already closed / in flight that still carry the defect.

Inputs (fleet side, read-only):
  ~/.local/state/fleet-viz/release_tree_elements_cache.json   current-die element rows (dies, die_bindable view, best job)
  ~/.local/state/fleet-viz/native_audit_cache.json            native_pin_audit records (capture_pin / capture_ps per view)
  ~/.local/state/closure_loop/jobs/<job>.json                 host + run dir of the element's best job
  <host>:<run>/routes/*/work/orfs/w18_sta_{tt,ff}.log         sign-off STA: first reported setup / hold path (ssh, batched)
Output: JSON (schema opentallas.reset_path_audit.v1) + a markdown table per die.

    reset_path_audit.py [--out results/arch/reset_path_audit_1019.json] [--md lanes/ROOT-RST_list.md] [--no-sta]
"""
import argparse
import base64
import collections
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
FV = Path(os.environ.get("FV_STATE", str(HOME / ".local/state/fleet-viz")))
CL = Path(os.environ.get("CL_STATE", str(HOME / ".local/state/closure_loop")))
DIES = {"qwen_compute": "Qwen compute", "qwen_kvsys": "Qwen KV/system", "s81": "S81 (DeepSeek ROM)", "hbm": "HBM"}
# a reset INPUT pin / port: rst / arst / prst / reset / por (+ _n / _ni / _i / _b), with any prefix (host_rst_n,
# core_rst_n, rst_n[3]); textbook_lint RST_LAND_RE spelling, prefix-tolerant
RESET_RE = re.compile(r"(^|_)(p?a?rst|reset|por)(_?n|_ni|_i|_b)?(\[\d+\])?$", re.I)
RETIRED = {"ot-epyc1tb", "ot-epyc2", "ot-epyc3", "localhost"}

STA_PROBE = r'''
import glob, json, re, sys
out = {}
for run in sys.stdin.read().split():
    r = {}
    # INF18-RST2 10-19: read the STA of the VERDICT's odb (record/route/corner_sta.json orfs_dir, e.g. cl/eco/pass2 after
    # the hold ECO, with io_ref_routed.sdc), not the pre-ECO route log -- that one gave 3 false DEFECTs (sfu_exp/rsq,
    # dsdv_bk_col) whose verdict FF input->reg was +47/+49/+24 ps.
    od = None
    try:
        od = json.load(open(run + "/record/route/corner_sta.json")).get("orfs_dir")
    except (OSError, ValueError, AttributeError):
        pass
    r["sta_dir"] = od or ""
    for c in ("tt", "ff"):
        fs = (glob.glob(od + "/w18_sta_%s.log" % c) if od else []) or glob.glob(run + "/routes/*/work/orfs/w18_sta_%s.log" % c)
        if not fs:
            continue
        try:
            t = open(fs[0], errors="replace").read(400000)
        except OSError:
            continue
        m = re.search(r"^Startpoint: (\S+)(?: \(([^)]*)\))?.*?^Endpoint: (\S+).*?^\s*(-?[\d.]+)\s+slack", t, re.S | re.M)
        if m:
            r[c] = dict(start=m.group(1), start_kind=m.group(2) or "", end=m.group(3), slack_ps=float(m.group(4)))
    out[run] = r
print(json.dumps(out))
'''


def is_reset(pin):
    return bool(pin) and bool(RESET_RE.search(str(pin).split("/")[-1]))


def load_rows():
    rt = json.loads((FV / "release_tree_elements_cache.json").read_text())
    return rt.get("generated_at"), rt["rows"]


def native_by_view():
    na = json.loads((FV / "native_audit_cache.json").read_text())["records"]
    by = collections.defaultdict(list)
    for r in na.values():
        by[r.get("view")].append(r)
    return by


def job_state(job):
    try:
        return json.loads((CL / "jobs" / f"{job}.json").read_text())
    except (OSError, ValueError):
        return None


def sta_probe(runs_by_host, timeout=300):
    """{run: {"tt": {...}, "ff": {...}}} for every reachable host (one ssh per host)"""
    out = {}
    for host, runs in sorted(runs_by_host.items()):
        if host in RETIRED or not runs:
            continue
        try:
            b64 = base64.b64encode(STA_PROBE.encode()).decode()
            p = subprocess.run(["timeout", str(timeout), "ssh", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", host,
                                f"python3 -c \"import base64; exec(base64.b64decode('{b64}'))\""],
                               input="\n".join(sorted(runs)), capture_output=True, text=True, timeout=timeout + 30)
            out.update(json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {})
        except (subprocess.SubprocessError, ValueError, IndexError) as ex:
            print(f"reset_path_audit: STA probe on {host} failed: {type(ex).__name__}", file=sys.stderr)
    return out


def audit(rows, by_view, sta=True):
    recs, runs = [], collections.defaultdict(set)
    for r in rows:
        dies = sorted({d.get("design") for d in r.get("dies") or [] if d.get("design") in DIES})
        if not dies or r.get("superseded") or str(r.get("category", "")).startswith("superseded"):
            continue
        db = r.get("die_bindable") or {}
        view = db.get("view")
        best = r.get("best") or {}
        job = best.get("job") or (r.get("latest") or {}).get("job")
        nat = by_view.get(view) or []
        # the record of the bound job when there are several trees of the view, else the worst capture
        nat = sorted(nat, key=lambda x: (x.get("job_from_view") != job, -(x.get("capture_ps") or -1e9)))
        n = nat[0] if nat else {}
        js = job_state(job) if job else None
        host, run = (js or {}).get("host"), (js or {}).get("run")
        if sta and host and run:
            runs[host].add(run)
        recs.append(dict(element=r.get("element"), dies=dies, category=r.get("category"), owner=r.get("owner_stream")
                         or r.get("owner"), view=view, job=job, job_status=(js or {}).get("status"),
                         host=host, run=run, tt_ps=best.get("tt"), ff_ps=best.get("ff"),
                         native=dict(capture_ps=n.get("capture_ps"), capture_pin=n.get("capture_pin"),
                                     capture_over=n.get("capture_over"), launch_ps=n.get("launch_ps"),
                                     launch_pin=n.get("launch_pin"), pass_=n.get("pass"), fail_why=n.get("fail_why"))
                         if n else None))
    got = sta_probe(runs) if sta else {}
    for x in recs:
        s = got.get(x["run"]) if x["run"] else None
        x["sta"] = s if s and (s.get("tt") or s.get("ff")) else None
        why = []
        nat = x["native"] or {}
        if is_reset(nat.get("capture_pin")):
            why.append(f"native worst capture {nat.get('capture_ps')} ps at {nat.get('capture_pin')}"
                       + (" (FAIL > 190)" if (nat.get("capture_ps") or 0) > 190 else ""))
        for c, label in (("tt", "setup TT"), ("ff", "hold FF")):
            p = (s or {}).get(c)
            if p and is_reset(p["start"]) and "input port" in (p.get("start_kind") or "input port"):
                why.append(f"worst {label} path starts at {p['start']} -> {p['end']} slack {p['slack_ps']:+.1f} ps")
        x["reset_findings"] = why
        x["severity"] = severity(x) if why else None
    return recs


# an endpoint that IS a landing / synchroniser / relay register (the reset reached its first register: the standard)
LANDING_RE = re.compile(r"(sync|meta|rst|reset|_rr\b|u_rr|rr\d|\brs\d|\brs_|\brs\[|\brn\$|ot_prs_|landing|rpin)", re.I)


def severity(x):
    """DEFECT: native capture > 190 ps at a reset pin, a reset-started sign-off path with negative slack, or a setup
    path from a reset port into a NON-landing endpoint with < 150 ps TT slack (an unregistered tree eating the cycle).
    WATCH: the reset is the worst path but lands in a synchroniser / relay register with margin."""
    nat = x["native"] or {}
    if is_reset(nat.get("capture_pin")) and (nat.get("capture_ps") or 0) > 190:
        return "DEFECT"
    for c in ("tt", "ff"):
        p = (x["sta"] or {}).get(c)
        if not p or not is_reset(p["start"]):
            continue
        if p["slack_ps"] < 0:
            return "DEFECT"
        if c == "tt" and p["slack_ps"] < 150 and not LANDING_RE.search(p["end"].split("/")[-1]):
            return "DEFECT"
    return "WATCH"


FAMILY = (("qwen_kvsys", re.compile(r"^(qkd|qkh|qkv|ot_qkh|ot_qkvd|ot_qwen_tp8|ot_qwen_nearhbm)")),
          ("qwen_compute", re.compile(r"^(qfd|ot_qfd|ot_qwen|ot_hdc_v(stream|reduce)|ot_hdc_sfu)")),
          ("s81", re.compile(r"^(dsfd|dsdv|ot_s81|s81|ot_dsrom|ot_engc|ot_v41)")),
          ("hbm", re.compile(r"^(hfd|ot_hbm|ot_hgi|hgi|ot_vms|ot_su12|ot_mtp|ot_hcoll|ot_attn)")))
RECENT_DAYS = 3


def family_die(cell):
    return next((d for d, rx in FAMILY if rx.search(str(cell))), None)


def other_views(by_view, recs, days=RECENT_DAYS):
    """native-audited views outside the release-tree rows (new elements not yet in a die contract, record branches)
    with a reset capture FAIL whose closing job finished in the last DAYS days (current work, not retired variants);
    die by cell family"""
    seen = {x["view"] for x in recs if x["view"]}
    cutoff = time.time() - days * 86400
    out = []
    for view, rs in by_view.items():
        if view in seen:
            continue
        for n in rs:
            if not (is_reset(n.get("capture_pin")) and (n.get("capture_ps") or 0) > 190):
                continue
            js = job_state(n.get("job_from_view")) if n.get("job_from_view") else None
            fin = (js or {}).get("finished_at") or (js or {}).get("updated")
            try:
                t = time.mktime(time.strptime(fin[:19], "%Y-%m-%dT%H:%M:%S")) if fin else 0
            except ValueError:
                t = 0
            if t < cutoff:
                continue
            out.append(dict(view=view, cell=n.get("cell"), job=n.get("job_from_view"), job_status=(js or {}).get("status"),
                            owner=((js or {}).get("spec") or {}).get("owner"), die=family_die(n.get("cell")),
                            capture_ps=n.get("capture_ps"), capture_pin=n.get("capture_pin")))
            break
    return sorted(out, key=lambda x: -x["capture_ps"])


def markdown(recs, generated, others=()):
    hit = [x for x in recs if x["reset_findings"]]
    lines = [f"# Reset-input worst paths per die (ROOT-RST reset_path_audit.py, {time.strftime('%Y-%m-%d %H:%M')}; "
             f"release-tree cache {generated})", "",
             f"{len(hit)} of {len(recs)} current-die elements have a worst native capture or worst sign-off path that "
             "starts at a reset input.  Fix: land the reset at the face in 2 registered stages (ref_tile "
             '"reset_landing": {"enable": true} or RTL rst_l0 -> rst_l1 per region), re-route, attach the '
             "native_capture receipt (native_pin_audit --view).", ""]
    for d, label in DIES.items():
        rows = [x for x in hit if d in x["dies"]]
        dfx = [x for x in rows if x["severity"] == "DEFECT"]
        wat = [x for x in rows if x["severity"] != "DEFECT"]
        lines.append(f"## {label}: {len(dfx)} DEFECT, {len(wat)} WATCH")
        if dfx:
            lines.append("| element | owner | job | TT / FF | finding |")
            lines.append("|---|---|---|---|---|")
            for x in sorted(dfx, key=lambda x: -((x["native"] or {}).get("capture_ps") or 0)):
                lines.append(f"| {x['element']} | {x['owner'] or ''} | {x['job'] or ''} | {x['tt_ps']} / {x['ff_ps']} | "
                             + "; ".join(x["reset_findings"]) + " |")
        if wat:
            lines.append("")
            lines.append("WATCH (reset is the worst path but lands in a synchroniser / relay register with margin): "
                         + ", ".join(sorted(x["element"] for x in wat)))
        lines.append("")
    if others:
        lines.append(f"## Recent views (closed in the last {RECENT_DAYS} days) outside the release-tree die rows with a reset "
                     f"capture FAIL ({len(others)}; die by cell family)")
        lines.append("| die | cell | owner | job | capture |")
        lines.append("|---|---|---|---|---|")
        for o in others:
            lines.append(f"| {o['die'] or '?'} | {o['cell']} | {o['owner'] or ''} | {o['job'] or ''} | "
                         f"{o['capture_ps']:.1f} ps at {o['capture_pin']} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out")
    ap.add_argument("--md")
    ap.add_argument("--no-sta", action="store_true")
    a = ap.parse_args(argv)
    generated, rows = load_rows()
    bv = native_by_view()
    recs = audit(rows, bv, sta=not a.no_sta)
    others = other_views(bv, recs)
    hit = [x for x in recs if x["reset_findings"]]
    res = dict(schema="opentallas.reset_path_audit.v1", generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               release_tree_cache=generated, elements=len(recs), with_reset_finding=len(hit),
               per_die={d: sorted(x["element"] for x in hit if d in x["dies"] and x["severity"] == "DEFECT") for d in DIES},
               per_die_watch={d: sorted(x["element"] for x in hit if d in x["dies"] and x["severity"] != "DEFECT")
                              for d in DIES},
               sta_probed=sum(1 for x in recs if x["sta"]), other_views_reset_capture_fail=others, records=recs)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    md = markdown(recs, generated, others)
    if a.md:
        Path(a.md).write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
