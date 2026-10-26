#!/usr/bin/env python3
"""auto_geom.py -- AUTO-GEOM: template registry + autopilot step (OWNER 2026-10-25 ~20:25).

Owner decision: a part built from a template that already passed visual GEOM review may pass on AUTOMATED rule checks
(geom_rules.py), with visual review sampled ~1 in 10.  Visual review stays mandatory for new templates, failures and
die-level items.  OFF unless the hub sets AP_AUTO_GEOM=1 (enable only after COORD approval).

Template registry (coord/state autopilot/geom_templates.tsv, append-only; last row per template id wins):
    tid die type design die_area rtl_sha pins_sha stage template_kit checkpoint metrics geom_ref scope registered by
  A template is a kit whose checkpoint (3_place or 4_cts) got a visual GEOM-REVIEW PASS / PASS-COND that allowed the
  route (scope 'route'; CTS-only / GRT-only / diagnostic verdicts never make a template).  metrics = HOST:PATH of the
  template checkpoint's own geom_rules.py auto_geom.json.  A row with scope 'revoked' removes the template.
  A queued kit is a REPLICA of a template when (kit signature, PROBE_SIG): same DESIGN_NAME, same RTL bytes (every
  VERILOG_FILES file + VERILOG_DEFINES), same DIE_AREA, same pin table (pins.json / io.tcl lines without strap_*).
  The rule check then also compares outline, macros, pin table, tap set and (CTS) clock-tree shape with the template.
  A template is REVOKED automatically when lanes/GEOM-REVIEW.md carries a later FAIL naming its type in the template's
  geom_ref tag (2026-10-25 vmr_s6kc: PASS-COND 14:56, FAIL 17:54 on the same ODB).

Queue: --geom AUTO [--geom-ref 'TEMPLATE <tid>'] (no tid: matched by signature).  Per tick, for each AUTO row:
  NOT-REPLICA / no checkpoint / disabled -> stays WAIT-GEOM (lane posts a normal GEOM REQ);
  replica -> check job (geom_check.sh on the kit host, docker, read-only) -> auto_geom.tsv row + a verdict line
  published to lanes/GEOM-REVIEW.md:
    PASS            -> row geom PASS, geom_ref 'GEOM-REVIEW [AUTO-GEOM <id>] AUTO PASS ...' -> routes (closure-order
                       holds, canary, path gate rule 1 unchanged; a later reviewer FAIL on that tag demotes / alerts
                       as for any verdict);
    PASS + sampled  -> same, and the line is a 'GEOM REQ [AUTO-GEOM <id>]' audit request (deterministic 1 in 10);
    FAIL            -> 'GEOM REQ [AUTO-GEOM <id>]' for the visual reviewers; the row waits on that tag like any REQ.
"""
from __future__ import annotations

import hashlib
import json
import re
import shlex
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REG_PATH = "autopilot/geom_templates.tsv"
REG_COLS = ["tid", "die", "type", "design", "die_area", "rtl_sha", "pins_sha", "stage", "template_kit", "checkpoint",
            "metrics", "geom_ref", "scope", "registered", "by"]
AG_TSV = "auto_geom.tsv"
AG_HEAD = "time\tid\tdie\ttype\tkit\ttemplate\tcheckpoint\tverdict\tsampled\tline"
AG_ROOT = "/srv/opentallas-scratch2/claude/autopilot/auto_geom"
SAMPLE_MOD = 10
CHECK_MEM_GB = 24
CHECK_TIMEOUT_S = 2 * 3600

# remote probe: kit signature (read-only).  args: {"kit": path}
PROBE_SIG = r'''
import json, sys, os, re, glob, hashlib
a = json.loads(sys.argv[1]); K = a["kit"]; out = {"kit": K}
def done(): print("AP_JSON " + json.dumps(out)); sys.exit(0)
cfg = os.path.join(K, "config.mk")
if not os.path.isfile(cfg):
    out["error"] = "no config.mk"; done()
v = {}
for ln in open(cfg, errors="replace"):
    m = re.match(r"\s*(?:export\s+)?([A-Z0-9_]+)\s*[:?]?=\s*(.*)$", ln)
    if m: v[m.group(1)] = m.group(2).strip()
out["design"] = v.get("DESIGN_NAME", "")
out["die_area"] = " ".join("%.4f" % float(x) for x in v.get("DIE_AREA", "").split()) if v.get("DIE_AREA") else ""
h = hashlib.sha256(); miss = []
for f in v.get("VERILOG_FILES", "").split():
    p = f.replace("/work/", K.rstrip("/") + "/", 1) if f.startswith("/work/") else f
    if "$" in p or not os.path.isfile(p):
        miss.append(f); continue
    h.update(os.path.basename(p).encode() + b"\0" + hashlib.sha256(open(p, "rb").read()).digest())
h.update(("DEFINES=" + v.get("VERILOG_DEFINES", "")).encode())
out["rtl_sha"] = h.hexdigest()[:16] if v.get("VERILOG_FILES") and not miss else ""
out["rtl_missing"] = miss[:5]
pf = next((os.path.join(K, n) for n in ("pins.json", "io.tcl") if os.path.isfile(os.path.join(K, n))), None)
if pf:
    lines = [l for l in open(pf, errors="replace").read().replace(",", ",\n").splitlines() if "strap_" not in l]
    out["pins_sha"] = hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]
    out["pins_file"] = os.path.basename(pf)
else:
    out["pins_sha"] = ""
base = sorted(glob.glob(os.path.join(K, "run", "results", "asap7", "*", "base")))
ck = []
for b in base:
    for n in ("4_cts.odb", "3_place.odb"):
        if os.path.isfile(os.path.join(b, n)): ck.append(os.path.join(b, n)); break
out["checkpoints"] = ck
out["routed"] = [os.path.basename(p) for b in base for p in glob.glob(os.path.join(b, "*.odb"))
                 if re.match(r"^(5_|6_)", os.path.basename(p))]
if ck:
    out["odb_bytes"] = os.path.getsize(ck[0])
done()
'''


# ------------------------------------------------------------------------------------------------ registry
def parse_registry(text):
    """{tid: row} -- last row per tid wins; scope 'revoked' rows remove the template"""
    reg = {}
    for raw in (text or "").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        f = raw.split("\t")
        if f[0] == "tid":
            continue
        r = {k: (f[i].strip() if i < len(f) else "") for i, k in enumerate(REG_COLS)}
        if not r["tid"]:
            continue
        if r["scope"] == "revoked":
            reg.pop(r["tid"], None)
            continue
        reg[r["tid"]] = r
    return reg


def revoked_by_review(tmpl, geom_text, LG):
    """a later GEOM-REVIEW FAIL that names the template's type under its geom_ref tag revokes it (latest verdict wins)"""
    m = re.search(r"\[([^\]]+)\]", tmpl.get("geom_ref") or "")
    if not m:
        return None
    tag = LG.tag_of(m.group(1))
    reqs, reps = LG.geom_events(geom_text or "")
    t_reg = LG.parse_ts(tmpl.get("registered") or "", 0) or 0
    last = None
    for t, rtag, v, line in reps:
        if rtag != tag or not v:
            continue
        if not LG.KitIdent(tmpl["type"], tmpl.get("template_kit", "")).names(line):
            continue
        last = (t or 0, v, line)
    if last and last[1] == "FAIL":
        return f"GEOM-REVIEW FAIL {time.strftime('%m-%d %H:%M', time.localtime(last[0]))} on [{tag}] names {tmpl['type']}"
    _ = t_reg
    return None


def match(reg, sig, die, want_tid=""):
    """(template row, why-not) for a kit signature"""
    if sig.get("error"):
        return None, f"kit signature: {sig['error']}"
    if not sig.get("rtl_sha"):
        return None, f"RTL not hashable (missing {sig.get('rtl_missing')})"
    cands = [reg[want_tid]] if want_tid and want_tid in reg else ([] if want_tid else list(reg.values()))
    if want_tid and not cands:
        return None, f"template {want_tid} not registered (or revoked)"
    why = []
    for t in cands:
        miss = [k for k in ("design", "rtl_sha", "die_area", "pins_sha") if (sig.get(k) or "") != t[k]]
        if t["die"] != die:
            miss.append("die")
        if not miss:
            return t, ""
        why.append(f"{t['tid']}: {'/'.join(miss)} differ")
    return None, "not a registered template replica" + (f" ({'; '.join(why[:3])})" if why else " (no template)")


def sampled(rid):
    return int(hashlib.sha1(f"auto-geom|{rid}".encode()).hexdigest(), 16) % SAMPLE_MOD == 0


# ------------------------------------------------------------------------------------------------ autopilot step
def enabled():
    import os
    return os.environ.get("AP_AUTO_GEOM", "") == "1"


def prepare(ap, st, rows):
    """before resolve_geom: AUTO rows that already have an AUTO-GEOM verdict get it applied (PASS) or are turned into a
    REQ on their own AUTO-GEOM tag (FAIL), so a reviewer REPLY [AUTO-GEOM <id>] is read by the normal geom chain"""
    ag = st.setdefault("auto_geom", {})
    for rid, r in rows.items():
        if r["error"] or r["geom"].upper() != "AUTO":
            continue
        a = ag.get(rid) or {}
        if a.get("verdict") == "PASS":
            r["geom"] = "PASS"
            r["geom_ref"] = a["geom_ref"]
        elif a.get("verdict") == "FAIL":
            r["geom"] = "REQ"
            r["geom_ref"] = f"GEOM REQ [AUTO-GEOM {rid}]"


def step(ap, st, r, geom_text):
    """one AUTO row (geom still AUTO after prepare): drive signature -> match -> check job -> verdict.  Returns a
    short status note for WAIT-GEOM (the row is never submitted from here; a PASS is applied by prepare next tick)."""
    rid = r["id"]
    ag = st.setdefault("auto_geom", {})
    a = ag.setdefault(rid, {})
    if not enabled():
        return "AUTO-GEOM disabled on this hub (AP_AUTO_GEOM != 1): post a GEOM REQ"
    if a.get("state") == "CHECK":
        return poll(ap, st, r, a)
    if a.get("state") in ("NOT-REPLICA", "NO-CHECKPOINT") and time.time() - a.get("t", 0) < 3600:
        return a["why"]
    reg = parse_registry(ap.read_coord(REG_PATH))
    for tid, t in list(reg.items()):
        why = revoked_by_review(t, geom_text, ap.LG)
        if why:
            reg.pop(tid)
            if a.get("revoked_note") != why:
                ap.log(f"AUTO-GEOM template {tid} revoked for {rid}: {why}")
                a["revoked_note"] = why
    sig = ap.rpy(r["host"], PROBE_SIG, {"kit": r["path"]}, timeout=120)
    want = ""
    m = re.match(r"\s*TEMPLATE\s+(\S+)", r.get("geom_ref") or "")
    if m:
        want = m.group(1)
    t, why = match(reg, sig, r["die"], want)
    if not t:
        a.update(state="NOT-REPLICA", why=f"AUTO-GEOM: {why} -> visual GEOM REQ needed", t=time.time())
        ap.log(f"AUTO-GEOM {rid} {r['die']}/{r['type']}: {a['why']}")
        return a["why"]
    if sig.get("routed"):
        a.update(state="NO-CHECKPOINT", why=f"AUTO-GEOM: kit already routed ({sig['routed'][:3]}); enqueue a fresh kit",
                 t=time.time())
        return a["why"]
    want_stage = "4_cts.odb" if t["stage"] == "cts" else "3_place.odb"
    ck = [c for c in sig.get("checkpoints") or [] if c.endswith(want_stage)]
    if not ck:
        a.update(state="NO-CHECKPOINT", t=time.time(),
                 why=f"AUTO-GEOM: replica of {t['tid']} but no {want_stage} yet (template stage {t['stage']}); "
                     "run place/CTS first")
        return a["why"]
    return launch(ap, st, r, a, t, ck[0], sig)


def launch(ap, st, r, a, t, odb, sig):
    rid = r["id"]
    host = ap.ssh_host(r["host"])
    out = f"{AG_ROOT}/{rid}"
    th, tp = t["metrics"].split(":", 1) if ":" in t["metrics"] else (host, t["metrics"])
    tools = [HERE / "geom_check.sh", HERE / "geom_dump.tcl", HERE / "geom_rules.py"]
    rc, _, err = ap.rbash(host, f"mkdir -p {shlex.quote(out)}/tools", timeout=60)
    ok = rc == 0
    for f in tools:
        if ok:
            rc, _, err = ap.sh(["scp", "-q", "-o", "BatchMode=yes", "-o", "ControlPath=none", str(f), f"{host}:{out}/tools/"],
                               timeout=120)
            ok = rc == 0
    if ok:   # the template metrics travel with the check (template host may differ from the kit host)
        rc, txt, err = ap.rbash(ap.ssh_host(th), f"cat {shlex.quote(tp)}", timeout=120)
        ok = rc == 0 and txt.strip().startswith("{")
        if ok:
            rc, _, err = ap.rbash(host, f"cat > {shlex.quote(out)}/template.json <<'EOF_T'\n{txt}\nEOF_T\n", timeout=60)
            ok = rc == 0
    if not ok:
        a.update(state="NOT-REPLICA", why=f"AUTO-GEOM: check setup failed ({err.strip()[-160:]})", t=time.time())
        return a["why"]
    mem = max(CHECK_MEM_GB, min(128, int(6 * (sig.get("odb_bytes") or 0) / 2**30) + 8))
    meta = {"id": rid, "odb": odb, "image": ap.IMAGE, "mem_gb": mem,
            "rules_args": ["--template", f"{out}/template.json", "--title", f"{r['die']}/{r['type']} tmpl {t['tid']}"]}
    ap.rbash(host, f"cat > {shlex.quote(out)}/check.json <<'EOF'\n{json.dumps(meta)}\nEOF\n", timeout=60)
    unit = f"ap-{rid}-ageom"
    logf = ap.AP_DIR / "jobs" / rid / "auto_geom.log"
    argv = ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", host, "bash", f"{out}/tools/geom_check.sh", out]
    if not ap.launch_unit(unit, logf, argv):
        a.update(state="NOT-REPLICA", why="AUTO-GEOM: could not launch the check unit", t=time.time())
        return a["why"]
    a.update(state="CHECK", unit=unit, log=str(logf), out=f"{host}:{out}", odb=odb, template=t["tid"],
             template_ref=t["geom_ref"], started=time.time())
    ap.log(f"AUTO-GEOM {rid} {r['die']}/{r['type']}: replica of {t['tid']} -> rule check {unit} on {host} ({odb})")
    return f"AUTO-GEOM check running ({unit})"


def poll(ap, st, r, a):
    rid = r["id"]
    if ap.unit_active(a["unit"]) and time.time() - a["started"] < CHECK_TIMEOUT_S:
        return f"AUTO-GEOM check running ({a['unit']})"
    try:
        txt = Path(a["log"]).read_text(errors="replace")
    except OSError:
        txt = ""
    m = re.findall(r"^AP_AUTO_GEOM (AUTO-GEOM (PASS|FAIL).*)$", txt, re.M)
    if not m:
        a.update(state="NOT-REPLICA", why=f"AUTO-GEOM: check produced no verdict (see {a['log']}) -> visual GEOM REQ",
                 t=time.time())
        ap.log(f"AUTO-GEOM {rid}: {a['why']}")
        return a["why"]
    line, verdict = m[-1]
    smp = verdict == "PASS" and sampled(rid)
    stamp = time.strftime("%Y-%m-%d %H:%M %Z")
    host_out = a["out"]
    head = (f"{stamp} AUTOPILOT: " + (f"GEOM REQ [AUTO-GEOM {rid}] " if verdict == "FAIL" or smp else "")
            + f"{line} | {r['die']}/{r['type']} kit {r['kit']} src {r['src']} checkpoint {a['odb']} template "
              f"{a['template']} ({a['template_ref']}) rules {host_out}/auto_geom.json")
    head += (" | visual review requested: rule FAIL (reviewers: REPLY [AUTO-GEOM " + rid + "] naming the type)"
             if verdict == "FAIL" else " | 1-in-10 visual audit sample; routing proceeds on the AUTO PASS" if smp else "")
    a.update(state="DONE", verdict=verdict, sampled=smp, line=line, t_done=time.time(),
             geom_ref=f"GEOM-REVIEW [AUTO-GEOM {rid}] AUTO {verdict} {time.strftime('%m-%d %H:%M')}")
    ap.tsv_append(AG_TSV, rid, [r["die"], r["type"], r["kit"], a["template"], a["odb"], verdict, int(smp), line[:600]])
    publish_line(ap, head)
    ap.log(f"AUTO-GEOM {rid} {r['die']}/{r['type']}: {line[:300]}" + (" (sampled for visual audit)" if smp else ""))
    ap.save_state(st)
    return f"AUTO-GEOM {verdict}"


def publish_line(ap, text):
    if ap.DRY:
        ap.log(f"would publish GEOM-REVIEW line: {text[:200]}")
        return
    try:
        import queue_publish as QP
        QP.publish(ap.COORD, text, "AUTOPILOT AUTO-GEOM verdict", path="lanes/GEOM-REVIEW.md")
    except Exception as e:                            # the verdict stays in auto_geom.tsv + log; LOOP-GAPS shows it
        ap.log(f"AUTO-GEOM publish to lanes/GEOM-REVIEW.md failed: {type(e).__name__}: {e}")


def gaps(st, now):
    """LOOP-GAPS lines: AUTO-GEOM FAIL / sampled rows waiting for a visual reply"""
    out = []
    for rid, a in (st.get("auto_geom") or {}).items():
        if a.get("state") == "DONE" and (a.get("verdict") == "FAIL" or a.get("sampled")):
            out.append((a.get("t_done") or now, f"AUTO-GEOM-{'FAIL' if a['verdict'] == 'FAIL' else 'SAMPLE'} {rid}: "
                        f"visual review of GEOM REQ [AUTO-GEOM {rid}] ({a.get('line', '')[:140]})"))
    return out


# ------------------------------------------------------------------------------------------------ CLI
def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="AUTO-GEOM template registry helper")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("row", help="print a geom_templates.tsv row for a visually passed template (append it with "
                                   "queue_publish / coord-commit; metrics = the template checkpoint's auto_geom.json)")
    for k in ("tid", "die", "type", "kit", "checkpoint", "metrics", "geom-ref", "by"):
        s.add_argument("--" + k, required=True)
    s.add_argument("--sig", required=True, help="PROBE_SIG JSON of the template kit (python3 -I - '{\"kit\": ...}')")
    s.add_argument("--scope", default="route", choices=["route", "revoked"])
    a = p.parse_args(argv)
    sig = json.loads(Path(a.sig).read_text())
    stage = "cts" if a.checkpoint.endswith("4_cts.odb") else "placed" if a.checkpoint.endswith("3_place.odb") else ""
    if not stage:
        raise SystemExit("template checkpoint must be 3_place.odb or 4_cts.odb")
    row = [a.tid, a.die, a.type, sig.get("design", ""), sig.get("die_area", ""), sig.get("rtl_sha", ""),
           sig.get("pins_sha", ""), stage, a.kit, a.checkpoint, a.metrics, a.geom_ref, a.scope,
           time.strftime("%Y-%m-%d %H:%M %Z"), a.by]
    print("\t".join(x.replace("\t", " ") for x in row))


if __name__ == "__main__":
    main()
