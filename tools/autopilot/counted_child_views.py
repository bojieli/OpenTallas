#!/usr/bin/env python3
"""KW-FIX-32 11-07 (COORD 17:3x WAITS-ON-CHILD class fix (i)): signed views of COUNTED child cores for WAIT types.

A type whose plan entry names a child hard core without a bound lef/lib reads WAIT (plan probe flag planned / noview)
and launches on PROVISIONAL child views (KW-PROV-1).  Its provisional candidates came only from the wave's own jobs
(state.json, DRC-0 sign-off) and die-config prov_view_sources, so a child that the sign-off counter COUNTS from a
lane build or a re-sign (auto-resign/*, */resign*, signoff-sprint-*) gave no candidate: the type built on the plan
contract abstract.  This driver closes that gap without new P&R:

  1. modules = the WAIT children of the die's current plan probe (kit_wave_state.json plans[...].prov_deps of the
     types flagged planned / noview);
  2. records = the counter's signed_designs entries of each module (release_tree_plan cache; names 'module' or
     'module#WxH/<hash>' for outline variants, so every outline is a candidate);
  3. export: tools/autopilot/export_view.py (the autopilot's own PROBE_VIEW_READ + view_payload, no OpenROAD) runs on
     the record's host into a non-hub views root; only views with gates.json view_complete true are kept;
  4. order: candidates whose kit pins sha256 / canon sha256 prefix matches the plan entry's pins hash (probe
     core_views) first, then counter order; at most PROV_MAX candidates per module (prov_view.py checks the pins on
     the gen host and falls through on a mismatch);
  5. --apply merges them FIRST into dies.<die>.prov_view_sources (prev kept as prov_view_sources_prev_kw32).

  counted_child_views.py --die qwen_compute --export --manifest M.json      (exports + manifest)
  counted_child_views.py --die qwen_compute --apply --manifest M.json       (config edit, kit_wave.json)

KW-FIX-35-CV 11-08: the kit-wave tick runs --export --publish <hub>/prov_view_sources_auto.json itself (hourly per die,
only for the prelint's SIGNED IN COUNT BUT NO WAVE VIEW modules) and overlays the sidecar at read time.  NOTE --apply
edits the hub's local kit_wave.json, which the tick does NOT read (it reads origin coord/state): commit a config edit
through the coord path instead.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
COUNTER = HOME / ".local/state/fleet-viz/release_tree_plan_cache.json"
COORD = HOME / "coord"
CFG = COORD / "autopilot/kit_wave.json"
STATE = COORD / "autopilot/kit_wave_state.json"
HUB = os.environ.get("OT_HUB_NAME", "intel2")
VIEWS_ROOT = "/srv/opentallas-scratch3/claude/kw32-views"   # non-hub disk on every host
TOOL_DIR = VIEWS_ROOT + "/tool"                              # tools/autopilot (+ die_plan/die_sta_related.py) of main
HUB_TOOL_DIR = str(HOME / "OpenTallas")                     # the hub's main checkout (read only), no copy on the hub
HUB_RELAY_HOST = "epyc4"                                     # records on the hub: view copied here (no hub payload)
PROV_MAX = 3
WAIT_FLAGS = ("planned", "noview")
SSH = ["ssh", "-n", "-o", "ControlPath=none", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]


def norm_module(name):
    """counter design name -> module: 'm#250.56x267.84/10ac9d744407ff50' -> 'm'; 'm__v<12hex>' -> 'm'"""
    return re.sub(r"__v[0-9a-f]{12}$", "", str(name).split("#", 1)[0])


def outline_of(name):
    m = re.match(r"^[^#]+#([^/]+)(?:/([0-9a-f]+))?$", str(name))
    return (m.group(1), m.group(2)) if m else (None, None)


def parse_record(rec):
    """'host:/x/signoff/signoff.json src S flow F ... db /x/base/6_final.odb ...' -> dict or None"""
    s = str(rec)
    m = re.match(r"^(?P<host>[A-Za-z0-9_-]+):(?P<so>/\S+signoff\.json)", s)
    if not m:
        return None
    db = re.search(r"\bdb (/\S+\.odb)", s)
    flow = re.search(r"\bflow (\S+)", s)
    out = dict(host=m.group("host"), signoff=m.group("so"), db=db.group(1) if db else None,
               flow_tag=flow.group(1) if flow else None)
    if out["db"]:
        base = os.path.dirname(out["db"])
        out["base"] = base
        i = base.find("/run/results/")
        out["kit"] = base[:i] if i > 0 else None
    else:
        out["base"] = out["kit"] = None
    return out


def counter_records(counter, die):
    """{module: [(counter_name, record), ...]} in counter order, deduplicated by sign-off path"""
    out, seen = {}, set()
    for ent in (counter.get("plans") or {}).values():
        if ent.get("die") != die:
            continue
        for name, recs in sorted((ent.get("signed_designs") or {}).items()):
            for r in recs if isinstance(recs, list) else [recs]:
                p = parse_record(r)
                if not p or not p["kit"] or p["signoff"] in seen:
                    continue
                seen.add(p["signoff"])
                out.setdefault(norm_module(name), []).append((name, p))
    return out


def wait_children(state, cfg, die):
    """WAIT types and their children from the die's cached plan probe -> ({module: [types]}, probe)"""
    d = cfg["dies"][die]
    key = f"{d['gen_host']}:{d['plan']}|{d['event']}"
    p = (state.get("plans") or {}).get(key) or {}
    flags, deps = p.get("flags") or {}, p.get("prov_deps") or p.get("deps") or {}
    mods = {}
    for t, f in flags.items():
        if f in WAIT_FLAGS:
            for m in deps.get(t) or []:
                mods.setdefault(m, []).append(t)
    return mods, p


def rec_id(p):
    return hashlib.sha256(p["signoff"].encode()).hexdigest()[:12]


def order_candidates(cands, plan_hashes):
    """plan-pin-hash matches first (kit pins sha256 or canon sha256 prefix in the probe core_views), then given order"""
    hs = {str(h) for h in plan_hashes or ()}

    def hit(c):
        for k in ("pins_sha256", "pins_canon_sha256", "counter_hash"):
            v = str(c.get(k) or "")
            if v and any(v.startswith(h) or h.startswith(v) for h in hs):
                return True
        return False
    for c in cands:
        c["plan_pin_match"] = hit(c)
    return sorted(cands, key=lambda c: not c["plan_pin_match"])[:PROV_MAX]


def run(argv, timeout=600, tries=4):
    """ssh rc 255 (connection reset under host load) is retried with a short back-off; any other rc is final"""
    for i in range(tries):
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 255 or i == tries - 1:
            return r.returncode, r.stdout, r.stderr
        time.sleep(5 * (i + 1))


ORFS_IMAGE = "openroad/orfs:asap7lock"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"


def parse_result(so):
    """last JSON object export_view.py printed (one line when complete, indented when not)"""
    dec, res, i = json.JSONDecoder(), None, 0
    while True:
        i = so.find("{", i)
        if i < 0:
            return res
        try:
            obj, j = dec.raw_decode(so, i)
        except ValueError:
            i += 1
            continue
        if isinstance(obj, dict) and "module" in obj:
            res = obj
        i = j


def needs_parent_only(res):
    """the only problem is the LOCAL_PASS_NEEDS_PARENT verdict: OWNER 11-03 counts it SIGNED (missing only the
    parent's io_hold receipt), the counter counts it, so its view is a provisional source like any signed one"""
    pr = (res or {}).get("problems") or []
    return bool(pr) and all("LOCAL_PASS_NEEDS_PARENT" in str(x) and "is not SIGNED" in str(x) for x in pr)


def lef_only(res, mod):
    """the view misses only <mod>.lef (flows whose finish step wrote tt/ff ETMs to kit/views but no abstract)"""
    pr = res.get("problems") or []
    lef = [x for x in pr if f"{mod}.lef not found" in str(x)]
    # KW-FIX-35-CV 11-08 (HBM hcol_h0_ra / hcol_h0_rb): a LOCAL_PASS_NEEDS_PARENT re-sign whose kit also lacks the lef
    # listed both problems, so neither this nor needs_parent_only() held and the counted view never exported.  The
    # verdict problem is the one OWNER 11-03 counts SIGNED; it does not stop the lef-from-odb path.
    return bool(lef) and all(x in lef or ("LOCAL_PASS_NEEDS_PARENT" in str(x) and "is not SIGNED" in str(x)) for x in pr)


def lef_from_odb(die, rid, p, mod, cmd, out, log):
    """write_abstract_lef of the SIGNED 6_final.odb (read-only mount, ~40 s, docker --memory 16g) into a staged base
    (symlinks to every base file + the lef), then export_view again on that base.  The kit/views ETMs must be newer
    than the odb (written by the same finish), else the view is refused."""
    stage = f"{VIEWS_ROOT}/{die}/_stage/{rid}"     # outside the view dir (the re-export clears that)
    sh = (f"cd / && set -e; B={shlex.quote(p['base'])}; K={shlex.quote(p['kit'])}; S={shlex.quote(stage)}; "
          f"M={shlex.quote(mod)}; for l in $K/views/${{M}}_tt.lib $K/views/${{M}}_ff.lib; do [ $l -nt $B/6_final.odb ] || "
          f"{{ echo ETM_OLDER_THAN_ODB $l >&2; exit 3; }}; done; "
          f"rm -rf $S && mkdir -p $S && for f in $B/*; do ln -s $f $S/; done; L=$M.lef; "
          f"printf 'read_db /b/6_final.odb\nwrite_abstract_lef /o/%s\nputs OT_LEF_DONE\n' $L > $S/kw32_lef.tcl; "
          f"timeout 600 docker run --rm --memory 16g --user $(id -u):$(id -g) -v $B:/b:ro -v $S:/o {ORFS_IMAGE} "
          f"bash -lc '{OPENROAD} -no_init -exit /o/kw32_lef.tcl' > $S/kw32_lef.log 2>&1; "
          f"grep -q OT_LEF_DONE $S/kw32_lef.log && rm -f $S/kw32_lef.tcl")
    rc, so, se = run(SSH + [p["host"], sh], timeout=900)
    if rc:
        log(f"LEF-FROM-ODB-FAIL {die} {p['host']}:{p['base']} rc {rc}: {se[-200:]}")
        return rc, so, se, None
    cmd2 = cmd.replace(f"--base {shlex.quote(p['base'])}", f"--base {shlex.quote(stage)}")
    rc, so, se = run(SSH + [p["host"], f"rm -rf {shlex.quote(out)} && " + cmd2])
    res = parse_result(so)
    if res is not None:
        res["lef_from_odb"] = True
    return rc, so, se, res


ABSTRACT_DETAIL = Path(__file__).resolve().parents[1] / "die_plan" / "abstract_detail.py"
DETAIL_KEYS = ("detailed_lef", "detailed_receipt", "detail_bloat_factor", "detail_pg_layer")


def view_detail(die, rid, p, mod, vdir, on_hub, log):
    """DIE-HBM-97 11-09 (DRT-0073 class): a view whose abstract encloses a signal pin under its own OBS (M5 clock pin,
    blanket or bloat-10 OBS on M5 and M6: write_abstract_lef defaults to -bloat_factor 10, ORFS generate_abstract uses
    -bloat_occupied_layers) gets detail_view.lef + detail_receipt.json next to the signed files, spliced from the SAME
    signed 6_final.odb.  The signed <mod>.lef stays as it was.  -> the wave's candidate fields, {} when none is needed.
    A failure here never stops the export: it is logged and the view goes out as before."""
    lef, q = f"{vdir}/{mod}.lef", shlex.quote
    helper, stage = str(ABSTRACT_DETAIL), f"{VIEWS_ROOT}/{die}/_stage/{rid}_detail"
    tool = helper if on_hub else f"{stage}/abstract_detail.py"       # this exporter's own helper, not a host copy
    if not on_hub:
        rc, so, se = run(SSH + [p["host"], f"rm -rf {q(stage)} && mkdir -p {q(stage)}"])
        if not rc:
            rc, so, se = run(["rsync", "-a", "-e", "ssh -o ControlPath=none -o BatchMode=yes", helper,
                              f"{p['host']}:{tool}"])
        if rc:
            log(f"DETAIL-PLAN-FAIL {die} {mod} {p['host']} helper copy rc {rc}: {(se or so)[-200:]}")
            return {}
    cmd = f"cd / && python3 -I {q(tool)} plan --base {q(lef)}"
    rc, so, se = run(["bash", "-c", cmd] if on_hub else SSH + [p["host"], cmd])
    try:
        plan = json.loads(so) if not rc else None
    except ValueError:
        plan = None
    if not plan or not plan.get("needed"):
        if not plan:
            log(f"DETAIL-PLAN-FAIL {die} {mod} {p['host']} rc {rc}: {(se or so)[-200:]}")
        elif plan.get("pin_window"):
            log(f"PIN-WINDOW-NO-DETAIL-FORM {die} {mod} {plan['pin_window'].get('pins')}: no pin access, but no "
                "detailed splice form applies; view published without a window")
        if not on_hub:
            run(SSH + [p["host"], f"rm -rf {q(stage)}"])
        return {}
    if on_hub:                                       # no OpenROAD on the hub, as for lef_from_odb
        log(f"DETAIL-NEEDED-ON-HUB {die} {mod} {plan.get('enclosed')}: view published without detail")
        return {}
    bf, layers = plan["bloat_factor"], ",".join(plan["layers"])
    # DIE-QC-97 11-10: signal pins the base leaves unreachable get a pin access window (exact metal kept inside it)
    pw = plan.get("pin_window") or {}
    on = pw.get("margin_um") is not None and bool(pw.get("top_layer"))
    exact = "detail.lef" if bf == 0 else "detail0.lef"
    win = (f" --pin-window-um {float(pw['margin_um'])} --top-layer {q(str(pw['top_layer']))} --window-detail $T/{exact}"
           if on else "")
    exact_tcl = (r"&& printf 'write_abstract_lef -bloat_factor 0 /o/detail0.lef\n' >> $T/d.tcl " if on and bf != 0 else "")
    sh = (f"cd / && T={q(stage)}; V={q(vdir)}; A={q(tool)}; "
          f"O=$(realpath {q(p['base'] + '/6_final.odb')}) && test -s $O "
          f"&& python3 -I $A tcl --odb /b/$(basename $O) --out /o/detail.lef --bloat-factor {bf} > $T/d.tcl "
          f"{exact_tcl}&& printf 'puts OT_DETAIL_DONE\n' >> $T/d.tcl "
          f"&& timeout 600 docker run --rm --memory 16g --user $(id -u):$(id -g) -v $(dirname $O):/b:ro -v $T:/o "
          f"{ORFS_IMAGE} bash -lc '{OPENROAD} -no_init -exit /o/d.tcl' > $T/d.log 2>&1 "
          f"&& grep -q OT_DETAIL_DONE $T/d.log "
          f"&& python3 -I $A splice --base {q(lef)} --detail $T/detail.lef --out $V/detail_view.lef "
          f"--layers {q(layers)} --bloat-factor {bf}{win} > $V/detail_receipt.json; rc=$?; "
          f"[ $rc = 0 ] || rm -f $V/detail_view.lef $V/detail_receipt.json; rm -rf $T; exit $rc")
    rc, so, se = run(SSH + [p["host"], sh], timeout=900)
    if rc:
        log(f"DETAIL-FAIL {die} {mod} {p['host']}:{p['base']} rc {rc}: {(se or so)[-200:]}")
        return {}
    log(f"DETAIL {die} {mod} layers {layers} bloat {bf} enclosed {plan.get('enclosed')}"
        + (f" pin windows {pw.get('pins')}" if win else ""))
    out = dict(detailed_lef="detail_view.lef", detailed_receipt="detail_receipt.json", detail_bloat_factor=bf)
    if plan.get("pg_layer"):
        out["detail_pg_layer"] = True
    return out


def export_one(die, name, p, log):
    """export_view.py on the record's host -> candidate dict or None"""
    rid = rec_id(p)
    host = p["host"]
    on_hub = host in (HUB, "localhost")
    out = (f"/tmp/kw32-views-relay/{die}/{rid}" if on_hub else f"{VIEWS_ROOT}/{die}/{rid}")
    tool = HUB_TOOL_DIR if on_hub else TOOL_DIR
    cmd = (f"cd / && mkdir -p {shlex.quote(out)} && python3 -I {tool}/tools/autopilot/export_view.py "
           f"--kit {shlex.quote(p['kit'])} --signoff {shlex.quote(p['signoff'])} --base {shlex.quote(p['base'])} "
           f"--out {shlex.quote(out)} --die {shlex.quote(die)} --note {shlex.quote('KW-FIX-32 counted child ' + name)}"
           + (f" --flow-tag {shlex.quote(p['flow_tag'])}" if p.get("flow_tag") else ""))
    argv = ["bash", "-c", cmd] if on_hub else SSH + [host, cmd]
    rc, so, se = run(argv)
    res = parse_result(so)
    if res and not res.get("complete") and lef_only(res, res.get("module")) and not on_hub:
        rc, so, se, res = lef_from_odb(die, rid, p, res["module"], cmd, out, log)
    if rc and needs_parent_only(res):
        rc = 0                                   # OWNER 11-03: LOCAL_PASS_NEEDS_PARENT counts SIGNED
    if rc or not res:
        log(f"EXPORT-FAIL {die} {name} {host}:{p['signoff']} rc {rc}: {(se or so)[-300:]}")
        return None
    needs_parent = needs_parent_only(res)
    if not res.get("complete") and not needs_parent:
        log(f"EXPORT-INCOMPLETE {die} {name} {host}:{p['signoff']}: {res.get('problems')}")
        return None
    mod = res["module"]
    vdir = res["view"]
    detail = view_detail(die, rid, p, mod, vdir, on_hub, log)
    if on_hub:
        dst = f"{VIEWS_ROOT}/{die}/{rid}/{mod}"
        rc1, _, e1 = run(SSH + [HUB_RELAY_HOST, f"mkdir -p {shlex.quote(dst)}"])
        rc2, _, e2 = run(["rsync", "-a", "-e", "ssh -o ControlPath=none -o BatchMode=yes", vdir + "/",
                          f"{HUB_RELAY_HOST}:{dst}/"])
        if rc1 or rc2:
            log(f"RELAY-FAIL {die} {name}: {e1 or e2}")
            return None
        subprocess.run(["rm", "-rf", f"/tmp/kw32-views-relay/{die}/{rid}"])   # own relay dir only
        host, vdir = HUB_RELAY_HOST, dst
    outline, chash = outline_of(name)
    return dict(host=host, dir=vdir, job=f"COUNTED {name} {p['host']}:{p['signoff']} (KW-FIX-32 export_view)",
                module=mod, counter_name=name, outline=outline, counter_hash=chash, flow_tag=p.get("flow_tag"),
                signoff=f"{p['host']}:{p['signoff']}", pins_sha256=res.get("pins_sha256"),
                lef_from_odb=bool(res.get("lef_from_odb")), verdict_needs_parent=needs_parent,
                pins_canon_sha256=res.get("pins_canon_sha256"), **detail)


def build_manifest(die, cfg, state, counter, export=True, log=print, only=None):
    mods, probe = wait_children(state, cfg, die)
    recs = counter_records(counter, die)
    cv = probe.get("core_views") or {}
    man = dict(schema="opentallas.kw32.counted_child_views.v1", die=die, generated=time.strftime("%Y-%m-%d %H:%M %Z"),
               plan_sha=probe.get("plan_sha"), modules={}, missing={})
    for m, types in sorted(mods.items()):
        if only and m not in only:
            continue
        if m not in recs:
            man["missing"][m] = sorted(set(types))
            continue
        cands = []
        for name, p in recs[m]:
            c = export_one(die, name, p, log) if export else dict(host=p["host"], dir=None, counter_name=name)
            if c:
                cands.append(c)
        uniq, keys = [], set()
        for c in cands:                      # the same signed view staged in several worktrees: one candidate
            k = (c.get("pins_sha256"), c.get("pins_canon_sha256"), c.get("outline"))
            if k not in keys:
                keys.add(k)
                uniq.append(c)
        cands = uniq
        man["modules"][m] = dict(types=sorted(set(types)), plan_pin_hashes=cv.get(m) or [],
                                 candidates=order_candidates(cands, cv.get(m)))
    return man


def apply_manifest(cfg, man):
    """merge the manifest candidates FIRST into dies.<die>.prov_view_sources (in place); returns the changed modules"""
    d = cfg["dies"][man["die"]]
    cur = copy.deepcopy(d.get("prov_view_sources") or {})
    if "prov_view_sources_prev_kw32" not in d:
        d["prov_view_sources_prev_kw32"] = copy.deepcopy(d.get("prov_view_sources"))
    changed = []
    for m, ent in sorted((man.get("modules") or {}).items()):
        new = [dict(host=c["host"], dir=c["dir"], job=c["job"]) for c in ent.get("candidates") or [] if c.get("dir")]
        if not new:
            continue
        old = cur.get(m) or []
        old = old if isinstance(old, list) else [old]
        dirs = {c["dir"] for c in new}
        merged = new + [c for c in old if c.get("dir") not in dirs]
        if merged != old:
            cur[m] = merged
            changed.append(m)
    d["prov_view_sources"] = cur
    d["note_prov_view_sources_kw32"] = (
        f"KW-FIX-32 {man.get('generated')}: signed views of counted child cores (counted_child_views.py, export_view.py "
        f"of the counter's sign-off records) first in prov_view_sources for {len(changed)} modules; "
        "revert: prov_view_sources <- prov_view_sources_prev_kw32")
    return changed


def publish_manifest(path, man):
    """KW-FIX-35-CV 11-08: merge the manifest's complete candidates into the hub sidecar the wave overlays at read time
    (kit_wave.merge_auto_views): {schema, dies: {die: {generated, plan_sha, modules: {m: [candidate]}}}}.  A module with
    no complete candidate this run keeps its earlier entry (a signed view does not expire); flock + atomic replace,
    so concurrent dies never lose each other's entries.  -> modules published"""
    import fcntl
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(str(p) + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            side = json.loads(p.read_text())
        except (OSError, ValueError):
            side = {}
        side["schema"] = "opentallas.kw35cv.prov_view_sources_auto.v1"
        ent = side.setdefault("dies", {}).setdefault(man["die"], {})
        mods = ent.setdefault("modules", {})
        done = []
        for m, e in sorted((man.get("modules") or {}).items()):
            new = [dict(host=c["host"], dir=c["dir"], job=c["job"], counted=True, signoff=c.get("signoff"),
                        outline=c.get("outline"), pins_sha256=c.get("pins_sha256"),
                        plan_pin_match=c.get("plan_pin_match"), **{k: c[k] for k in DETAIL_KEYS if k in c})
                   for c in e.get("candidates") or [] if c.get("dir") and c.get("host")]
            if new:
                mods[m] = new
                done.append(m)
        ent.update(generated=man.get("generated"), plan_sha=man.get("plan_sha"), last_published=done,
                   missing=sorted(man.get("missing") or {}))
        tmp = p.with_name(p.name + f".{os.getpid()}")
        tmp.write_text(json.dumps(side, indent=1, sort_keys=True) + "\n")
        os.replace(tmp, p)
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--die", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--export", action="store_true", help="run the exports and write the manifest")
    ap.add_argument("--apply", action="store_true", help="merge the manifest into kit_wave.json prov_view_sources")
    ap.add_argument("--config", default=str(CFG))
    ap.add_argument("--state", default=str(STATE))
    ap.add_argument("--counter", default=str(COUNTER))
    ap.add_argument("--only", nargs="*", help="modules to export (default: all WAIT children)")
    ap.add_argument("--publish", help="merge the exported candidates into this hub sidecar (kit_wave AUTO-VIEWS overlay)")
    a = ap.parse_args(argv)
    if a.export:
        cfg = json.loads(Path(a.config).read_text())
        man = build_manifest(a.die, cfg, json.loads(Path(a.state).read_text()), json.loads(Path(a.counter).read_text()),
                             only=set(a.only) if a.only else None, log=lambda s: print(s, file=sys.stderr))
        Path(a.manifest).write_text(json.dumps(man, indent=1) + "\n")
        n = sum(1 for e in man["modules"].values() if e["candidates"])
        print(f"{a.die}: {len(man['modules'])} counted WAIT children, {n} with a complete exported view, "
              f"{len(man['missing'])} not counted")
        if a.publish:
            done = publish_manifest(a.publish, man)
            print(f"{a.die}: published {len(done)} modules to {a.publish}: {' '.join(done)}")
    if a.apply:
        man = json.loads(Path(a.manifest).read_text())
        cfg = json.loads(Path(a.config).read_text())
        changed = apply_manifest(cfg, man)
        s = json.dumps(cfg, indent=2)
        json.loads(s)
        tmp = a.config + ".kw32tmp"
        Path(tmp).write_text(s)
        os.replace(tmp, a.config)
        print(f"{a.die}: prov_view_sources updated for {len(changed)} modules: {' '.join(changed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
