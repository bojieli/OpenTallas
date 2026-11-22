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
  - AB-CONSUMED-1122 (COORD, OPUS-FIX-QC-COLL-R3 pkit_core3s: --ab OT_TAP_RESET_SPLIT=1 never reached config.mk, so the A/B kit was a
    copy of its control): an A/B key the kit env SETS (non-empty, differing from the wave) that config.mk does not export with that
    value is classified by who reads it in the source tree: a generator (Python under tools/ or physical/ names it as a quoted
    token: OT_GEN_M8_GRANT, OT_IO_HOLD, OT_GRT_CONG_ITERS ...) = consumed at gen; only flow scripts (::env(K) / $(K) in .tcl/.sh/.mk)
    = FAIL "A/B override not consumed" (the flow reads config.mk, not the gen env: the kit is a copy of its control); nobody = WARN
    "read by nothing".  A knob gen_phys TRANSLATES into another config line (gen_phys.ENV_CONFIG_FORMS: OT_GRT_CONG_ITERS ->
    GLOBAL_ROUTE_ARGS ... -congestion_iterations N) is checked in that form first: line present (or a no-op value) = consumed,
    line missing = FAIL.  Keys consumed elsewhere by design are declared in the spec (ab.env_only = [...]); run-item prints the verdict.
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


# GEN-CONSUMED-1122 (OPUS-FIX-S81-COLROM-R6): gen-time knobs gen_phys turns into a non-OT config.mk line instead of an OT_* export.
# key -> regex (with {v} = the kit value) that config.mk must contain; a match counts as consumed.
GEN_CONSUMED = {
    "OT_GRT_CONG_ITERS": r"^\s*export\s+GLOBAL_ROUTE_ARGS\s*=.*-congestion_iterations\s+{v}\b",   # gen_phys _grt_cong_iters
}


def gen_consumed(key, value, config_text):
    """True when gen_phys consumed `key`=`value` into another config.mk line (GEN_CONSUMED)"""
    pat = GEN_CONSUMED.get(key)
    if not pat or config_text is None:
        return False
    if key == "OT_GRT_CONG_ITERS" and str(value).strip() in ("0", "30"):
        return True                                      # OpenROAD default: gen_phys writes no flag by design
    return re.search(pat.format(v=re.escape(str(value).strip())), config_text, re.M) is not None


_READERS = {}


def key_readers(keys, root=None):
    """{key: "gen" | "flow" | ""} -- who reads KEY in the source tree ROOT (default: the repo this file is in): "gen" = a Python file under
    tools/ or physical/ (not the scheduler tools/autopilot, not tests) names it as a quoted token; "flow" = only a .tcl/.sh/.mk reads it
    (::env(K), $(K), ${K}, $K); "" = nobody.  None when the tree cannot be read."""
    root = os.path.abspath(root or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    keys = sorted(set(keys))
    ck = (root, tuple(keys))
    if ck in _READERS:
        return _READERS[ck]
    if not keys or not os.path.isdir(os.path.join(root, "tools")):
        return None
    alt = "|".join(re.escape(k) for k in keys)
    py_re = re.compile(r"[\"'](" + alt + r")[\"']")
    fl_re = re.compile(r"(?:::env\(|\$\(|\$\{|\$)(" + alt + r")\b")
    out = {k: "" for k in keys}
    for top in ("tools", "physical"):
        for dp, dns, fns in os.walk(os.path.join(root, top)):
            dns[:] = [d for d in dns if not d.startswith(".") and d not in ("__pycache__", "results", "logs", "objects", "reports", "run")]
            if os.sep + os.path.join("tools", "autopilot") in dp + os.sep:
                continue
            for fn in fns:
                ext = os.path.splitext(fn)[1]
                if ext not in (".py", ".tcl", ".sh", ".mk") or fn.startswith("test_"):
                    continue
                try:
                    fp = os.path.join(dp, fn)
                    if os.path.getsize(fp) > 8 << 20:
                        continue
                    txt = open(fp, errors="replace").read()
                except OSError:
                    continue
                for m in (py_re if ext == ".py" else fl_re).finditer(txt):
                    k = m.group(1)
                    out[k] = "gen" if ext == ".py" else (out[k] or "flow")
    _READERS[ck] = out
    return out


_FORMS = {}


def config_forms(root=None):
    """gen_phys.ENV_CONFIG_FORMS of the source tree ROOT, read as a literal (no import) -> {} when absent / unreadable"""
    import ast
    root = os.path.abspath(root or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    if root not in _FORMS:
        out = {}
        try:
            src = open(os.path.join(root, "tools", "die_plan", "gen_phys.py"), errors="replace").read()
            i = src.find("\nENV_CONFIG_FORMS = {")
            if i >= 0:
                j = src.find("\n}\n", i)
                out = ast.literal_eval(src[i:j + 2].split("=", 1)[1].strip())
        except (OSError, ValueError, SyntaxError):
            out = {}
        _FORMS[root] = out if isinstance(out, dict) else {}
    return _FORMS[root]


def translated(key, value, config_text, forms):
    """True / False when KEY has a translated config form (present / missing), None when it has none"""
    f = (forms or {}).get(key)
    if not isinstance(f, dict) or not f.get("re"):
        return None
    if str(value) in [str(x) for x in f.get("noop") or []]:
        return True
    rx = re.compile(f["re"].replace("{v}", re.escape(str(value))), re.M)
    return bool(rx.search(config_text or ""))


def ab_classify(rec, cfg, root=None, config_text=None):
    """-> (dropped, unread): A/B keys not exported by config.mk that only flow scripts read, or whose translated config line
    (gen_phys.ENV_CONFIG_FORMS) is missing (dropped: the override never reached the flow), and that nobody reads (unread).  Keys a
    generator reads are consumed at gen.  Unknown source tree: every candidate is 'unread' (warn)."""
    cand = ab_not_consumed(rec, cfg, config_text)
    if not cand:
        return [], []
    if config_text is None:
        config_text = "\n".join(f"export {k} = {v}" for k, v in (cfg or {}).items())
    forms = config_forms(root)
    tr = {k: translated(k, v, config_text, forms) for k, v, _ in cand}
    gone = [c for c in cand if tr[c[0]] is False]
    cand = [c for c in cand if tr[c[0]] is None]
    if not cand:
        return gone, []
    rd = key_readers([k for k, _, _ in cand], root)
    if rd is None:
        return gone, cand
    return gone + [c for c in cand if rd.get(c[0]) == "flow"], [c for c in cand if not rd.get(c[0])]


def ab_not_consumed(rec, cfg, config_text=None):
    """[(key, kit value, config.mk value or None)] for A/B keys the kit env sets that config.mk does not export with that value"""
    ab = rec.get("ab") or {}
    keys = set(ab.get("keys") or []) - set(ab.get("env_only") or [])
    w, e = rec.get("wave_env") or {}, rec.get("env") or {}
    out = []
    for k in sorted(keys):
        v = e.get(k)
        if v is None or str(v) == "" or (k in w and str(w.get(k)) == str(v)):
            continue                                     # unset / emptied / same as wave: nothing to consume
        c = cfg.get(k)
        if c is not None and (str(c) == str(v) or (len(str(v).split()) > 1 and set(str(v).split()) <= set(str(c).split()))):
            continue                                     # exported as given, or a list the generator extended (every given item kept)
        if c is None and gen_consumed(k, v, config_text):
            continue                                     # GEN-CONSUMED-1122: written as another config.mk line
        out.append((k, str(v), c))
    return out


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
    if config_text is not None and ab_keys:             # AB-CONSUMED-1122
        nc, unread = ab_classify(rec, config_ot(config_text), config_text=config_text)
        if nc:
            lines.append("ENV-PROVENANCE FAIL: A/B override not consumed: config.mk does not export "
                         + "; ".join(f"{k}={v!s:.40} (config.mk {'<unset>' if c is None else c})" for k, v, c in nc[:12])
                         + " -- only flow scripts read it and the flow reads config.mk, so this kit is a copy of its control; set the knob "
                           "in the plan (gen_phys writes it), or declare ab.env_only for a key consumed outside config.mk")
        if unread:
            lines.append("ENV-PROVENANCE WARN: A/B key(s) read by nothing in the source tree and not in config.mk (no effect?): "
                         + ", ".join(k for k, _, _ in unread[:12]))
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
    try:
        nc = ab_classify(rec, rec.get("config_ot") or {}, config_text=txt)[0] if txt is not None else []
    except Exception:                                    # never fail run-item on this report
        nc = []
    if nc:                                               # AB-CONSUMED-1122: loud at run-item; run_kit.sh's check refuses place
        print("ENV-PROVENANCE AB-NOT-CONSUMED " + " ".join(f"{k}={v} (config.mk {c if c is not None else '<unset>'})" for k, v, c in nc)
              + ": these A/B overrides do not reach the flow (config.mk); place will be refused", flush=True)
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
