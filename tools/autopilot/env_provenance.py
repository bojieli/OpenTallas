#!/usr/bin/env python3
"""env_provenance.py -- ENV-PROVENANCE (FLOW-PROC-A 11-21, FABLE-FLOW-0800 class a): a kit states where its gen environment came from,
and run_kit.sh refuses to start place on a kit whose environment is not its wave source.

Why: 5 lanes built at least 7 private kits on hand-written env subsets (missing OT_PGCAP, OT_PLACE_MAX_FANOUT, OT_CBC_REACH_UM, flow_tag ...)
and compared them with wave kits: every conclusion drawn from them had to be re-measured.  A private kit is now made by
`kit_wave.py private-spec DIE ITEM [--plan P] [--tree T] [--overlay O]`, which computes the item's wave spec fresh from the die config;
only plan, tree and overlay differ.  `kit_wave.py run-item SPEC` (wave and private alike) writes K/kit_env_provenance.json right before
place:

  {"schema": "opentallas.env_provenance/1", "source": "wave" | "private-spec" | "unregistered", "die", "item", "event", "spec_sha256",
   "env": {the OT_* gen env the kit was generated with}, "wave_env": {the wave env of that item}, "plan_derived": [keys allowed to differ:
   values rewritten to the private tree], "ab": {"keys": [...], "why": "..."} | null, "flow_tag", "gen_args", "wave_gen_args",
   "config_ot": {OT_* exports of config.mk at that moment}, "written": "..."}

  env_provenance.py check KIT      (run_kit.sh, before place; exit 0 pass, 14 refuse)
  env_provenance.py write KIT --b64 B64JSON   (run-item; adds config_ot + written)

Refusals (only while the kit has no 3_place.odb: a kit already past place gets a WARN line and runs on -- never a stop of live work):
  - no record, and the kit is not under a kit-wave work root (a hand-built kit) -- a legacy wave kit without a record passes with a note
  - source "unregistered" (run-item on a copied spec.json that is neither a wave attempt nor a private-spec output)
  - env differs from wave_env on a key that is not plan-derived and not named by the spec's A/B opt-out (ab.keys, with a reason)
  - a private-spec kit whose config.mk OT_* exports differ from the ones recorded at run-item (config.mk edited by hand after generation;
    on a wave kit this is a NOTE: wave kits are right by construction)
  - FLOW-OPS-0900 (FABLE-FLOW-0745 g, FAM-S81-LEPE-3 proof9 = wave kit copy + config.mk diff): a wave record found in a kit dir other than
    the one run-item wrote it in (the record's "kit") is a COPIED wave kit; a config.mk change there is a FAIL, not a NOTE (a copy + edit
    is a hand-built kit).  A plain copy with an unchanged config.mk passes with a NOTE.
Only exit 14 refuses; a crash of this checker (any other rc) never stops the kit.
"""
import base64
import json
import os
import re
import sys
import time

SCHEMA = "opentallas.env_provenance/1"
RECORD = "kit_env_provenance.json"
REFUSE_RC = 14
# keys whose value legitimately follows the plan / tree of a private kit (paths into the source tree are added per spec)
PLAN_DERIVED_KEYS = ("OT_SIGNED_VIEW_SHA", "OT_NATIVE_PRODUCER_CONTEXT")
EXPORT_RE = re.compile(r"^\s*(?:override\s+)?export\s+(OT_[A-Z0-9_]+)\s*(?:\?=|:=|\+=|=)\s*(.*?)\s*$")


def config_ot(text):
    """the OT_* exports of a config.mk text -> {KEY: value} (the last assignment wins, as in make)"""
    out = {}
    for ln in (text or "").splitlines():
        m = EXPORT_RE.match(ln)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def env_diff(wave, env):
    """keys added, removed or changed between the wave env and the kit env"""
    wave, env = dict(wave or {}), dict(env or {})
    return sorted(k for k in set(wave) | set(env) if str(wave.get(k)) != str(env.get(k)) or (k in wave) != (k in env))


def judge(rec, config_text, placed=False, kit_path=""):
    """-> (ok, [lines]).  ok False = refuse place.  Pure function (tests)."""
    lines = []
    if not rec:
        if "/kit-wave/" in kit_path + "/":
            return True, ["ENV-PROVENANCE NOTE: legacy wave kit with no kit_env_provenance.json (generated before ENV-PROVENANCE)"]
        if "/flow-canary/runs/" in kit_path + "/":     # FLOW-CANARY-1121: a flow canary regenerates a reference kit with main's generator to test the flow itself, never a design proof
            return True, ["ENV-PROVENANCE NOTE: flow canary reference kit (tools/flow_canary), not a design proof"]
        why = ("ENV-PROVENANCE FAIL: no kit_env_provenance.json and the kit is not a kit-wave attempt (hand-built kit?): build private kits with "
               "`kit_wave.py private-spec DIE ITEM [--plan P] [--tree T] [--overlay O]` + `kit_wave.py run-item SPEC`")
        return _soft(placed, [why])
    src = rec.get("source")
    if src not in ("wave", "private-spec"):
        return _soft(placed, [f"ENV-PROVENANCE FAIL: source {src!r}: run-item on a spec that is neither a wave attempt nor a private-spec output "
                              f"(a copied spec.json carries an old env); make one with `kit_wave.py private-spec`"])
    allowed = set(PLAN_DERIVED_KEYS) | set(rec.get("plan_derived") or [])
    ab = rec.get("ab") or {}
    ab_keys = set(ab.get("keys") or [])
    if ab_keys and not str(ab.get("why") or "").strip():
        return _soft(placed, ["ENV-PROVENANCE FAIL: A/B opt-out without a reason (spec env_ab.why)"])
    diff = env_diff(rec.get("wave_env"), rec.get("env"))
    bad = [k for k in diff if k not in allowed and k not in ab_keys]
    if bad:
        w, e = rec.get("wave_env") or {}, rec.get("env") or {}
        lines.append("ENV-PROVENANCE FAIL: kit env differs from the wave env of %s/%s on %d key(s) that are neither plan-derived nor declared A/B: %s"
                     % (rec.get("die"), rec.get("item"), len(bad), "; ".join(f"{k} wave={w.get(k, '<unset>')!s:.60} kit={e.get(k, '<unset>')!s:.60}" for k in bad[:12])))
    unused = sorted(ab_keys - set(diff))
    if unused:
        lines.append(f"ENV-PROVENANCE NOTE: A/B keys {','.join(unused)} equal the wave env")
    rec_cfg = rec.get("config_ot")
    if isinstance(rec_cfg, dict) and config_text is not None:
        now = config_ot(config_text)
        cd = env_diff(rec_cfg, now)
        copied = copied_from(rec, kit_path)
        if cd:                                           # a wave kit is right by construction: a later config.mk edit there is only reported
            if src == "wave" and copied:
                lines.append(f"ENV-PROVENANCE FAIL: copied wave kit (record written in {copied}) with config.mk OT_* exports edited after run-item "
                             f"(a hand-built kit): {', '.join(cd[:12])}; build private kits with `kit_wave.py private-spec` + `run-item`")
            else:
                lines.append(("ENV-PROVENANCE FAIL" if src == "private-spec" else "ENV-PROVENANCE NOTE")
                             + ": config.mk OT_* exports changed after run-item recorded them (hand edit?): " + ", ".join(cd[:12]))
        elif copied:
            lines.append(f"ENV-PROVENANCE NOTE: kit copied from {copied} (config.mk unchanged)")
    if any(ln.startswith("ENV-PROVENANCE FAIL") for ln in lines):
        return _soft(placed, lines)
    n = len([k for k in diff if k in ab_keys])
    lines.insert(0, f"ENV-PROVENANCE PASS: source {src} {rec.get('die')}/{rec.get('item')} env=wave"
                 + (f"+{len(diff)}({','.join(diff[:8])})" if diff else "") + (f" A/B {n} key(s): {ab.get('why')}" if n else ""))
    return True, lines


def copied_from(rec, kit_path):
    """the kit dir the record was written in when that is not KIT (a copied kit), else ''.  Records older than FLOW-OPS-0900 carry no kit."""
    k = str((rec or {}).get("kit") or "")
    if not k or not kit_path:
        return ""
    try:
        same = os.path.realpath(k) == os.path.realpath(kit_path)
    except (OSError, ValueError):
        same = k.rstrip("/") == str(kit_path).rstrip("/")
    return "" if same else k


def wave_delta(kit):
    """number of non-plan env keys that differ from the wave env (A/B keys included) -> int; None when KIT has no readable record"""
    try:
        rec = json.loads(_read(os.path.join(kit, RECORD)) or "null")
    except ValueError:
        return None
    if not isinstance(rec, dict) or not isinstance(rec.get("env"), dict):
        return None
    allowed = set(PLAN_DERIVED_KEYS) | set(rec.get("plan_derived") or [])
    return len([k for k in env_diff(rec.get("wave_env"), rec.get("env")) if k not in allowed])


def _soft(placed, lines):
    if placed:
        return True, [ln.replace("ENV-PROVENANCE FAIL", "ENV-PROVENANCE WARN (kit already placed, runs on)") for ln in lines]
    return False, lines


def _read(p):
    try:
        with open(p, errors="replace") as f:
            return f.read()
    except OSError:
        return None


def check(kit):
    kit = os.path.abspath(kit)
    try:
        rec = json.loads(_read(os.path.join(kit, RECORD)) or "null")
    except ValueError as e:
        rec = {"source": f"unreadable record ({e})"}
    import glob
    placed = bool(glob.glob(os.path.join(kit, "run/results/asap7/*/base/3_place.odb")))
    ok, lines = judge(rec, _read(os.path.join(kit, "config.mk")), placed=placed, kit_path=kit)
    for ln in lines:
        print(ln, flush=True)
    try:
        with open(os.path.join(kit, "env_provenance_check.log"), "a") as f:
            f.write(time.strftime("%F %T %Z ") + " | ".join(lines) + "\n")
    except OSError:
        pass
    return 0 if ok else REFUSE_RC


def write(kit, decl):
    kit = os.path.abspath(kit)
    rec = dict(decl, schema=SCHEMA, written=time.strftime("%F %T %Z"), kit=kit)
    txt = _read(os.path.join(kit, "config.mk"))
    if txt is not None:
        rec["config_ot"] = config_ot(txt)
    tmp = os.path.join(kit, f".{RECORD}.{os.getpid()}")
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, os.path.join(kit, RECORD))
    print(f"ENV-PROVENANCE RECORD {rec.get('source')} {rec.get('die')}/{rec.get('item')}: env {len(rec.get('env') or {})} keys, "
          f"differs from wave on {','.join(env_diff(rec.get('wave_env'), rec.get('env'))) or 'nothing'}", flush=True)
    return 0


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) >= 2 and a[0] == "check":
        return check(a[1])
    if len(a) >= 4 and a[0] == "write" and a[2] == "--b64":
        return write(a[1], json.loads(base64.b64decode(a[3])))
    print(__doc__.split("\n\n")[0])
    print("usage: env_provenance.py check KIT | write KIT --b64 B64JSON")
    return 2


if __name__ == "__main__":
    sys.exit(main())
