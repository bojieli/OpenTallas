#!/usr/bin/env python3
"""ot_event_env: one env file per plan event, read by `ot-run --event-env FILE` (EVENT-ENV-PREFLIGHT 11-24, FABLE FLOW REVIEW #3/#4).

Why: between 02:00 and 04:52 on 11-24, 14 DIED posts were FileNotFoundError at setup, and S81 lk_ES0 lost a 3.3 h gate because its
script set OT_PLAN_GATE_SKIP where the event uses OT_PLAN_GATE_PRE=warn.  The gate env and the rt pin were typed by hand in every lane.
With one file per event (~/coord/events/<event>.env), every unit of the event gets the same env and the same rt pin.  ot-run also checks,
at queue time on the target host, that the event's inputs and rt exist and that the command does not set its own OT_PLAN_GATE_* values.
The alternative is finding out hours later.

File format: one KEY=VALUE per line.  `export ` is optional and `#` starts a comment line.  A value may be wrapped in single or
double quotes, and nothing is expanded (no $VAR, no backticks).  KEY is [A-Z_][A-Z0-9_]*.
  OT_EVENT=<name>                the event name (required)
  OT_EVENT_RT=<sha12 | path>     the rt snapshot every unit pins (exported as OT_TOOLSTALE_RT). A bare sha is resolved under each
                                 host's <scratch>/claude/rt/<sha>
  OT_EVENT_INPUTS=<p1>,<p2>      absolute paths that the units of the event read (bind dir, tree dir).  They must exist on the chosen host
  OT_RUN_PREFLIGHT=fail|warn|off how a preflight finding is handled (default fail: units that name --event-env opt in)
  any other KEY=VALUE            exported into the unit's environment unchanged (OT_PLAN_GATE_PRE, OT_PLAN_GATE_BASELINE, the wave env:
                                 OT_PGCAP, OT_PLACE_MAX_FANOUT, OT_CLAND_STRIP_DENS, OT_IO_HOLD, ...)
Without --event-env, ot-run reports its preflight findings as WARN lines only, which current users see as no change in behaviour.
There is no date-based switch to FAIL (r703).

CLI:  python3 -I ot_event_env.py --check FILE      validates FILE and prints the env it exports.  stdlib only.
"""
import os
import re
import shlex
import sys

KEY_RE = re.compile(r"[A-Z_][A-Z0-9_]*")
SHA_RE = re.compile(r"[0-9a-f]{12}")
RT_ROOTS = tuple(f"/srv/opentallas-scratch{n}/claude/rt" for n in ("2", "", "3"))
MODES = ("fail", "warn", "off")
META = ("OT_EVENT", "OT_EVENT_RT", "OT_EVENT_INPUTS", "OT_RUN_PREFLIGHT")
# keys a unit's command or script must not set to a different value than its event (the lk_ES0 loss: OT_PLAN_GATE_SKIP vs PRE=warn)
GUARDED_RE = re.compile(r"\b(OT_PLAN_GATE_[A-Z_]+|OT_TOOLSTALE_RT)=(\"[^\"]*\"|'[^']*'|[^\s;&|)]*)")


class EventEnvError(ValueError):
    pass


def parse(text, where="event env"):
    """-> dict KEY -> value (insertion order).  Raises EventEnvError on a bad line, a duplicate key or a bad meta value."""
    env = {}
    for n, raw in enumerate(text.splitlines(), 1):
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith("export "):
            ln = ln[len("export "):].lstrip()
        k, eq, v = ln.partition("=")
        k = k.strip()
        if not eq or not KEY_RE.fullmatch(k):
            raise EventEnvError(f"{where}:{n}: not KEY=VALUE: {raw.strip()[:80]!r}")
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        elif v[:1] in "'\"" or v[-1:] in "'\"":
            raise EventEnvError(f"{where}:{n}: unbalanced quote in {k}")
        if "$" in v or "`" in v:
            raise EventEnvError(f"{where}:{n}: {k}: values are literal (no $ or backtick expansion)")
        if k in env:
            raise EventEnvError(f"{where}:{n}: {k} set twice")
        env[k] = v
    if not env.get("OT_EVENT"):
        raise EventEnvError(f"{where}: OT_EVENT=<name> is required")
    mode = env.get("OT_RUN_PREFLIGHT", "fail")
    if mode not in MODES:
        raise EventEnvError(f"{where}: OT_RUN_PREFLIGHT takes {'|'.join(MODES)} (got {mode!r})")
    rt = env.get("OT_EVENT_RT", "")
    if rt and not (SHA_RE.fullmatch(rt) or (rt.startswith("/") and SHA_RE.fullmatch(os.path.basename(rt.rstrip("/"))))):
        raise EventEnvError(f"{where}: OT_EVENT_RT is a 12-hex rt sha or an absolute .../rt/<sha12> path (got {rt!r})")
    if rt and env.get("OT_TOOLSTALE_RT") and os.path.basename(env["OT_TOOLSTALE_RT"].rstrip("/")) != rt_sha(rt):
        raise EventEnvError(f"{where}: OT_TOOLSTALE_RT and OT_EVENT_RT name different rt snapshots")
    for p in inputs({"OT_EVENT_INPUTS": env.get("OT_EVENT_INPUTS", "")}):
        if not p.startswith("/"):
            raise EventEnvError(f"{where}: OT_EVENT_INPUTS takes absolute paths (got {p!r})")
    return env


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return parse(f.read(), where=path)
    except OSError as e:
        raise EventEnvError(f"{path}: {e.strerror or e}")


def rt_sha(rt):
    return os.path.basename(rt.rstrip("/")) if rt else ""


def rt_candidates(rt, roots=RT_ROOTS):
    """the host paths that can hold the event rt (an absolute path: that path first, then the same sha under every scratch root)"""
    if not rt:
        return []
    sha = rt_sha(rt)
    out = [rt.rstrip("/")] if rt.startswith("/") else []
    return out + [f"{r}/{sha}" for r in roots if f"{r}/{sha}" not in out]


def inputs(env):
    return [os.path.normpath(x.strip()) for x in env.get("OT_EVENT_INPUTS", "").split(",") if x.strip()]


def mode(env, override=None):
    """the preflight mode: OT_RUN_PREFLIGHT in the process env wins, then the event file, then fail (event) / warn (no event)"""
    m = override if override is not None else os.environ.get("OT_RUN_PREFLIGHT", "")
    if m in MODES:
        return m
    if env is None:
        return "warn"
    return env.get("OT_RUN_PREFLIGHT", "fail")


def unit_env(env):
    """-> [(KEY, value)] exported into the unit: every non-meta key, plus OT_TOOLSTALE_RT from OT_EVENT_RT (resolved on the host)"""
    return [(k, v) for k, v in env.items() if k not in META and k != "OT_TOOLSTALE_RT"] + [("OT_EVENT", env["OT_EVENT"])]


def env_prefix(env):
    """the 'K=V ' assignments ot-run puts before ot-heavy on the host (shell-quoted)"""
    return "".join(f"{k}={shlex.quote(v)} " for k, v in unit_env(env))


def rt_pin_sh(tag, env, roots=RT_ROOTS):
    """the remote fragment that exports OT_TOOLSTALE_RT = the event rt (first candidate dir with tools/).  None found: an
    OT_RUN_RTPIN_EVENT_MISSING line, and the normal current-rt pin follows (the queue-time preflight refuses that case first)"""
    c = rt_candidates(env.get("OT_EVENT_RT", "") or env.get("OT_TOOLSTALE_RT", ""), roots)
    if not c:
        return None
    return ("unset OT_TOOLSTALE_RT; for _r in " + " ".join(shlex.quote(x) for x in c) + "; do "
            "if [ -d \"$_r/tools\" ]; then export OT_TOOLSTALE_RT=\"$_r\"; break; fi; done; "
            f"if [ -n \"${{OT_TOOLSTALE_RT:-}}\" ]; then echo \"OT_RUN_RTPIN {tag} $OT_TOOLSTALE_RT event\" >&2; "
            f"else echo \"OT_RUN_RTPIN_EVENT_MISSING {tag} {rt_sha(c[0])}\" >&2; fi; ")


def guarded_sets(text):
    """-> [(KEY, value)] OT_PLAN_GATE_* / OT_TOOLSTALE_RT assignments in a command line or script text"""
    out = []
    for m in GUARDED_RE.finditer(text or ""):
        v = m.group(2)
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        out.append((m.group(1), v))
    return out


def gate_conflicts(env, sets, where):
    """the assignments that differ from the event: a key the event sets to another value, or an OT_PLAN_GATE_* key the event
    does not set at all (lk_ES0: OT_PLAN_GATE_SKIP=ANCHORDRY under an event with OT_PLAN_GATE_PRE=warn).  An assignment from
    a variable ($X, ${X:-...}) cannot be judged here and is skipped."""
    out = []
    for k, v in sets:
        if "$" in v:
            continue
        if k == "OT_TOOLSTALE_RT":
            ev = rt_sha(env.get("OT_EVENT_RT", ""))
            if ev and rt_sha(v) != ev:
                out.append(f"{where} sets OT_TOOLSTALE_RT={v} but the event rt is {ev}")
            continue
        if k not in env:
            out.append(f"{where} sets {k}={v}, which event {env['OT_EVENT']} does not set (the event gate env is the whole gate env)")
        elif env[k] != v:
            out.append(f"{where} sets {k}={v} but event {env['OT_EVENT']} has {k}={env[k]}")
    return list(dict.fromkeys(out))


def caller_conflicts(env, environ=None):
    """the caller's own exported OT_PLAN_GATE_* / OT_TOOLSTALE_RT values that the event file replaces"""
    environ = os.environ if environ is None else environ
    sets = [(k, v) for k, v in environ.items() if k.startswith("OT_PLAN_GATE_") or k == "OT_TOOLSTALE_RT"]
    return gate_conflicts(env, sets, "the caller environment")


def host_findings(env, row, scripts=()):
    """row = {path: exists} from one host probe, plus '#grep:<script>' -> text.  -> [finding] for that host"""
    out = []
    for p in inputs(env):
        if not row.get(p):
            out.append(f"event input {p} is missing")
    c = rt_candidates(env.get("OT_EVENT_RT", ""))
    if c and not any(row.get(x + "/tools") for x in c):
        out.append(f"event rt {rt_sha(c[0])} is missing (no {c[0]}/tools)")
    for s in scripts:
        out += gate_conflicts(env, guarded_sets(row.get("#grep:" + s, "")), f"script {s}")
    return out


def probe_paths(env):
    return list(dict.fromkeys(inputs(env) + [x + "/tools" for x in rt_candidates(env.get("OT_EVENT_RT", ""))]))


def probe_sh(paths, scripts=()):
    """one remote shell command: '1 PATH' / '0 PATH' per path, then the guarded assignment lines of each script ('G<TAB>script<TAB>line')"""
    sh = "for p in " + " ".join(shlex.quote(x) for x in paths) + "; do if test -e \"$p\"; then echo \"1 $p\"; else echo \"0 $p\"; fi; done; " if paths else ""
    for s in scripts:
        q = shlex.quote(s)
        sh += f"test -f {q} && grep -hoE 'OT_(PLAN_GATE_[A-Z_]+|TOOLSTALE_RT)=[^[:space:];&|)]*' {q} 2>/dev/null | sed 's|^|G\t'{q}'\t|'; "
    return sh + "true"


def parse_probe(out, paths, scripts=()):
    got, grep = {}, {s: [] for s in scripts}
    for ln in (out or "").splitlines():
        if ln.startswith("G\t"):
            _g, s, rest = (ln.split("\t", 2) + [""])[:3]
            if s in grep:
                grep[s].append(rest)
        elif len(ln) > 2 and ln[1] == " " and ln[0] in "01":
            got[ln[2:]] = ln[0] == "1"
    row = {x: got.get(x, False) for x in paths}
    row.update({"#grep:" + s: "\n".join(v) for s, v in grep.items()})
    row["#answered"] = bool(got) or not paths
    return row


def cmd_scripts(cmd, d=None):
    """the script files a command runs: absolute .sh/.bash/.py tokens, or relative ones resolved against --dir (bash -c strings are scanned too)"""
    out = []
    for t in cmd:
        for w in (safe_split(t) if re.search(r"\s", t) else [t]):
            w = w.strip(";&|()")
            if re.fullmatch(r"[^\s;&|<>()'\"=]+\.(sh|bash|py)", w):
                p = w if w.startswith("/") else (os.path.normpath(os.path.join(d, w)) if d else None)
                if p and p not in out:
                    out.append(p)
    return out


def safe_split(t):
    try:
        return shlex.split(t)
    except ValueError:
        return t.split()


def preflight(env, hosts, cmd, d=None, probe=None, environ=None):
    """-> (kept hosts, {host: [finding]}, [global finding]).  probe(host, paths, scripts) -> row (parse_probe form).
    A host whose probe answered nothing (unreachable) is kept and proves nothing."""
    glob = gate_conflicts(env, guarded_sets(" ".join(cmd)), "the command") + caller_conflicts(env, environ)
    scripts = cmd_scripts(cmd, d)
    paths = probe_paths(env)
    if not hosts or (not paths and not scripts):
        return list(hosts), {}, glob
    probe = probe or ssh_probe
    rows = {h: probe(h, paths, scripts) for h in hosts}
    per = {}
    for h, r in rows.items():
        if not r.get("#answered"):
            continue
        f = host_findings(env, r, scripts)
        if f:
            per[h] = f
    return [h for h in hosts if h not in per], per, glob


def ssh_probe(host, paths, scripts=()):
    import subprocess
    try:
        r = subprocess.run(["ssh", "-o", "ConnectTimeout=20", "-o", "BatchMode=yes", host, probe_sh(paths, scripts)],
                           capture_output=True, text=True, timeout=90)
        if r.returncode:
            return {"#answered": False}
        return parse_probe(r.stdout, paths, scripts)
    except Exception:
        return {"#answered": False}


def main(argv):
    if len(argv) == 2 and argv[0] == "--check":
        try:
            env = load(argv[1])
        except EventEnvError as e:
            print(f"ot_event_env: BAD {e}", file=sys.stderr)
            return 1
        print(f"event {env['OT_EVENT']}  rt {rt_sha(env.get('OT_EVENT_RT', '')) or '(current)'}  preflight {mode(env, '')}")
        for p in inputs(env):
            print(f"  input {p}")
        for k, v in unit_env(env):
            print(f"  {k}={v}")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
