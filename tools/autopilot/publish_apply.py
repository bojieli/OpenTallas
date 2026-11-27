#!/usr/bin/env python3
"""publish_apply.py -- LATENCY-R 11-18 (COORD ruling 11-18, OWNER "remove plan validations, build all types directly from the latest plan").

Measured 11-17 (lanes/LATENCY-1117.md): a plan event spent 1.5-3 h between "bind done" and "first kit": serial PRE/G0/R8/cohort/CB16 checks, a 13-92 min
publish gate (static then dry gen), a separate apply step that waited on a person, gate-label misses, then a tick.  This tool is the one step a lane runs
the moment its tree is PUBLISHED:

  apply     optimistic atomic apply (apply_reviewed_tree_marker optimistic=True: publish gate, source guard and smoke are ADVISORY, no pilot hold, the
            event joins gate_events_extra in the same write), commit through coord-commit.sh, then the publish gate is started in the background as a
            REPORT (its record lists advisory findings; it never blocks), and one post names the warnings.  The next wave pass launches every type.
            apply then starts the post-apply strict bind + LATCHECK itself (post-bind below) unless --no-post-bind.
  post-bind strict bind + LATCHECK of the candidate's PUBLISHED tree in a hardlink copy <tree>_postbind_<stamp> (sibling, .link-base = tree) on
            a gen host, via ot-run --plan-job bind; outputs only under <copy>/_postbind/; one POST-APPLY-BIND post with the result.  Never bind in
            the tree a lane is composing: the publish renames it (D8f 11-18).
  bind-fail strict bind / LATCHECK (still running in parallel, the only blocking plan checks) failed: hold ONLY the types it names (explicit --types,
            or the plan item names found in --log), released by result:<owner>:<id>.  Running rows of held types are cancelled by the wave (kit_wave
            hold_records with cancel_running, WAVE-FLOW-R2).

    publish_apply.py apply --candidate JSON --expect-source OLD_TREE --expect-event OLD_EVENT --lane LANE [--coord ~/coord] [--no-gate]
    publish_apply.py post-bind --candidate JSON --lane LANE [--die D] [--host H] [--coord ~/coord]
    publish_apply.py bind-fail --die DIE --lane LANE --id ID (--types t1,t2 | --log FILE) [--reason TEXT] [--coord ~/coord] [--dry]
    publish_apply.py derive-asbuilt --bind BIND_DIR --asbuilt KIT_ASBUILT --tree TREE --out NEW_ASBUILT
  apply first runs kit_topology.bind_matches on the candidate on a candidate host (FABLE-FLOW-1400): a bind that does not match refuses (rc 4).
  bind-fail writes dies.<die>.bind_fail {id, bind, items} first: the wave books those rows FAIL class BIND-FAIL until the bind changes.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import apply_reviewed_tree_marker as A  # noqa: E402
import flow_guard as FG  # noqa: E402
import hold_records as HR  # noqa: E402
import publish_bind_receipt as PBR  # noqa: E402
sys.path.insert(0, str(HERE.parent / "fleet"))
import ot_event_env as EE  # noqa: E402


def post(C, lane, text, run=subprocess.run):
    return run(["bash", str(Path(C) / "bin/post.sh"), lane, text], capture_output=True, text=True, timeout=600)


def gate_argv(C, cand_path, tree, event):
    """the advisory publish gate after the apply: the projection re-applies the SAME tree onto the live config, so it expects the new source/event"""
    return [sys.executable, "-I", str(HERE / "publish_gate.py"), "run", "--candidate", str(cand_path), "--expect-source", tree,
            "--expect-event", str(event), "--coord", str(C), "--commit"]

def advisory_gate_candidate(obj, live, previous_source, event):
    """An exact post-apply projection already contains the holds the apply installed."""
    candidate = {k: v for k, v in obj.items() if k != "_path"}
    candidate["optimistic"] = True
    marker = candidate.get("marker", candidate)
    want = marker.get("manifest_hash") or marker.get("src_manifest_sha")
    if (live.get("src"), live.get("event"), live.get("plan_sha256"), live.get("src_manifest_hash")) != (
            marker.get("tree"), event, marker.get("plan_sha256"), want):
        return candidate

    installed = live.get("hold_records") or []

    def already_installed(record):
        matches = [row for row in installed if row.get("id") == record.get("id")]
        if len(matches) != 1:
            return False
        expected = dict(record, release=A.repoint_hold_releases(
            record, marker["die"], previous_source, marker["tree"]))
        expected.pop("die", None)
        return json.dumps(expected, sort_keys=True) == json.dumps(matches[0], sort_keys=True)

    if candidate.get("hold_records_add"):
        candidate["hold_records_add"] = [
            record for record in candidate["hold_records_add"] if not already_installed(record)
        ]
    if candidate.get("hold_record") and already_installed(candidate["hold_record"]):
        candidate.pop("hold_record")
    return candidate


# FABLE-FLOW-1400 (1): QC sat 3.2 h on 56 BIND-STALE rows because the candidate's kit_rtl.asbuilt named the N2BBR clock table while its bind was made
# on N4DBQ.  apply now runs kit_topology.bind_matches (the wave's own bind preflight) on the candidate, on a host that holds the tree, BEFORE the switch.
PROBE_CAND = r"""
import functools, json, os, sys
from pathlib import Path
a = json.loads(sys.argv[1])
try:
    if a.get("scope"):
        os.environ["OT_NATIVE_RESET_SCOPE"] = a["scope"]
    sys.path.insert(0, str(Path(a["src"]) / "tools" / "die_plan"))
    import kit_topology as kt
    raw = json.loads(Path(a["plan"]).read_text())
    ab = a.get("asbuilt") or None
    plan = a["plan"]
    native_contract = kt.native_contract

    @functools.cache
    def candidate_contract():
        return native_contract(raw, ab, plan)

    def shared_contract(data, asbuilt=None, plan_path=None):
        if data is raw and asbuilt == ab and plan_path == plan:
            return candidate_contract()
        return native_contract(data, asbuilt, plan_path)

    # For this one sealed candidate, reuse its whole-plan fingerprint in the
    # frozen checker. Per-type receipt and separate producer checks still run.
    kt.native_contract = shared_contract
    types = [t for t in (raw.get("partition_types") or {}) if kt.has_topology(raw, t, ab)]
    stale = [t for t in types if not kt.bind_matches(raw, t, a["bind_out"], ab, plan)]
    diff = {}
    if stale:
        old = json.loads((Path(a["bind_out"]) / "native_topology.json").read_text())
        new = kt.native_contract(raw, ab, a["plan"])
        diff = {k: [str(old.get(k))[:16], str(new.get(k))[:16]] for k in ("clock_table_sha256", "reset", "transport", "ownership") if old.get(k) != new.get(k)}
    out = {"checked": len(types), "stale": stale, "diff": diff}
except Exception as e:
    out = {"error": (type(e).__name__ + ": " + str(e))[:300]}
print("AP_JSON " + json.dumps(out))
"""


# PRECHECK-1119 (owner 11-19): after each apply the static pre-build estimator (tools/precheck) runs in the background on
# the die's first gen host and posts its family summary to the applying lane.  It never blocks (owner r703/r704).
PRECHECK_RT = os.path.realpath(os.environ.get("OT_RT_CURRENT") or "/srv/opentallas-scratch2/claude/rt/current")   # FLOW-NOADV-R3: the sha dir at import, not a moving link


def prev_event_of(live, die):
    """ADOPT-CENSUS-1800: the previous event of the die (the live config BEFORE the switch) for EVENT-CENSUS"""
    live = live or {}
    if not live.get("plan"):
        return {}
    kr = ""
    if live.get("work_root") and live.get("event"):
        kr = str(Path(live["work_root"]) / die / str(live["event"]) / "items")
    return dict(plan=live["plan"], src=live.get("src") or "", event=live.get("event") or "", kit_root=kr)


def precheck_argv(obj, res, lane, now=None, prev=None, tools_sha=""):
    """the background precheck launch (ssh + systemd-run on the first gen host), or None when the candidate names no plan/tree/host.
    ADOPT-CENSUS-1800: the same unit runs ABS-CENSUS, ADOPT-DIFF and, given the previous event, EVENT-CENSUS"""
    m = obj.get("marker", obj)
    mc = m.get("config") or {}
    hosts = list(res.get("gen_hosts") or mc.get("gen_hosts") or m.get("hosts") or [])
    tree, plan = m.get("tree") or res.get("source"), m.get("plan")
    if not hosts or not tree or not plan:
        return None
    plan = plan if os.path.isabs(plan) else str(Path(tree) / plan)
    die = m.get("die") or res.get("applied")
    unit = "precheck-%s-%d" % (die, int(now or time.time()))
    return ["timeout", "60", "ssh", "-n", "-o", "ControlPath=none", hosts[0], "systemd-run", "--user", "--unit", unit, "--collect", "--quiet",
            "--nice=15", "python3", "-I", PRECHECK_RT + "/tools/precheck/precheck_hook.py", "--die", str(die), "--plan", plan,
            "--tools", str(Path(tree) / "tools/die_plan"), "--event", str(res.get("event")), "--owner", lane,
            "--kit-hosts", ",".join(hosts)] + census_args(prev, plan, tools_sha)


def census_args(prev, plan, tools_sha=""):
    p = prev or {}
    out = []
    if p.get("plan") and p["plan"] != plan:
        out += ["--prev-plan", p["plan"], "--prev-event", str(p.get("event") or "")]
        if p.get("src"):
            out += ["--prev-tools", str(Path(p["src"]) / "tools/die_plan")]
        if p.get("kit_root"):
            out += ["--prev-kits", p["kit_root"]]
    if tools_sha:
        out += ["--tools-sha", str(tools_sha)]
    return out


def candidate_bind_args(obj):
    """-> (probe args, hosts) of a bind-mode candidate, (None, []) when the candidate builds no bind"""
    m = obj.get("marker", obj)
    mc = m.get("config") or {}
    kr = A.marker_kit_rtl(m)
    if kr.get("mode") != "bind" or not kr.get("bind_out"):
        return None, []
    env = dict(m.get("die_gen_env") or {})
    return (dict(src=m["tree"], plan=m["plan"], bind_out=kr["bind_out"], asbuilt=kr.get("asbuilt") or "", scope=env.get("OT_NATIVE_RESET_SCOPE") or ""),
            list(mc.get("gen_hosts") or m.get("hosts") or []))


def bind_check(obj, run=subprocess.run):
    """-> (ok, text).  ok None = not a bind candidate; the probe runs on the first candidate host that answers"""
    return bind_check_full(obj, run)[:2]


def bind_check_full(obj, run=subprocess.run):
    """-> (ok, text, stale types): bind_check with the FULL list of types whose bind does not match (the text names six)"""
    args, hosts = candidate_bind_args(obj)
    if not args:
        return None, "no bind", []
    err = []
    for h in hosts:
        p = run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", h,
                 "python3 -I -c " + shlex.quote(PROBE_CAND) + " " + shlex.quote(json.dumps(args))], capture_output=True, text=True, timeout=900)
        line = [x for x in (p.stdout or "").splitlines() if x.startswith("AP_JSON ")]
        if not line:
            err.append(f"{h}: rc {p.returncode} {(p.stderr or '')[-160:]}")
            continue
        r = json.loads(line[-1][8:])
        if r.get("error"):
            return False, f"bind check on {h} could not run: {r['error']}", []
        if r["stale"]:
            return False, (f"bind {args['bind_out']} does not match the candidate on {len(r['stale'])}/{r['checked']} types ({h}): differs {r['diff']}; "
                           f"e.g. {', '.join(r['stale'][:6])}.  A clock_table_sha256-only difference = the asbuilt names other tables than the bind used: "
                           f"derive it from the bind (publish_apply.py derive-asbuilt --bind {args['bind_out']} --asbuilt {args['asbuilt']} --tree {args['src']} --out NEW)"), list(r["stale"])
        return True, f"bind matches the candidate on {r['checked']}/{r['checked']} types ({h})", []
    return False, "bind check: no candidate host answered: " + "; ".join(err)[:400], []


# The candidate source has already been sealed against its manifest. Read the
# same explicit bind that apply_marker will put in the wave configuration.
OUT_PROBE = r"""
import hashlib, json, os, sys
a = json.loads(sys.argv[1])
res = {}
try:
    if not os.path.isdir(a["tree"]):
        res["state"] = "no-tree"
    else:
        bind = a["bind"]
        hashes = {}
        for root, _, names in os.walk(os.path.join(bind, "rtl")):
            for name in names:
                if name.endswith((".sv", ".v")):
                    path = os.path.join(root, name)
                    with open(path, "rb") as stream:
                        hashes[os.path.relpath(path, bind)] = hashlib.sha256(stream.read()).hexdigest()
        if not hashes:
            raise ValueError("bind has no RTL modules")
        for name in ("bind_report.json", "native_topology.json"):
            path = os.path.join(bind, name)
            if name == "bind_report.json" or os.path.isfile(path):
                with open(path, "rb") as stream:
                    hashes[name] = hashlib.sha256(stream.read()).hexdigest()
        res.update(state="ok", count=len(hashes), digest=hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode()).hexdigest())
except (OSError, ValueError) as e:
    res.update(state="error", error=str(e)[:200])
print("AP_JSON " + json.dumps(res))
"""


def out_sync(obj, run=subprocess.run, hosts=None):
    """Verify identical selected bind output across the applicable replicas."""
    args, candidate_hosts = candidate_bind_args(obj)
    if not args:
        return None, ["no bind output to verify"]
    probe = dict(tree=args["src"], bind=args["bind_out"])
    lines, bad, digest = [], False, None
    for h in candidate_hosts if hosts is None else hosts:
        p = run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", h,
                 "python3 -I -c " + shlex.quote(OUT_PROBE) + " " + shlex.quote(json.dumps(probe))], capture_output=True, text=True, timeout=900)
        row = [x for x in (p.stdout or "").splitlines() if x.startswith("AP_JSON ")]
        if p.returncode or not row:
            lines.append(f"{h}: no answer (rc {p.returncode}) {(p.stderr or '')[-120:]}")
            bad = True
            continue
        result = json.loads(row[-1][8:])
        if result["state"] == "no-tree":
            bad |= hosts is not None
            lines.append(f"{h}: no tree here" + (" (checked during replication)" if hosts is None else " after replication"))
        elif result["state"] == "ok" and digest in (None, result["digest"]):
            digest = result["digest"]
            lines.append(f"{h}: selected bind verified ({result['count']} files, {digest[:12]})")
        else:
            bad = True
            why = result.get("error") or f"selected bind digest {result['digest']} != {digest}"
            lines.append(f"{h}: {why}")
    return (not bad), lines



def tree_rel(path, tree_roots):
    """an absolute file path inside one of the tree roots (or any tree: from physical/ / tools/ / rtl/ on) -> tree-relative"""
    for t in tree_roots:
        t = t.rstrip("/") + "/"
        if path.startswith(t):
            return path[len(t):]
    for marker in ("/physical/", "/tools/", "/rtl/"):
        if marker in path:
            return path[path.index(marker) + 1:]
    raise ValueError(f"{path}: not inside a source tree")


def derive_asbuilt(bind, asbuilt, tree, out):
    """FABLE-FLOW-1400 (1): the kit asbuilt the bind was ACTUALLY made with: asbuilt's clock_landing_table / land_r8 / land_r8_extra replaced by the
    sidecar / r8 / extra tables bind/INPUTS_ISOLATED.json records (tree-relative, each sha-checked in tree).  Never hand-edited.  -> the written dict"""
    import hashlib
    iso = json.loads((Path(bind) / "INPUTS_ISOLATED.json").read_text())
    a = json.loads(Path(asbuilt).read_text())

    def rel_checked(pth, sha):
        r = tree_rel(pth, [tree])
        got = hashlib.sha256((Path(tree) / r).read_bytes()).hexdigest()
        if sha and got != sha:
            raise SystemExit(f"DERIVE refuse: {r} in {tree} is {got[:12]}, the bind used {str(sha)[:12]}")
        return r
    if iso.get("sidecar"):
        a["clock_landing_table"] = rel_checked(iso["sidecar"], iso.get("sidecar_sha256"))
    if iso.get("r8"):
        a["land_r8"] = rel_checked(iso["r8"], iso.get("r8_sha256"))
    if iso.get("extra_tables"):
        a["land_r8_extra"] = [rel_checked(x["copy"], x.get("sha256")) for x in iso["extra_tables"]]
    a["derived_from_bind"] = {"bind": str(bind), "tool": "publish_apply.py derive-asbuilt (FABLE-FLOW-1400)"}
    tmp = Path(out).with_suffix(".tmp")
    tmp.write_text(json.dumps(a, indent=1) + "\n")
    os.replace(tmp, out)
    return a


def cmd_derive(a):
    d = derive_asbuilt(a.bind, a.asbuilt, a.tree, a.out)
    print(json.dumps({k: d.get(k) for k in ("clock_landing_table", "land_r8", "land_r8_extra")}, indent=1))
    print(f"DERIVED {a.out}: add it to the tree (live-tree pack), point kit_rtl.asbuilt at it; the bind receipt's asbuilt_sha256 names the asbuilt the bind was run with")
    return 0


# S81-DIE-R3 11-18 (COORD): the post-apply strict bind + LATCHECK run in a hardlink copy this tool makes, never in the tree a lane composed.
# D8f: bind r4 ran in <tree>_work while the publish renamed it to _work_live; the bind's absolute paths re-created _work (delta-apply refused the
# publish) and the bind died (ModuleNotFoundError, its tools path was gone).  The copy is a SIBLING of the published tree whose .link-base names it
# (src_manifest.linked_children: the shared inodes are accounted, the published tree still verifies --ro).  Every shared file stays read-only, so an
# in-place write fails instead of reaching the tree; the bind and LATCHECK write only under <copy>/_postbind/ (fresh files).
POSTBIND_MEM = int(os.environ.get("OT_POSTBIND_MEM", "96"))
POSTBIND_DIR = "_postbind"


def _rel(p, tree):
    return p if not os.path.isabs(p) else tree_rel(p, [tree])


BIND_NO_PROGRESS_S = int(os.environ.get("OT_BIND_NO_PROGRESS_S", "3600"))


def bind_env_of(obj, live=None):
    """COORD 11-19 (KV): the env the die's strict bind needs = every OT_* of the live die config (die_gen_env, bind_env) under the candidate marker's own
    die_gen_env / bind_env (the plan's values win).  The bind reads e.g. OT_KV_HEAD_KST, OT_HCPARAM_ALL, OT_NATIVE_RESET_SCOPE from the environment."""
    m = obj.get("marker", obj)
    env = {}
    for src in (live or {}, m):
        for blk in ("die_gen_env", "bind_env"):
            for k, v in (src.get(blk) or {}).items():
                if str(k).startswith("OT_") and isinstance(v, (str, int, float)) and not isinstance(v, bool):
                    env[str(k)] = str(v)
    return env


def live_die_cfg(C, die):
    try:
        return (json.loads((Path(C) / "autopilot/kit_wave.json").read_text()).get("dies") or {}).get(die) or {}
    except (OSError, ValueError):
        return {}


def write_published_event_env(coord, applied, cfg):
    """Write the adopted event's default inputs once; the die owner can keep a hand-authored file."""
    event = applied.get("event")
    source = applied.get("source")
    if not event or cfg.get("event") != event or cfg.get("src") != source:
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", event):
        raise EE.EventEnvError(f"event has no safe env filename: {event!r}")
    dest = Path(coord) / "events" / f"{event}.env"
    if dest.exists():
        return None
    pin = str(cfg.get("gen_tools_pin") or cfg.get("tools_sha") or "")
    if not re.fullmatch(r"[0-9a-f]{12}([0-9a-f]{28})?", pin):
        raise EE.EventEnvError(f"{event}: a versioned tools pin is required")
    args = [source]
    kit = cfg.get("kit_rtl") or {}
    bind = kit.get("bind_out") or cfg.get("bind_out")
    if bind:
        args.append(bind)
    values = {key: value for key, value in bind_env_of(cfg).items()
              if key not in EE.META and key != "OT_TOOLSTALE_RT"}
    values.update(OT_EVENT=event, OT_EVENT_RT=pin[:12], OT_EVENT_INPUTS=",".join(dict.fromkeys(args)),
                  OT_RUN_PREFLIGHT="fail")
    data = ("# Generated from the adopted wave configuration. The die owner may edit this file.\n"
            + "".join(f"{key}={value}\n" for key, value in sorted(values.items())))
    if EE.parse(data, where=str(dest)) != values:
        raise EE.EventEnvError(f"{event}: an environment value cannot be represented literally")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=dest.parent, encoding="utf-8") as tmp:
        tmp.write(data)
        tmp.flush()
        os.chmod(tmp.name, 0o644)
        try:
            os.link(tmp.name, dest)
        except FileExistsError:
            return None
    return dest


def postbind_spec(obj, stamp, host="", live=None):
    """-> {host, tree, copy, plan, asbuilt, env, run_dir} for a bind-mode candidate (paths in the copy tree-relative), None when it builds no bind"""
    args, hosts = candidate_bind_args(obj)
    if not args or not (host or hosts):
        return None
    tree = args["src"].rstrip("/")
    env = bind_env_of(obj, live)
    if args["scope"]:
        env["OT_NATIVE_RESET_SCOPE"] = args["scope"]
    marker = obj.get("marker", obj)
    remap_base = marker.get("remap_base") or obj.get("remap_base")
    if remap_base:
        env["OT_PLAN_GATE_BASELINE"] = str(remap_base)
    # P-POSTBIND-PROOF-DROP (QC C9 11-26): the candidate's rows proofs (tree-relative) reach the bind's PRE (bind.py reads OT_PRE_ROWS_PROOFS);
    # without them the strict bind refused ROWS-NO-PROOF on rows the candidate carries a proof for
    proofs = [str(x) for x in (marker.get("rows_proofs") or obj.get("rows_proofs") or [])]
    if proofs:
        env["OT_PRE_ROWS_PROOFS"] = os.pathsep.join(_rel(x, tree) if os.path.isabs(x) else x for x in proofs)
    cfg = {**(live or {}), **(marker.get("config") or {})}
    pin = ""
    if cfg.get("tools_from_rt") is not False:
        pin = str(cfg.get("gen_tools_pin") or marker.get("tools_sha") or cfg.get("tools_sha") or "")
        if pin and not re.fullmatch(r"[0-9a-f]{12}([0-9a-f]{28})?", pin):
            raise ValueError(f"post-bind: invalid tools pin {pin!r}")
    spec = {"host": host or hosts[0], "tree": tree, "copy": f"{tree}_postbind_{stamp}", "plan": _rel(args["plan"], tree),
            "asbuilt": _rel(args["asbuilt"], tree) if args["asbuilt"] else "", "env": env,
            "bind_out": args["bind_out"], "tools_sha": pin,
            "tools_rt_root": str(cfg.get("tools_rt_root") or "/srv/opentallas-scratch2/claude/rt")}


    if (marker.get("manifest_hash") or marker.get("src_manifest_sha")) and marker.get("plan_sha256"):
        spec["receipt_inputs"] = PBR.receipt_inputs(spec, marker)
    return spec


def postbind_parallel_check_sh(binder, identity, rt_root=""):
    """Read the whole-die no-serial guard from the exact binder before building.  The refusal names the CURRENT parallel-capable runtime pin of
    <rt_root>/current when it has the guard (QC C9 post-bind, 11-26: the inherited pin 45bb7d41e172 refused with no way forward); it is a
    hint only, never selected automatically."""
    q = shlex.quote
    hint = ""
    if rt_root:
        cur = f"$(readlink -f -- {q(rt_root)}/current 2>/dev/null)"
        hint = (f"hint=\ncur={cur} || cur=\n"
                "if [ -n \"$cur\" ] && grep -Fq -- 'BIND_PARALLEL_REQUIRED: whole-die emit' \"$cur/tools/die_plan/bind.py\" 2>/dev/null; then\n"
                "    hint=\" Current parallel-capable pin: $(basename \"$cur\") (set the candidate's config.gen_tools_pin / marker.tools_sha to it; "
                "it is not selected automatically).\"\nfi\n")
    return (f"if ! grep -Fq -- 'BIND_PARALLEL_REQUIRED: whole-die emit' {binder} 2>/dev/null; then\n"
            + hint
            + f"    printf 'POSTBIND_PARALLEL_REQUIRED %s lacks the whole-die parallel bind guard. "
            f"Select and qualify a parallel-compatible tools pin or sealed checkout before retrying.%s\\n' {identity} \"${{hint:-}}\" >&2\n"
            "    exit 6\nfi\n")


def postbind_runtime_sh(s, *, require_parallel=False):
    """Compose the checked-out design with the exact published tools on the bind host."""
    q = shlex.quote
    pin = s.get("tools_sha")
    if not pin:
        if not require_parallel:
            return ""
        return postbind_parallel_check_sh(q(s["tree"] + "/tools/die_plan/bind.py"), q("checkout " + s["tree"]), s.get("tools_rt_root", ""))
    root = q(s["tools_rt_root"])
    manifest_sha = q("import json,sys; print(json.load(open(sys.argv[1]))['sha'])")
    select = (f"tool_root={root}\n"
            "resolved=$(readlink -f -- \"$tool_root/current\") || resolved=\"$tool_root/current\"\n"
            "resolved_root=$(dirname -- \"$resolved\")\n"
            f"pin={q(pin)}\n"
            "runtime=\n"
            "for root in \"$tool_root\" \"$resolved_root\"; do\n"
            "    candidate=\"$root/${pin:0:12}\"\n"
            "    [ -r \"$candidate.manifest.json\" ] && [ -r \"$candidate/tools/die_plan/bind.py\" ] || continue\n"
            f"    actual=$(python3 -I -c {manifest_sha} \"$candidate.manifest.json\") || continue\n"
            "    case \"$actual\" in \"$pin\"*) runtime=$candidate; break;; esac\n"
            "done\n"
            "[ -n \"$runtime\" ] || { echo \"POSTBIND_RUNTIME unavailable pin $pin in $tool_root or $resolved_root\" >&2; exit 6; }\n")
    if require_parallel:
        return select + postbind_parallel_check_sh('"$runtime/tools/die_plan/bind.py"', '"pin $pin ($runtime)"', s.get("tools_rt_root", ""))
    copy = q(s["copy"])
    launch = q(f"{s['copy']}/{POSTBIND_DIR}/launch")
    return (select
            + f"launch={launch}\n"
            + f"if ! bash \"$runtime/tools/autopilot/rt_launch_tree.sh\" {copy} \"$runtime\" \"$launch\"; then\n"
              "    echo \"POSTBIND_RUNTIME could not compose pin $pin in $launch\" >&2; exit 6\n"
              "fi\n"
            + f"export OT_REPO_ROOT=\"$launch\" OT_PLAN_ROOT=\"$(realpath -- \"$(dirname -- {q(s['plan'])})\")\" OT_RT_CURRENT=\"$runtime\"\n"
            "echo \"POSTBIND_RUNTIME $pin $runtime\"\n")


def postbind_run_sh(s):
    """the job ot-run starts in the copy: strict elab + bind into _postbind/out, then LATCHECK on that bind (outputs under _postbind only)"""
    q = shlex.quote
    L = f"{s['copy']}/{POSTBIND_DIR}"
    ab = f" --asbuilt {q(s['asbuilt'])}" if s["asbuilt"] else ""
    env = "".join(f"export {k}={q(v)}\n" for k, v in sorted(s["env"].items()))
    runtime = postbind_runtime_sh(s)

    tools = '"$runtime"/tools/die_plan' if runtime else "tools/die_plan"
    inputs_name = q(str(Path(L) / PBR.INPUT))
    result_name = q(str(Path(L) / PBR.RESULT))
    inputs = s.get("receipt_inputs")
    record_inputs = f"printf '%s\\n' {q(json.dumps(inputs, sort_keys=True))} > {inputs_name} || exit 6\n" if inputs else ""
    record_result = f"""printf '{{"elab":%s,"bind":%s,"latcheck":%s}}\\n' "$e" "$b" "$l" > {result_name} || exit 6\n""" if inputs else ""
    return (f"#!/bin/bash\n# publish_apply.py post-bind: strict bind + LATCHECK of {s['tree']} in its hardlink copy\nset -uo pipefail\n"
            "export PYTHONDONTWRITEBYTECODE=1\n"
            f"{env}"
            # Older pinned runtimes still bound auto workers by JMAX. Preserve an explicit lower cap.
            'export OT_BIND_EMIT_JMAX="${OT_BIND_EMIT_JMAX:-${OT_HEAVY_THREADS:-8}}"\n'
            f"cd {q(s['copy'])} || exit 6\n{runtime}mkdir -p {q(L)}/out\n"
            f"{record_inputs}"
            f"python3 -I -B {tools}/bind.py elab {q(s['plan'])}{ab} --out {q(L)}/out --strict --mem {POSTBIND_MEM} > {q(L)}/elab.log 2>&1\n"
            f"e=$?; echo ELAB_RC=$e; tail -n 1 {q(L)}/elab.log | cut -c1-300\n"
            f"python3 -I -B {tools}/bind.py bind {q(s['plan'])}{ab} --out {q(L)}/out --strict > {q(L)}/bind.log 2>&1\n"
            f"b=$?; echo BIND_RC=$b; tail -n 2 {q(L)}/bind.log | cut -c1-600\n"
            f"[ $b = 0 ] || grep -E '^ +[A-Z_]+ ' {q(L)}/bind.log | head -20 | cut -c1-600\n"
            f"python3 -I -B {tools}/lane_asbuilt_latency.py {q(L)}/out {q(s['plan'])}{ab} --pricing as-bound --tsv {q(L)}/latcheck.tsv "
            f"--json {q(L)}/latcheck.json > {q(L)}/latcheck.log 2>&1\n"
            f"l=$?; echo LATCHECK_RC=$l; tail -n 2 {q(L)}/latcheck.log | cut -c1-300\n"
            f"{record_result}"
            f"echo POSTBIND_DONE elab $e bind $b latcheck $l\nexit $(( e || b || l ))\n")


def postbind_prep_sh(s):
    """host side, ONE ssh: cp -al the published tree to <copy>.part, make the copy's own dirs writable, declare .link-base (rename, never a write
    through a shared inode), write _postbind/run.sh, rename to <copy>.  Refuses when the tree is not a manifest tree or the copy exists."""
    q = shlex.quote
    T, Cp = q(s["tree"]), q(s["copy"])
    return (f"set -euo pipefail\ncd /\ntest -f {T}/.src-manifest.json\ntest ! -e {Cp}\ntest ! -e {Cp}.part\n"
            + postbind_runtime_sh(s, require_parallel=True)
            + f"cp -al {T} {Cp}.part\nfind {Cp}.part -type d -exec chmod u+w {{}} +\n"
            f"realpath {T} > {Cp}.part/.link-base.tmp\nchmod 444 {Cp}.part/.link-base.tmp\nmv -f {Cp}.part/.link-base.tmp {Cp}.part/.link-base\n"
            f"mkdir {Cp}.part/{POSTBIND_DIR}\n"
            f"cat > {Cp}.part/{POSTBIND_DIR}/run.sh <<'OT_POSTBIND_EOF'\n{postbind_run_sh(s)}OT_POSTBIND_EOF\n"
            f"mv {Cp}.part {Cp}\necho POSTBIND_COPY {Cp}\n")


def start_postbind(C, obj, lane, die, run=subprocess.run, host="", stamp=None, log_dir=None, auto_adopt=True):
    """start the post-apply strict bind + LATCHECK as a hub user unit: ssh-prep the copy, ot-run the job there (plan/bind admission), post the result.
    -> (unit or None, text)"""
    stamp = stamp or time.strftime("%m%d%H%M%S")
    live = live_die_cfg(C, die)
    if not auto_adopt:
        live = publication_live_cfg(obj, live)
    s = postbind_spec(obj, stamp, host, live)
    if not s:
        return None, "no bind (candidate is not kit_rtl mode bind)"
    ld = Path(log_dir or os.path.expanduser("~/.local/state/ot-postbind"))
    ld.mkdir(parents=True, exist_ok=True)
    unit = f"postbind-{die}-{stamp}"
    prep, log = ld / f"{unit}.prep.sh", ld / f"{unit}.log"
    prep.write_text(postbind_prep_sh(s))
    q = shlex.quote
    otrun = HERE.parent / "fleet" / "ot-run"
    fail = (f"publish_apply.py bind-fail --die {die} --lane {lane} --id {unit} --log {log}")
    # the prep script goes over ssh STDIN: never `ssh -n` here (D8f 11-19: -n fed bash -s /dev/null, no copy, ot-run NOT RUN); the copy
    # counts as made only when the script's last line POSTBIND_COPY arrived
    body = (f"cd /; {{ ssh -o BatchMode=yes -o ControlPath=none {q(s['host'])} 'bash -s' < {q(str(prep))} > {q(str(log))} 2>&1 && "
            f"grep -q '^POSTBIND_COPY ' {q(str(log))}; }} || "
            f"{{ reason=$(grep -m1 '^POSTBIND_PARALLEL_REQUIRED ' {q(str(log))}) || reason='the bind copy could not be made'; "
            f"bash {q(str(Path(C) / 'bin/post.sh'))} {q(lane)} \"POST-APPLY-BIND [{lane} -> COORD] {die} on {s['host']}: $reason (log {log})\"; exit 3; }}\n"
            f"{q(str(otrun))} --mem {POSTBIND_MEM} --threads 48 --hosts {q(s['host'])} --priority plan --plan-job bind --dir {q(s['copy'])} --stage {q(s['copy'])} "
            f"--stage {q(s['tree'])} -- bash {q(s['copy'] + '/' + POSTBIND_DIR + '/run.sh')} >> {q(str(log))} 2>&1; rc=$?\n"
            f"r=$(grep -E '^(ELAB|BIND|LATCHECK)_RC=' {q(str(log))} | tr '\\n' ' ')\n"
            f"if [ $rc = 0 ]; then v=PASS; else v=\"FAIL (rc $rc): run {fail}\"; fi\n"
            f"bash {q(str(Path(C) / 'bin/post.sh'))} {q(lane)} \"POST-APPLY-BIND [{lane} -> COORD] {die} tree {s['tree']}: strict bind + LATCHECK in hardlink copy "
            f"{s['copy']} on {s['host']}: $r-> $v; log hub:{log}\"\n"
            + (f"[ $rc = 0 ] && python3 -I {q(str(HERE / 'publish_apply.py'))} adopt-bind --die {die} --lane {q(lane)} --tree {q(s['tree'])} --copy {q(s['copy'])} --host {q(s['host'])} "
               f"--id {unit} --coord {q(str(C))} >> {q(str(log))} 2>&1\n" if auto_adopt else ""))
    r = run(["systemd-run", "--user", "--unit", unit, "--collect", "--quiet", "--nice=5", "bash", "-c", body], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None, "post-apply bind not started (rc %d: %s)" % (r.returncode, (r.stderr or r.stdout)[-160:])
    return unit, f"post-apply strict bind + LATCHECK unit {unit} in hardlink copy {s['copy']} on {s['host']} (log {log})"


# COORD 11-19 (structural; S81-DIE-R3 owns the post-bind): publish / apply never carried the bind output, so after every plan event kit_rtl.bind_out kept pointing at the OLD bind and the kits
# failed KIT_TOPOLOGY_BIND_STALE until someone hand-published.  adopt-bind closes the loop when the post-apply bind is GREEN: its output (<copy>/_postbind/out, fresh files, the only part of the copy
# the bind wrote) is sealed (read-only) as <tree>_bind_<stamp> on the bind host, replicated to every other gen host of the die, checked with kit_topology.bind_matches against the die's live plan, and
# only then dies.<die>.kit_rtl.bind_out (and every item_inputs bind_out that still named the old bind) is switched to it in ONE CAS commit (kit_wave_edit).  This does not compose a new tree: the
# tree is unchanged, so no manifest hash, event or tools change; a child tree is only needed when the bind must travel INSIDE the tree.  A bind that does not match the plan on every type switches
# nothing and bind-fails ONLY the types that differ.
BIND_DEST_SUFFIX = "_bind_"


def adopt_bind_plan(cfg, die, tree, copy, stamp, host):
    """-> dict(out, dest, hosts, old_bind, patch) for dies.<die>: out = the bind the post-bind wrote, dest = its sealed name beside the tree, patch = the kit_wave_edit ops that repoint the die
    and every item_inputs bind_out that named the same old bind; None when the die has no bind-mode kit_rtl"""
    d = (cfg.get("dies") or {}).get(die) or {}
    kr = d.get("kit_rtl") or {}
    if kr.get("mode") != "bind" or not kr.get("bind_out"):
        return None
    dest = f"{tree.rstrip('/')}{BIND_DEST_SUFFIX}{stamp}"
    old = kr["bind_out"]
    ops = [{"op": "replace", "path": f"/dies/{die}/kit_rtl/bind_out", "value": dest}]
    for item, ii in sorted((d.get("item_inputs") or {}).items()):
        if isinstance(ii, dict) and isinstance((ii.get("kit_rtl") or {}).get("bind_out"), str) and ii["kit_rtl"]["bind_out"] == old:
            ops.append({"op": "replace", "path": f"/dies/{die}/item_inputs/{item.replace('~', '~0').replace('/', '~1')}/kit_rtl/bind_out", "value": dest})
    hosts = [h for h in (d.get("gen_hosts") or []) if h != host]
    return dict(out=f"{copy.rstrip('/')}/{POSTBIND_DIR}/out", dest=dest, hosts=hosts, old_bind=old, patch=ops)


def adopt_bind_seal_sh(plan_):
    """host side (the bind host): the bind output must be there and complete, then it is copied (fresh files) to <dest>.part, made read-only and renamed; an existing dest is left alone"""
    q = shlex.quote
    o, d = q(plan_["out"]), q(plan_["dest"])
    return (f"set -euo pipefail\ntest -f {o}/native_topology.json\nif [ -e {d} ]; then echo ADOPT_SEAL exists {d}; exit 0; fi\ntest ! -e {d}.part\n"
            f"cp -a {o} {d}.part\nchmod -R a-w {d}.part\nmv {d}.part {d}\necho ADOPT_SEAL {d}\n")


def bind_copy_of_record(cfg, copy):
    old = [path for path in cfg.get("bind_copy_of_record") or [] if isinstance(path, str) and path != copy]
    return [copy] + old[:3]


def adopt_bind_candidate(cfg, die, dest):
    """the candidate shape bind_check reads: the die's live tree and plan with the NEW bind_out"""
    d = cfg["dies"][die]
    kr = dict(d.get("kit_rtl") or {})
    kr["bind_out"] = dest
    return {"marker": {"tree": d["src"], "plan": d["plan"], "die_gen_env": d.get("die_gen_env") or {}, "hosts": d.get("gen_hosts") or [],
                       "config": {"kit_rtl": kr, "gen_hosts": d.get("gen_hosts") or []}}}


def cmd_adopt_bind(a, run=subprocess.run, check_fn=None):
    """publish_apply.py adopt-bind --die D --lane L --tree TREE --copy COPY --host H --id ID: see the block comment above.  rc 0 switched (or already current), 1 bind did not match (those types
    are bind-failed), 2 nothing to do / a step failed (nothing switched)"""
    C = Path(a.coord)
    cfg = json.loads((C / "autopilot/kit_wave.json").read_text())
    plan_ = adopt_bind_plan(cfg, a.die, a.tree, a.copy, a.stamp or time.strftime("%m%d%H%M%S"), a.host)
    if not plan_:
        print(f"ADOPT-BIND {a.die}: no bind-mode kit_rtl; nothing to adopt")
        return 2
    sh = lambda host, script: run(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", host, "bash -s"], input=script, capture_output=True, text=True, timeout=1800)
    r = sh(a.host, adopt_bind_seal_sh(plan_))
    if r.returncode or "ADOPT_SEAL" not in (r.stdout or ""):
        print(f"ADOPT-BIND {a.die}: sealing the bind output on {a.host} failed rc {r.returncode}: {(r.stderr or r.stdout)[-200:]}; nothing switched")
        return 2
    e = "ssh -o BatchMode=yes -o ControlPath=none -o ConnectTimeout=15"
    out_ = shlex.quote(plan_["out"] + "/")
    for h in plan_["hosts"]:
        # SNAP-RO-1119 (FABLE-FLOW-0035): the kits name HDL files INSIDE the post-bind copy (<copy>/_postbind/out/rtl/...); the sealed bind alone left the copy on the bind host only
        # (QC n46_s1_postbind and KV D25e: SRC-INCOMPLETE on every other gen host).  Both travel, to the same paths.
        r = run(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", a.host,
                 f"ssh -n -o BatchMode=yes -o ControlPath=none {h} {shlex.quote('mkdir -p ' + shlex.quote(plan_['out']))} && rsync -a -e {shlex.quote(e)} {out_} {h}:{out_} && "
                 f"rsync -a -e {shlex.quote(e)} {shlex.quote(plan_['dest'] + '/')} {h}:{shlex.quote(plan_['dest'] + '/')}"], capture_output=True, text=True, timeout=1800)
        if r.returncode:
            print(f"ADOPT-BIND {a.die}: replicating the bind to {h} failed rc {r.returncode}: {(r.stderr or r.stdout)[-200:]}; nothing switched")
            return 2
    # the same all-host proof as the apply (verify_tree_on_all_hosts): the sealed bind and the post-bind rtl are on EVERY gen host before kit_rtl.bind_out moves
    bad = []
    for h in [a.host] + list(plan_["hosts"]):
        r = run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", h,
                 f"test -f {shlex.quote(plan_['dest'] + '/native_topology.json')} && test -d {shlex.quote(plan_['out'])} && "
                 f"{{ test ! -d {shlex.quote(plan_['out'] + '/rtl')} || test -n \"$(ls -A {shlex.quote(plan_['out'] + '/rtl')} | head -1)\"; }}"], capture_output=True, text=True, timeout=300)
        if r.returncode:
            bad.append(f"{h} (rc {r.returncode})")
    if bad:
        print(f"ADOPT-BIND {a.die}: the sealed bind {plan_['dest']} or the post-bind copy {plan_['out']} is not complete on {', '.join(bad)}; nothing switched")
        return 2
    ok, txt = (check_fn or bind_check)(adopt_bind_candidate(cfg, a.die, plan_["dest"]), run=run)
    print(f"ADOPT-BIND {a.die}: {txt}")
    if ok is not True:
        types = re.findall(r"e\.g\. ([^;]+?)\.", txt)
        names = [t.strip() for t in (types[0].split(",") if types else []) if t.strip()]
        post(C, a.lane, f"ADOPT-BIND-FAIL [{a.lane} -> {a.lane}] {a.die}: the post-bind output {plan_['dest']} does not match the live plan ({txt[:300]}); kit_rtl.bind_out NOT switched; "
                        f"bind-failing {len(names)} named type(s)", run=run)
        if names:
            run([sys.executable, "-I", str(HERE / "publish_apply.py"), "bind-fail", "--die", a.die, "--lane", a.lane, "--id", a.id or "adopt-bind", "--types", ",".join(names),
                 "--coord", str(C)], capture_output=True, text=True, timeout=600)
        return 1
    n_items = len(plan_["patch"]) - 1
    # a bind of record's source copy is a live reference: any absolute scratch path in a die block is on the delete guard's protected list (build_protected walks every key), so the copy is
    # registered under dies.<die>.bind_copy_of_record (newest 4, like bound_trees); a lane can no longer delete the tree the bind of record reads (KV D25e)
    plan_["patch"] += [{"op": "add", "path": f"/dies/{a.die}/bind_copy_of_record", "value": bind_copy_of_record(cfg["dies"][a.die], a.copy)}]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(plan_["patch"], f)
    r = run([sys.executable, "-I", str(HERE / "kit_wave_edit.py"), "--coord", str(C), "--message",
             f"{a.lane}: adopt post-bind output as kit_rtl.bind_out of {a.die} ({Path(plan_['dest']).name}; was {Path(plan_['old_bind']).name})", "--patch-file", f.name],
            capture_output=True, text=True, timeout=600)
    os.unlink(f.name)
    if r.returncode:
        print(f"ADOPT-BIND {a.die}: the kit_wave.json edit failed: {(r.stdout + r.stderr)[-300:]}")
        return 2
    post(C, a.lane, f"ADOPT-BIND [{a.lane} -> COORD] {a.die}: post-bind GREEN and matching on every type; kit_rtl.bind_out {plan_['old_bind']} -> {plan_['dest']} "
                    f"({n_items} item_inputs repointed, hosts {a.host},{','.join(plan_['hosts'])}); the BIND-STALE rows relaunch on the next wave pass", run=run)
    return 0


def postbind_wait_sh(spec, log):
    """Wait for the exact local launcher, observing files and its scope on the bind host."""
    q = shlex.quote
    postbind = q(f"{spec['copy']}/{POSTBIND_DIR}")
    remote = f"""dir={postbind}
stamp=$(stat -c '%Y:%s' "$dir"/*.log "$dir"/out/* 2>/dev/null | sort -t: -k1,1n -k2,2n | tail -1)
cpu=0
if [ -n "$1" ]; then
    cpu=$(systemctl --user show --property=CPUUsageNSec --value "$1.scope" 2>/dev/null)
fi
printf '%s %s\\n' "${{stamp:-0:0}}" "${{cpu:-0}}"
"""
    probe = q("bash -c " + q(remote) + " --")
    return f"""pid=$!
log={q(str(log))}
probe={probe}
last_progress=$(date +%s)
last_local=
last_remote=
last_cpu=0
last_scope=
while kill -0 "$pid" 2>/dev/null; do
    sleep 60
    kill -0 "$pid" 2>/dev/null || break
    now=$(date +%s)
    local_stamp=$(stat -c '%Y:%s' "$log" 2>/dev/null)
    scope=$(sed -nE 's/^ot-heavy:.* as (oth-[A-Za-z0-9_-]+) after.*$/\\1/p' "$log" | tail -1)
    if [ "$local_stamp" != "$last_local" ] && [ -n "$local_stamp" ]; then
        last_progress=$now
        last_local=$local_stamp
    fi
    observed=$(timeout 30s ssh -n -o BatchMode=yes -o ControlPath=none -o ConnectTimeout=10 \
        {q(spec['host'])} "$probe $scope" 2>/dev/null) || observed=
    if [ -n "$observed" ]; then
        read -r remote_stamp cpu <<< "$observed"
        if [ "$remote_stamp" != 0:0 ] && [ "$remote_stamp" != "$last_remote" ]; then
            last_progress=$now
            last_remote=$remote_stamp
        fi
        if [ "$scope" != "$last_scope" ]; then
            last_scope=$scope
            last_cpu=0
        fi
        if [[ "$cpu" =~ ^[0-9]+$ ]] && [ "$cpu" -gt "$last_cpu" ]; then
            last_progress=$now
            last_cpu=$cpu
        fi
    fi
    if [ "$(( now - last_progress ))" -gt {BIND_NO_PROGRESS_S} ]; then
        echo "BIND-NO-PROGRESS {BIND_NO_PROGRESS_S}s: stopping ot-run $pid" >> "$log"
        kill "$pid" 2>/dev/null
        break
    fi
done
wait "$pid"
"""


def bind_first(C, obj, lane, die, run=subprocess.run, host="", stamp=None, log_dir=None):
    """COORD 11-19 (FABLE-FLOW-0358 A, other half): run the strict bind + LATCHECK of the candidate's PUBLISHED tree in its hardlink copy BEFORE the apply and wait for it (the old tree keeps building
    meanwhile: an ordering, not a hold), seal its output beside the tree and replicate it to the other gen hosts.  -> (dest or '', text, failing types from the bind log).  '' = no bind output:
    the caller does not switch (the tree stays as it is)"""
    stamp = stamp or time.strftime("%m%d%H%M%S")
    s = postbind_spec(obj, stamp, host, live_die_cfg(C, die))
    if not s:
        return "", "no bind (candidate is not kit_rtl mode bind)", []
    ld = Path(log_dir or os.path.expanduser("~/.local/state/ot-postbind"))
    ld.mkdir(parents=True, exist_ok=True)
    unit = f"bindfirst-{die}-{stamp}"
    prep, log = ld / f"{unit}.prep.sh", ld / f"{unit}.log"
    prep.write_text(postbind_prep_sh(s))
    q = shlex.quote
    otrun = HERE.parent / "fleet" / "ot-run"
    body = (f"cd /; {{ ssh -o BatchMode=yes -o ControlPath=none {q(s['host'])} 'bash -s' < {q(str(prep))} > {q(str(log))} 2>&1 && grep -q '^POSTBIND_COPY ' {q(str(log))}; }} || exit 3\n"
            f"{q(str(otrun))} --mem {POSTBIND_MEM} --threads 48 --hosts {q(s['host'])} --priority plan --plan-job bind --dir {q(s['copy'])} --stage {q(s['copy'])} "
            f"--stage {q(s['tree'])} -- bash {q(s['copy'] + '/' + POSTBIND_DIR + '/run.sh')} >> {q(str(log))} 2>&1 &\n"
            + postbind_wait_sh(s, log))
    r = run(["bash", "-c", body], capture_output=True, text=True, timeout=None)
    txt = ""
    try:
        txt = Path(log).read_text(errors="replace")
    except OSError:
        pass
    if r.returncode and (refusal := re.search(r"^POSTBIND_PARALLEL_REQUIRED .+$", txt, re.M)):
        return "", "bind-first: " + refusal[0], []
    fails = types_from_log(txt, set(item_names((json.loads((Path(C) / "autopilot/kit_wave.json").read_text()).get("dies") or {}).get(die) or {})))
    plan_ = dict(out=f"{s['copy']}/{POSTBIND_DIR}/out", dest=f"{s['tree'].rstrip('/')}{BIND_DEST_SUFFIX}{stamp}", hosts=list(((obj.get("marker") or obj).get("config") or {}).get("gen_hosts") or [])[:])
    plan_["hosts"] = [h for h in plan_["hosts"] if h != s["host"]]
    sh = lambda host, script: run(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", host, "bash -s"], input=script, capture_output=True, text=True, timeout=1800)
    seal = sh(s["host"], adopt_bind_seal_sh(plan_))
    if seal.returncode or "ADOPT_SEAL" not in (seal.stdout or ""):
        return "", f"bind-first: no bind output ({'bind rc ' + str(r.returncode)}; seal on {s['host']} failed): {(seal.stderr or seal.stdout)[-160:]}", fails
    e = "ssh -o BatchMode=yes -o ControlPath=none -o ConnectTimeout=15"
    for h in plan_["hosts"]:
        rr = run(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", s["host"], f"rsync -a -e {q(e)} {q(plan_['dest'] + '/')} {h}:{q(plan_['dest'] + '/')}"], capture_output=True, text=True, timeout=1800)
        if rr.returncode:
            return "", f"bind-first: replicating the bind to {h} failed rc {rr.returncode}", fails
    for h in [s["host"]] + plan_["hosts"]:                # FABLE-FLOW-0555 A: a tree never becomes the die's tree without a bind report on every gen host
        rr = run(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", h, f"test -f {q(plan_['dest'] + '/bind_report.json')}"], capture_output=True, text=True, timeout=300)
        if rr.returncode:
            return "", f"bind-first: no bind_report.json in {plan_['dest']} on {h}; the die keeps its tree", fails
    return plan_["dest"], f"bind-first: strict bind + LATCHECK rc {r.returncode}; output sealed as {plan_['dest']} on {s['host']},{','.join(plan_['hosts'])}", fails


def with_bind_out(obj, dest):
    """a copy of the candidate whose marker names `dest` as the bind (apply_marker writes kit_rtl.bind_out from marker.bind_out + asbuilt, in the same commit as the tree)"""
    o = json.loads(json.dumps(obj))
    m = o.get("marker", o)
    kr = (m.setdefault("config", {}).setdefault("kit_rtl", {}))
    kr["bind_out"] = dest
    if kr.get("asbuilt"):
        m["asbuilt"], m["bind_out"] = kr["asbuilt"], dest
    return o


def cmd_post_bind(a, run=subprocess.run):
    obj = json.loads(Path(a.candidate).read_text())
    m = obj.get("marker", obj)
    unit, txt = start_postbind(a.coord, obj, a.lane, a.die or obj.get("die") or m.get("die") or "die", run=run, host=a.host or "", auto_adopt=not getattr(a, "no_auto_adopt", False))
    print(f"POST-BIND {txt}")
    return 0 if unit else 2


class SelectedBindVerificationError(Exception):
    pass


def postbind_required_problem(obj, no_post_bind=False):
    """-> text when the candidate cannot get a post-apply strict bind + LATCHECK (fail closed), else ''"""
    if no_post_bind:
        return "--no-post-bind: the apply would run no post-apply strict bind + LATCHECK"
    kr = A.marker_kit_rtl(obj.get("marker", obj))
    if kr.get("mode") != "bind" or not kr.get("bind_out"):
        return f"the candidate's kit_rtl is not bind mode (mode {kr.get('mode')!r}): no post-apply strict bind + LATCHECK can run"
    return ""


def publication_live_cfg(obj, live):
    """Project the same plan-sensitive config apply_marker will use after its source switch."""
    marker = obj.get("marker", obj)
    data = json.loads(json.dumps(live))
    HR._deep_set(data, marker.get("config") or {})
    HR._deep_set(data.setdefault("die_gen_env", {}), marker.get("die_gen_env") or {})
    A.repoint_gen_env(data, live.get("src"), marker["tree"], exists=lambda _: True)
    return data


def publication_receipt_spec(obj, live):
    # A fallback tree-relative match is useful to the normal bind worker, but a
    # reusable receipt must attest the exact files the publication will read.
    args, _hosts = candidate_bind_args(obj)
    if not args:
        raise ValueError("receipt candidate has no selected bind")
    tree = Path(args["src"])
    if any(not Path(args[key]).is_absolute() or not Path(args[key]).is_relative_to(tree) or ".." in Path(args[key]).parts
           for key in ("plan", "asbuilt")):
        raise ValueError("receipt plan and asbuilt must be inside the selected source tree")
    spec = postbind_spec(obj, "reuse", live=live)
    if not spec or not spec.get("receipt_inputs") or not spec.get("tools_sha"):
        raise ValueError("receipt requires source and plan hashes, pinned tools, and generation hosts")
    return spec


def verify_reusable_bind(obj, live, expected, hosts=None, run=subprocess.run):
    """Verify one exact sealed producer receipt and its local enrollment on every generation host."""
    spec = publication_receipt_spec(obj, live)
    _args, candidates = candidate_bind_args(obj)
    if not spec or not spec.get("receipt_inputs") or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("post-bind receipt requires a sealed bind-mode candidate and a full producer SHA-256")
    bind = Path(spec["bind_out"])
    if not bind.is_absolute() or bind.name != "out" or bind.parent.name != POSTBIND_DIR:
        raise ValueError("the selected bind must be the immutable producer's _postbind/out")
    hosts = list(dict.fromkeys(candidates if hosts is None else hosts))
    if not hosts:
        raise ValueError("no generation hosts for post-bind receipt")
    arg = dict(bind=str(bind), inputs=spec["receipt_inputs"], expected=expected)
    source = Path(PBR.__file__).read_text().split('if __name__ == "__main__":', 1)[0] + """
import sys
try:
    a = json.loads(sys.argv[1])
    print("AP_JSON " + json.dumps(verify(Path(a["bind"]), a["inputs"], a["expected"])))
except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
    print("AP_JSON " + json.dumps({"error": str(exc)}))
"""
    cmd = "python3 -I -c " + shlex.quote(source) + " " + shlex.quote(json.dumps(arg))

    def one(host):
        try:
            proc = run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", host, cmd],
                       capture_output=True, text=True, timeout=90)
            lines = [ln[8:] for ln in proc.stdout.splitlines() if ln.startswith("AP_JSON ")]
            if proc.returncode or len(lines) != 1:
                raise ValueError(f"verification did not finish (rc {proc.returncode})")
            info = json.loads(lines[0])
            if "error" in info:
                raise ValueError(info["error"])
            return info, ""
        except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
            return None, f"{host}: {exc}"

    with ThreadPoolExecutor(max_workers=len(hosts)) as pool:
        results = list(pool.map(one, hosts))
    errors = [why for _, why in results if why]
    if errors:
        raise ValueError("; ".join(errors))
    return dict(results[0][0], sha256=expected, bind=str(bind), hosts=hosts)


def cmd_apply(a, run=subprocess.run, apply_fn=None, commit_fn=None):
    C = Path(a.coord)
    obj = json.loads(Path(a.candidate).read_text())
    obj["optimistic"] = True
    obj["_path"] = a.candidate
    bound_dest, stale_types = "", []
    # POSTBIND-FAILCLOSED 11-23 (COORD FABLE-FLOW-REVIEW item 4): HEAD s2 was applied with post_bind null (script-mode kit_rtl, no bind probe): no strict bind, no LATCHECK.
    # An apply without a post-apply strict bind + LATCHECK is refused (rc 6) unless --allow-no-post-bind names why; a post-bind that cannot start fails the apply AFTER the commit (rc 6, held).
    allow_nopb = getattr(a, "allow_no_post_bind", "") or ""
    reuse_sha = getattr(a, "reuse_post_bind", "") or ""
    if reuse_sha and (getattr(a, "skip_out_check", False) or getattr(a, "skip_bind_check", False) or allow_nopb):
        print("APPLY REFUSED: reusable strict bind evidence cannot be combined with waived checks")
        return 6
    if not allow_nopb and not reuse_sha:
        why_ = postbind_required_problem(obj, getattr(a, "no_post_bind", False))
        if why_:
            print(f"APPLY REFUSED: {why_} (pass --allow-no-post-bind 'reason' to apply without it; the wave is then NOT bind-verified)")
            return 6
    if not getattr(a, "skip_bind_check", False):
        chk = getattr(a, "bind_check_fn", None)

        def check(o):
            r = chk(o, run=run) if chk else bind_check_full(o, run=run)
            return r[0], r[1], (list(r[2]) if len(r) > 2 else [])
        ok, txt, stale_types = check(obj)
        print(f"BIND-CHECK {txt}", flush=True)
        if ok is False and not reuse_sha and not getattr(a, "no_bind_first", False):
            # the candidate names a bind that does not match its plan (publish never carried the new bind): run the strict bind on the PUBLISHED new tree first, switch tree + bind in ONE commit
            dest, btxt, fails = (getattr(a, "bind_first_fn", None) or bind_first)(C, obj, a.lane, a.die if getattr(a, "die", "") else (obj.get("die") or (obj.get("marker") or obj).get("die") or ""), run=run)
            print(f"BIND-FIRST {btxt}", flush=True)
            if not dest:
                print("APPLY REFUSED: the strict bind produced no output for the new tree; the old tree keeps building (types the bind log names: " + (", ".join(fails[:20]) or "none") + ")")
                return 4
            obj = with_bind_out(obj, dest)
            ok2, txt2, stale_types = check(obj)
            print(f"BIND-CHECK (new bind) {txt2}", flush=True)
            bound_dest = dest
            ok = None
        elif ok is False:
            print("APPLY REFUSED: the candidate's bind does not match it (the wave would hold every type BIND-STALE); fix the candidate or pass --skip-bind-check")
            return 4
    def verify_selected_bind(hosts=None):
        if hosts is None:
            ok, lines = (getattr(a, "out_sync_fn", None) or out_sync)(obj, run=run)
        else:
            ok, lines = out_sync(obj, run=run, hosts=hosts)
        for line in lines:
            print(f"OUT-SYNC {line}", flush=True)
        if ok is False:
            raise SelectedBindVerificationError

    die0 = a.die if getattr(a, "die", "") else (obj.get("die") or (obj.get("marker") or obj).get("die") or "")
    live = live_die_cfg(C, die0) if die0 else {}
    prev = prev_event_of(live, die0) if die0 else {}       # ADOPT-CENSUS-1800: read BEFORE the switch
    t0 = time.time()
    reused = None

    def verify_reuse(hosts=None):
        nonlocal reused
        reused = verify_reusable_bind(obj, projected_bind_cfg, reuse_sha, hosts=hosts, run=run)

    def check_reuse_context(projected):
        if publication_receipt_spec(obj, projected)["receipt_inputs"] != expected_inputs:
            raise ValueError("the effective bind configuration changed during publication")

    try:
        kwargs = {}
        if reuse_sha:
            projected_bind_cfg = publication_live_cfg(obj, live)
            expected_inputs = publication_receipt_spec(obj, projected_bind_cfg)["receipt_inputs"]
            verify_reuse()
            marker = obj.get("marker", obj)
            copy = str(Path(reused["bind"]).parent.parent)
            marker.setdefault("config", {})["bind_copy_of_record"] = bind_copy_of_record(live, copy)
            if apply_fn is None:
                kwargs["verify_retained_bind"] = verify_reuse
                kwargs["check_bind_config"] = check_reuse_context
        elif not getattr(a, "skip_out_check", False):
            verify_selected_bind()
            if apply_fn is None:
                kwargs["verify_retained_bind"] = verify_selected_bind
        res = (apply_fn or A.apply_marker)(C, obj, a.expect_source, a.expect_event, pilot_item=a.pilot_item, optimistic=True, **kwargs)
    except ValueError as exc:
        if not reuse_sha:
            raise
        print(f"APPLY REFUSED: cannot reuse the selected strict bind + LATCHECK: {exc}")
        return 6
    except SelectedBindVerificationError:
        print("APPLY REFUSED: the candidate's selected bind output could not be verified across publish hosts; fix the host named above or pass --skip-out-check")
        return 5
    live_new = live_die_cfg(C, res["applied"])
    try:
        env_path = write_published_event_env(C, res, live_new)
        if env_path:
            res["event_env"] = str(env_path)
    except (OSError, EE.EventEnvError) as e:
        res["warnings"] = list(res.get("warnings") or []) + [f"ADVISORY event env: {e}"]
    res["commit"] = (commit_fn or A.commit_apply)(C, res)
    res["plan_probe"] = A.start_plan_probe(res) if commit_fn is None else "skipped: custom commit"      # COORD FABLE-FLOW-0200 C: the new event's plan blocks are cached before the next tick
    res["apply_s"] = round(time.time() - t0, 1)
    if bound_dest:
        res["bind_first"] = bound_dest
        a.no_post_bind = True                       # the bind already ran (before the switch); adopt-bind has nothing left to do
        if stale_types:                             # the bind does not match some types: switched anyway, ONLY those are bind-failed
            r_ = run([sys.executable, "-I", str(HERE / "publish_apply.py"), "bind-fail", "--die", res["applied"], "--lane", a.lane, "--id", "bindfirst-" + time.strftime("%m%d%H%M%S"),
                      "--types", ",".join(stale_types), "--coord", str(C)], capture_output=True, text=True, timeout=600)
            res["bind_failed_types"] = stale_types
    gate = "off"
    if not a.no_gate:
        # the gate's projection must see the candidate as optimistic too (guard/smoke advisory); written next to the receipt
        gc = Path(res["receipt"]).with_suffix(".gate_candidate.json")
        candidate = advisory_gate_candidate(obj, live_new, a.expect_source, res.get("event"))
        gc.write_text(json.dumps(candidate, indent=1))
        unit = "pubgate-%s-%d" % (res["applied"], int(time.time()))
        r = run(["systemd-run", "--user", "--unit", unit, "--collect", "--quiet", "--nice=10", *gate_argv(C, gc, (obj.get("marker") or obj)["tree"], res.get("event"))],
                capture_output=True, text=True, timeout=120)
        gate = unit if r.returncode == 0 else "not started (rc %d: %s)" % (r.returncode, (r.stderr or r.stdout)[-160:])
    res["advisory_gate"] = gate
    pc = "off"
    if not getattr(a, "no_precheck", False):
        pa = precheck_argv(obj, res, a.lane, prev=prev, tools_sha=live_new.get("tools_sha") or "")
        if pa:
            try:
                r = run(pa, capture_output=True, text=True, timeout=120)
                pc = pa[pa.index("--unit") + 1] + "@" + pa[6] if r.returncode == 0 else "not started (rc %d)" % r.returncode
            except Exception as e:  # noqa: BLE001 -- an estimator launch never fails the apply
                pc = "not started (%s)" % type(e).__name__
    res["precheck"] = pc
    pb = "off (--no-post-bind)"
    if reused is not None:
        res["post_bind_reused"] = reused
        pb = f"reused strict bind {reused['types']} types + LATCHECK {reused['lanes']} lanes ({reuse_sha[:12]})"
    elif not getattr(a, "no_post_bind", False):
        unit, pb = (getattr(a, "postbind_fn", None) or start_postbind)(C, obj, a.lane, res["applied"], run=run)
        res["post_bind"] = unit
    w = res.get("warnings") or []
    post(C, a.lane, f"APPLIED-OPTIMISTIC [{a.lane} -> COORD; cc WAVE-FLOW-R2] {res['applied']} event {res.get('event')} tree {res.get('source')}: every type launches on the "
                    f"next wave pass (no pilot); apply {res['apply_s']} s; advisory gate {gate}; precheck {pc}; gen_hosts {','.join(res.get('gen_hosts') or [])}; "
                    f"{len(w)} advisory warning(s){': ' + ' | '.join(w)[:900] if w else ''}. Strict bind + LATCHECK stay blocking: {pb}; on a failure run "
                    f"publish_apply.py bind-fail (holds only the named types).", run=run)
    print(json.dumps(res))
    nopb_ok = bool(getattr(a, "allow_no_post_bind", "")) or bool(bound_dest) or reused is not None
    if not res.get("post_bind") and not nopb_ok:
        post(C, a.lane, f"POSTBIND-MISSING [{a.lane} -> COORD, FLOW-OPS-R3] {res['applied']}: applied but the post-apply strict bind + LATCHECK did NOT start ({pb}); NOT bind-verified. "
                        f"Run publish_apply.py post-bind --candidate {a.candidate} --lane {a.lane}; treat the wave as not ready until POST-APPLY-BIND is GREEN.", run=run)
        print("APPLY RESULT: post_bind missing: wave NOT bind-verified (rc 6)")
        return 6
    return 0


def item_names(d):
    """every item name the die's current plan lists (hold_event_items of its plan sha, else the union of all lists)"""
    hei = d.get("hold_event_items") or {}
    items = hei.get(d.get("plan_sha256")) or [i for v in hei.values() for i in v]
    return sorted(set(items))


def types_from_log(text, items):
    """plan item names that appear as whole words in a bind/LATCHECK failure log, longest first (a__b before a)"""
    found = []
    for it in sorted(items, key=len, reverse=True):
        if re.search(r"(?<![A-Za-z0-9_])" + re.escape(it) + r"(?![A-Za-z0-9_])", text):
            if not any(it in f for f in found):
                found.append(it)
    return sorted(found)


def bind_fail_record(d, types, lane, ident, reason):
    return {"id": f"bindfail-{ident}", "plan_sha": d.get("plan_sha256"), "items": list(types), "owner": lane, "carry": True, "cancel_running": True,
            "reason": f"LATENCY-R optimistic launch: strict bind/LATCHECK failed on these types only ({reason})"[:900],
            "release": [f"result:{lane}:{ident}"]}


def bind_fail_records(cfg, die, types, lane, ident, now=None):
    """one bind_fail record per bind the named types build on now (item kit_rtl over die kit_rtl): {id, bind, items, at, lane}"""
    import kit_wave as KW
    by = {}
    for t in types:
        b = KW.item_bind_out(cfg, die, t)
        if b:
            by.setdefault(b, []).append(t)
    at = time.time() if now is None else now
    return [{"id": f"bindfail-{ident}", "bind": b, "items": sorted(ts), "at": at, "lane": lane} for b, ts in sorted(by.items())]


def owner_lane_of(d, fallback):
    if d.get("die_owner"):
        return str(d["die_owner"])
    m = re.search(r"\(([A-Z][A-Z0-9-]+)\)", str(d.get("owner_lane") or ""))
    return m.group(1) if m else fallback


SSH = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=10"]


def running_rows(state, die, types):
    """the wave rows of DIE whose type is named and whose kit is running (RUNNING / LAUNCHING unit, or an ENQUEUED job that is running / queued)"""
    out = []
    for r in (state.get("items") or {}).values():
        if r.get("die") != die or r.get("item") not in types:
            continue
        if r.get("status") in ("RUNNING", "LAUNCHING") or (r.get("status") == "ENQUEUED" and r.get("q_status") in ("RUNNING", "QUEUED", "STARTING", "WAIT-GEOM")):
            out.append(r)
    return out


def cancel_running_kits(rows, run=subprocess.run):
    """OWNER r705 (1): cancel the running kits of the named types by EXACT unit: the ot-heavy scope(s) of the attempt on its host (resolved with a dry run of ot-heavy-stop
    --match <attempt dir>, then stopped one by one with --unit) and the wave's own hub unit.  -> [(item, where, unit)]"""
    done = []
    for r in rows:
        host, _, kit = str(r.get("kit") or "").partition(":")
        adir = kit.rsplit("/gen/", 1)[0] if kit else ""
        if host and adir:
            q = run([*SSH, host, f"ot-heavy-stop --match {adir} --dry-run 2>&1 | grep -o 'oth-[A-Za-z0-9-]*' | sort -u"], capture_output=True, text=True, timeout=120)
            for u in [x for x in (q.stdout or "").split() if x.startswith("oth-")]:
                run([*SSH, host, f"ot-heavy-stop --unit {u}"], capture_output=True, text=True, timeout=120)
                done.append((r.get("item"), host, u))
        if r.get("unit") and r.get("status") in ("RUNNING", "LAUNCHING"):
            run(["systemctl", "--user", "stop", str(r["unit"])], capture_output=True, text=True, timeout=120)
            done.append((r.get("item"), "hub", str(r["unit"])))
    return done


def cmd_bind_fail(a, run=subprocess.run):
    C = Path(a.coord)
    cfg = json.loads((C / "autopilot/kit_wave.json").read_text())
    d = cfg["dies"][a.die]
    items = item_names(d)
    types = [t for t in (a.types or "").split(",") if t] or types_from_log(Path(a.log).read_text(errors="replace") if a.log else "", items)
    if not types:
        print("BIND-FAIL: no plan type named in the failure; nothing held (hold the die by hand if the failure is die-wide)")
        return 2
    if FG.stops_off_die(cfg, a.die):
        # OWNER r705 (1): under stops_off a bind / LATCHECK failure holds NOTHING: the running kits of the named types are cancelled by exact unit and ONE line names the owner lane
        owner = owner_lane_of(d, a.lane)
        st = {}
        try:
            st = json.loads((C / "autopilot/kit_wave_state.json").read_text())
        except (OSError, ValueError):
            pass
        rows = running_rows(st, a.die, set(types))
        # FABLE-FLOW-1400 (3): the cancelled rows were read as OOM and resubmitted at x1.5 memory on the failed bind (QC cbx_q10).  A bind_fail
        # record (bind id + the bind each type builds on) is written FIRST: the wave books those rows FAIL class BIND-FAIL and launches the
        # types again only when their bind_out changes (kit_wave.bind_fail_active).
        recs = bind_fail_records(cfg, a.die, types, a.lane, a.id)
        if a.dry:
            print(json.dumps({"cancel": [(r.get("item"), r.get("unit"), r.get("kit")) for r in rows], "owner": owner, "bind_fail": recs}, indent=1))
            return 0
        if recs:
            patch = [{"op": "add", "path": f"/dies/{a.die}/bind_fail", "value": list(d.get("bind_fail") or []) + recs}] if not d.get("bind_fail") else \
                [{"op": "add", "path": f"/dies/{a.die}/bind_fail/-", "value": x} for x in recs]
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(patch, f)
            r = run([sys.executable, "-I", str(HERE / "kit_wave_edit.py"), "--coord", str(C), "--message",
                     f"{a.lane}: bind-fail {a.id} ({len(types)} types, class BIND-FAIL)", "--patch-file", f.name], capture_output=True, text=True, timeout=600)
            os.unlink(f.name)
            if r.returncode:
                print("BIND-FAIL: the bind_fail record was not written; nothing cancelled: " + (r.stdout + r.stderr)[-400:])
                return 1
        done = cancel_running_kits(rows, run=run)
        post(C, a.lane, f"BIND-FAIL-CANCEL [{a.lane} -> {owner}] {a.die}: strict bind/LATCHECK failed for {len(types)} type(s): {', '.join(types)[:600]}; cancelled {len(rows)} running "
                        f"kit(s) by exact unit ({len(done)} unit(s)); nothing is held (stops_off), the types relaunch on the next change", run=run)
        print(json.dumps({"cancelled": done, "owner": owner}))
        return 0
    rec = bind_fail_record(d, types, a.lane, a.id, a.reason or (a.log or "explicit types"))
    probe = json.loads(json.dumps(cfg))
    HR.add_record(probe, a.die, dict(rec))          # validation only: unknown item / lane / term -> ValueError, nothing written
    patch = [{"op": "add", "path": f"/dies/{a.die}/hold_records/-" if d.get("hold_records") else f"/dies/{a.die}/hold_records",
              "value": rec if d.get("hold_records") else [rec]}]
    if a.dry:
        print(json.dumps(patch, indent=1))
        return 0
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(patch, f)
    r = run([sys.executable, "-I", str(HERE / "kit_wave_edit.py"), "--message", f"{a.lane}: bind-fail hold {rec['id']} ({len(types)} types)", "--patch-file", f.name],
            capture_output=True, text=True, timeout=600)
    os.unlink(f.name)
    if r.returncode:
        print((r.stdout + r.stderr)[-600:])
        return 1
    post(C, a.lane, f"BIND-FAIL-HOLD [{a.lane} -> COORD; cc WAVE-FLOW-R2] {a.die}: held {len(types)} type(s) named by the strict bind/LATCHECK failure, every other "
                    f"type keeps building: {', '.join(types)[:900]}; release result:{a.lane}:{a.id}", run=run)
    print(json.dumps(rec))
    return 0


def main(argv=None):
    P = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = P.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("apply")
    p.add_argument("--candidate", required=True)
    p.add_argument("--expect-source", required=True)
    p.add_argument("--expect-event", required=True)
    p.add_argument("--lane", required=True)
    p.add_argument("--pilot-item")
    p.add_argument("--coord", default=os.path.expanduser("~/coord"))
    p.add_argument("--no-gate", action="store_true", help="do not start the advisory publish gate")
    p.add_argument("--no-precheck", action="store_true", help="do not start the background PRECHECK-1119 estimator")
    p.add_argument("--skip-bind-check", action="store_true", help="apply although kit_topology.bind_matches says the bind does not match the candidate")
    p.add_argument("--skip-out-check", action="store_true", help="apply without comparing the selected bind output on the publish hosts")
    p.add_argument("--no-bind-first", action="store_true", help="do not run the strict bind before the apply when the candidate bind does not match (refuse instead, as before)")
    p.add_argument("--die", default="", help="die name (default: from the candidate)")
    p.add_argument("--allow-no-post-bind", default="", metavar="REASON", help="apply without a post-apply strict bind + LATCHECK (default: refused, rc 6, POSTBIND-FAILCLOSED 11-23)")
    p.add_argument("--no-post-bind", action="store_true", help="do not start the post-apply strict bind + LATCHECK (hardlink copy of the published tree)")
    p.add_argument("--reuse-post-bind", metavar="SHA256", help="consume the exact sealed strict-bind + LATCHECK producer receipt already enrolled for this candidate")
    pb = sp.add_parser("post-bind", help="post-apply strict bind + LATCHECK in a hardlink copy of the candidate's published tree (apply starts it itself)")
    pb.add_argument("--candidate", required=True)
    pb.add_argument("--lane", required=True)
    pb.add_argument("--die", default="")
    pb.add_argument("--host", default="", help="build host holding the tree (default: the candidate's first gen host)")
    pb.add_argument("--coord", default=os.path.expanduser("~/coord"))
    pb.add_argument("--no-auto-adopt", action="store_true", help="prepare exact bind output for later publication without modifying wave configuration")
    ad = sp.add_parser("adopt-bind", help="after a GREEN post-bind: seal its output, replicate it to the die gen hosts, verify it matches the live plan, switch kit_rtl.bind_out (one CAS commit)")
    ad.add_argument("--die", required=True)
    ad.add_argument("--lane", required=True)
    ad.add_argument("--tree", required=True)
    ad.add_argument("--copy", required=True)
    ad.add_argument("--host", required=True)
    ad.add_argument("--id", default="")
    ad.add_argument("--stamp", default="")
    ad.add_argument("--coord", default=os.path.expanduser("~/coord"))
    dv = sp.add_parser("derive-asbuilt", help="write the kit asbuilt the bind was made with (tables from bind/INPUTS_ISOLATED.json)")
    dv.add_argument("--bind", required=True)
    dv.add_argument("--asbuilt", required=True)
    dv.add_argument("--tree", required=True)
    dv.add_argument("--out", required=True)
    b = sp.add_parser("bind-fail")
    b.add_argument("--die", required=True)
    b.add_argument("--lane", required=True)
    b.add_argument("--id", required=True)
    b.add_argument("--types", default="")
    b.add_argument("--log")
    b.add_argument("--reason", default="")
    b.add_argument("--coord", default=os.path.expanduser("~/coord"))
    b.add_argument("--dry", action="store_true")
    a = P.parse_args(argv)
    if a.cmd == "post-bind":
        return cmd_post_bind(a)
    if a.cmd == "adopt-bind":
        return cmd_adopt_bind(a)
    return cmd_apply(a) if a.cmd == "apply" else cmd_derive(a) if a.cmd == "derive-asbuilt" else cmd_bind_fail(a)


if __name__ == "__main__":
    sys.exit(main())
