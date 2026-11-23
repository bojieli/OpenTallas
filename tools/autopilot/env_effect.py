#!/usr/bin/env python3
"""LAUNCH-GUARD 11-23 (COORD, class of FAM-S81-MISC kit 1 and the 11-21 private-kit env miss): every OT_* knob a launcher requests in the
gen env must reach the kit's effective config.mk with that value, or the kit builds something other than what was asked.

Scope: a requested key K = v is checked when the CURRENT tools (this tree) write K into a kit config.mk (`export K = ...` in a generator);
OT_GEN_<X> = v is checked as OT_<X> (the gen-time switch of a config knob, e.g. OT_GEN_TAP_GRT_PRE -> OT_TAP_GRT_PRE).  Gen-time-only knobs
(OT_PG_DIE_PHASE, OT_FLOW_TAG, ...) never appear in config.mk and are not checked.  A pinned / older tools tree that ignores a knob the
current tools know is exactly the miss this catches.  Plan fields: PLAN_FIELD_KEYS maps a plan / type field to its config key.

  env_effect.py check --spec SPEC.json --config config.mk       -> mismatches, rc 3 when any
  env_effect.py scan [--json]                                     -> static check of the running wave + private kits (reads kits over ssh)
"""
import argparse, glob, json, os, re, shlex, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORT_RE = re.compile(r"export (OT_[A-Z0-9_]+)\s*[:?]?=")
ASSIGN_RE = re.compile(r"^\s*(?:export\s+)?(OT_[A-Z0-9_]+)\s*([:?+]?=)\s*(.*?)\s*$")
TRUE, FALSE = {"1", "true", "on", "yes"}, {"", "0", "false", "off", "no"}
PLAN_FIELD_KEYS = {"clock.tap_grt_pre": "OT_TAP_GRT_PRE"}
_KNOWN = {}


def known_keys(root=ROOT):
    """-> {OT_key} the generators of `root` write into a kit config.mk"""
    root = str(root)
    if root not in _KNOWN:
        out = set()
        for f in glob.glob(f"{root}/tools/die_plan/*.py") + glob.glob(f"{root}/tools/autopilot/*.py"):
            if os.path.basename(f).startswith("test_"):
                continue
            try:
                out.update(EXPORT_RE.findall(open(f, errors="replace").read()))
            except OSError:
                pass
        _KNOWN[root] = out
    return _KNOWN[root]


def parse_mk(text):
    """-> {OT_key: value} of a config.mk (the last assignment wins; ?= keeps an earlier value; comments skipped)"""
    cfg = {}
    for line in str(text or "").splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = ASSIGN_RE.match(line)
        if not m:
            continue
        k, op, v = m.groups()
        if op == "?=" and k in cfg:
            continue
        cfg[k] = (cfg.get(k, "") + " " + v).strip() if op == "+=" else v
    return cfg


LIST_KEYS = {"OT_KEEP_WIRES", "OT_FSM_NONE_WIRES"}          # the generator merges the env names into its own derived list


def same(want, got, key=""):
    if key in LIST_KEYS:
        return set(str(want).replace(",", " ").split()) <= set(str(got or "").replace(",", " ").split())
    w, g = str(want).strip(), (None if got is None else str(got).strip())
    if w.lower() in FALSE:
        return g is None or g.lower() in FALSE
    if g is None:
        return False
    if w.lower() in TRUE and g.lower() in TRUE:
        return True
    try:
        return float(w) == float(g)
    except ValueError:
        return w == g


def target(key, known):
    """-> the config.mk key a requested env key must set, '' when it is gen-time only"""
    if key.startswith("OT_GEN_"):
        t = "OT_" + key[len("OT_GEN_"):]
        return t if t in known else ""
    return key if key in known else ""


def mismatches(gen_env, cfg_text, known=None, plan_fields=None):
    """-> [(requested key, wanted value, config key, value in config.mk or None)] for every requested knob that did not land"""
    known = known_keys() if known is None else known
    cfg = parse_mk(cfg_text)
    out = []
    for k, v in sorted((gen_env or {}).items()):
        t = target(str(k), known)
        if t and not same(v, cfg.get(t), t):
            out.append((str(k), str(v), t, cfg.get(t)))
    for f, v in sorted((plan_fields or {}).items()):
        t = PLAN_FIELD_KEYS.get(f)
        if t and not same("1" if v is True else "0" if v is False else v, cfg.get(t)):
            out.append((f, str(v), t, cfg.get(t)))
    return out


def describe(mm):
    return "; ".join(f"{k}={v!r} requested but config.mk {t}=" + ("<absent>" if g is None else repr(g)) for k, v, t, g in mm)


def _ssh_cat(host, path, timeout=60):
    try:
        p = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=10", host, f"cat {shlex.quote(path)}"],
                           capture_output=True, text=True, timeout=timeout)
        return p.stdout if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def running_kits(ap_dir, now=None, live_s=6 * 3600):
    """-> [(label, gen_env, host, kit dir)] of the wave attempts in flight and the private specs whose run-item is still live"""
    now = time.time() if now is None else now
    ap = Path(ap_dir)
    out = []
    try:
        st = json.loads((ap / "kit_wave_state.json").read_text())
    except (OSError, ValueError):
        st = {}
    for r in (st.get("items") or {}).values():
        if r.get("status") in ("FAIL", "CANCELLED", "RETRY-INFRA", "PASS", "SIGNED", "DONE") or r.get("q_status") in ("FAIL", "CANCELLED", "PASS", "SIGNED"):
            continue
        kit, d = str(r.get("kit") or ""), r.get("dir")
        if ":" not in kit or not d:
            continue
        try:
            sp = json.loads((Path(d) / "spec.json").read_text())
        except (OSError, ValueError):
            continue
        h, k = kit.split(":", 1)
        out.append((f"wave {r.get('die')}/{r.get('item')}@{r.get('attempt')}", sp.get("gen_env") or {}, h, k))
    for spf in glob.glob(str(ap / "private_specs" / "*" / "*" / "spec.json")):
        d = Path(spf).parent
        log = d / "run_item.log"
        if (d / "result.json").exists() or not log.exists() or now - log.stat().st_mtime > live_s:
            continue
        try:
            sp = json.loads(Path(spf).read_text())
        except (OSError, ValueError):
            continue
        out.append((f"private {d.parent.name}/{d.name}", sp.get("gen_env") or {}, sp.get("gen_host"), f"{sp.get('work')}/gen/{sp.get('item')}"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--spec", required=True)
    c.add_argument("--config", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--ap-dir", default="/srv/opentallas-scratch2/claude/hub-coord/autopilot")
    s.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        mm = mismatches(json.loads(Path(a.spec).read_text()).get("gen_env") or {}, Path(a.config).read_text())
        print(describe(mm) or "ENV-EFFECT OK")
        return 3 if mm else 0
    bad, n, unread = [], 0, []
    for label, env, host, kit in running_kits(a.ap_dir):
        if not any(target(k, known_keys()) for k in env):
            continue
        txt = _ssh_cat(host, f"{kit}/config.mk")
        if txt is None:
            unread.append(label)
            continue
        n += 1
        mm = mismatches(env, txt)
        if mm:
            bad.append({"kit": label, "host": host, "path": kit, "missing": [list(x) for x in mm]})
    if a.json:
        print(json.dumps({"checked": n, "unread": unread, "mismatch": bad}, indent=1))
    else:
        print(f"ENV-EFFECT scan: {n} running kits checked, {len(bad)} mismatch, {len(unread)} unread")
        for b in bad:
            print(f"  MISMATCH {b['kit']} {b['host']}:{b['path']}: " + describe([tuple(x) for x in b["missing"]]))
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
