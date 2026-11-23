#!/usr/bin/env python3
"""ot-build DIE TYPE: the hub side (see ot_build.py for the command and its exit codes).

  1 resolve   the die's tree / plan / as-built manifest / bind env from the wave config (AP_DIR/kit_wave.json); --tree / --plan replace
              them (a lane fork made by ot-tree-fork, a plan overlay made by `ot-build plan-overlay`)
  2 host      the least loaded gen host that HOLDS the tree and the plan (never a pinned loaded host; --host overrides)
  3 bind      `ot_build.py bind --status` there over ssh (hashes only, seconds); only when a node is stale the bind stage runs through
              ot-run --priority plan --plan-job bind on that host
  4 kit       stamped on (the type's plan block, its bound RTL, the as-built manifest, runtime pin, bind env): an unrelated row change
              re-binds the die but does NOT rebuild this type.  Stale -> kit_wave.py private-spec --tree --plan --bind-out (the tree's
              own bind, wave env) + run-item --goal finish: place .. route, sign-off, routed LEC.  SIGNED is the only pass.
  5 export    auto_export.py enqueue of the signed-off kit.
Every refusal names the inconsistent input and happens before the first multi-hour stage."""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_graph as G  # noqa: E402

AP_DIR = Path(os.environ.get("AP_DIR") or (Path.home() / "coord" / "autopilot"))
RT_ROOT = Path(os.environ.get("OT_RT_ROOT") or "/srv/opentallas-scratch2/claude/rt")
SCRATCH = os.environ.get("OT_BUILD_SCRATCH") or "/srv/opentallas-scratch2/claude"
SSH = ["ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
GOALS = ("bind", "kit", "finish", "export")
MIN_DISK_GB = int(os.environ.get("OT_BUILD_MIN_DISK_GB", "250"))
PROBE = r'''
t=$1; shift
echo L $(cut -d' ' -f1,2 /proc/loadavg); echo N $(nproc); echo M $(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
[ -d "$t" ] && echo T 1 || echo T 0
echo D $(df -BG --output=avail "$(dirname "$t")" 2>/dev/null | tail -1 | tr -dc 0-9)
ok=1; for f in "$@"; do [ -e "$f" ] || { ok=0; echo MISS "$f"; }; done; echo F $ok
'''


def log(msg):
    print(msg, flush=True)


def sh(cmd, timeout=None, stdin=None):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=stdin)
    return r.returncode, r.stdout, r.stderr


def local_host():
    return os.uname().nodename.split(".")[0]


def remote(host, command, timeout=600, run=sh):
    """run a shell command on `host` (locally when it is this host) -> (rc, stdout, stderr)"""
    if host in ("localhost", local_host(), os.environ.get("OT_BUILD_SELF", "intel2")) and os.environ.get("OT_BUILD_FORCE_SSH") != "1":
        return run(["bash", "-c", "cd / && " + command], timeout=timeout)
    return run(["timeout", str(timeout)] + SSH + [host, "cd / && " + command], timeout=timeout + 30)


def swap_prefix(p, old, new):
    p, old, new = str(p), str(old).rstrip("/"), str(new).rstrip("/")
    return new + p[len(old):] if p == old or p.startswith(old + "/") else p


def bind_env_of(d):
    """the env the die's strict bind runs with = every OT_* of the die config's die_gen_env and bind_env (publish_apply.bind_env_of:
    the binder reads e.g. OT_KV_HEAD_KST, OT_HCPARAM_ALL, OT_NATIVE_RESET_SCOPE from the environment)"""
    env = {}
    for blk in ("die_gen_env", "bind_env"):
        for k, v in (d.get(blk) or {}).items():
            if str(k).startswith("OT_") and isinstance(v, (str, int, float)) and not isinstance(v, bool):
                env[str(k)] = str(v)
    return env


def resolve(cfg, die, tree=None, plan=None, asbuilt=None):
    dies = cfg.get("dies") or {}
    if die not in dies:
        raise G.BuildError(f"die {die!r} is not in the wave config ({', '.join(sorted(dies))})")
    d = dies[die]
    kr = d.get("kit_rtl") or {}
    if kr.get("mode") != "bind":
        raise G.BuildError(f"die {die}: kit_rtl.mode is {kr.get('mode')!r}; ot-build drives dies whose kit RTL comes from a die bind "
                           "(mode bind).  Use kit_wave.py private-spec / run-item for this die.")
    src = d.get("src")
    if not src or not d.get("plan"):
        raise G.BuildError(f"die {die}: the wave config has no src / plan")
    t = os.path.abspath(tree) if tree else src
    res = dict(die=die, wave_src=src, tree=t, plan=os.path.abspath(plan) if plan else swap_prefix(d["plan"], src, t),
               asbuilt=os.path.abspath(asbuilt) if asbuilt else (swap_prefix(kr["asbuilt"], src, t) if kr.get("asbuilt") else None),
               env={k: swap_prefix(v, src, t) for k, v in bind_env_of(d).items()}, wave_bind_out=kr.get("bind_out"), event=d.get("event"),
               hosts=list(dict.fromkeys((d.get("gen_hosts") or []) + ([d["gen_host"]] if d.get("gen_host") else []))))
    if res["asbuilt"] and not str(res["asbuilt"]).startswith(str(t).rstrip("/") + "/") and not asbuilt:
        raise G.BuildError(f"die {die}: the wave as-built manifest {kr.get('asbuilt')} is outside the die tree {src}; give --asbuilt")
    return res


def probe(host, tree, files, run=sh):
    rc, out, err = run(["timeout", "30"] + [x for x in SSH if x != "-n"] + [host, "bash -s -- " + " ".join(shlex.quote(str(x)) for x in [tree] + files)],
                       timeout=45, stdin=PROBE)
    d = dict(host=host, miss=[])
    for ln in out.splitlines():
        k, _, v = ln.partition(" ")
        if k == "L":
            d["l1"], d["l5"] = (float(x) for x in v.split())
        elif k == "N":
            d["ncpu"] = int(v)
        elif k == "M":
            d["mem_gb"] = int(v)
        elif k == "T":
            d["has_tree"] = v == "1"
        elif k == "D" and v.strip().isdigit():
            d["disk_gb"] = int(v)
        elif k == "F":
            d["has_files"] = v == "1"
        elif k == "MISS":
            d["miss"].append(v)
    if "ncpu" not in d:
        d["error"] = (err or "no answer").strip()[-120:]
    return d


def pick_host(hosts, tree, files, min_mem_gb=64, run=sh, pin=None):
    """-> (host, table lines).  The least loaded host (max(load1, load5) / cpus) that has the tree, the plan-side files and the memory."""
    import concurrent.futures as cf
    hosts = [pin] if pin else hosts
    if not hosts:
        raise G.BuildError("no candidate hosts (the die has no gen_hosts; give --host)")
    with cf.ThreadPoolExecutor(len(hosts)) as ex:
        rows = list(ex.map(lambda h: probe(h, tree, files, run), hosts))
    ok, lines = [], []
    for d in rows:
        if "error" in d:
            lines.append(f"  {d['host']:8s} unreachable ({d['error']})")
            continue
        d["lpc"] = round(max(d["l1"], d["l5"]) / d["ncpu"], 2)
        why = []
        if not d.get("has_tree"):
            why.append("no tree")
        elif not d.get("has_files"):
            why.append("missing " + ", ".join(d["miss"][:2]))
        if d.get("mem_gb", 0) < min_mem_gb:
            why.append(f"{d.get('mem_gb')} GB free < {min_mem_gb}")
        if d.get("disk_gb", MIN_DISK_GB) < MIN_DISK_GB and not pin:      # a draining host takes no new job (its admit cap), even a small one
            why.append(f"disk {d['disk_gb']} GB < {MIN_DISK_GB} (draining)")
        lines.append(f"  {d['host']:8s} load/cpu {d['lpc']:5.2f}  mem {d.get('mem_gb')} GB  disk {d.get('disk_gb', '?')} GB  "
                     f"tree {'yes' if d.get('has_tree') else 'no'}"
                     + ("   skip: " + "; ".join(why) if why else ""))
        if not why:
            ok.append(d)
    if not ok:
        raise G.BuildError(f"no host holds the tree {tree} with its plan files and {min_mem_gb} GB free:\n" + "\n".join(lines)
                           + "\n  replicate the tree (src_manifest.py replicate / ot-tree-fork --host) or give --host")
    best = min(ok, key=lambda d: (d["lpc"], -d.get("mem_gb", 0)))
    return best["host"], lines


def bind_argv(r, rt_dir, out_root, emit_j, types):
    argv = ["python3", "-I", f"{rt_dir}/tools/autopilot/ot_build.py", "bind", "--tree", r["tree"], "--plan", r["plan"],
            "--out-root", out_root, "--rt", str(rt_dir), "--emit-j", str(emit_j)]
    if r["asbuilt"]:
        argv += ["--asbuilt", r["asbuilt"]]
    if r.get("remap_base"):
        argv += ["--remap-base", r["remap_base"]]
    for k, v in sorted(r["env"].items()):
        argv += ["--env", f"{k}={v}"]
    for t in types:
        argv += ["--type", t]
    return argv


def parse_bind(out):
    eff = None
    for ln in out.splitlines():
        if ln.startswith("OT-BUILD EFFECTIVE "):
            try:
                eff = json.loads(ln[len("OT-BUILD EFFECTIVE "):])
            except ValueError:
                pass
    return eff


def _bind_env(lane, out_root):
    return f"OT_LANE={shlex.quote(lane)} OT_BUILD_HASH_CACHE={shlex.quote(out_root)}/hash_cache.json"


def bind_status(r, host, rt_dir, out_root, lane, emit_j, types, run=sh):
    """hashes only, over ssh (seconds) -> (rc, effective record | None, output): rc 0 every node fresh, 3 stale, 1 refused"""
    q = " ".join(shlex.quote(x) for x in bind_argv(r, rt_dir, out_root, emit_j, types))
    rc, out, err = remote(host, f"mkdir -p {shlex.quote(out_root)} && {_bind_env(lane, out_root)} {q} --status", timeout=1800, run=run)
    return rc, parse_bind(out), out + err


def bind_job(r, host, rt_dir, out_root, lane, emit_j, mem, types, run=sh):
    """write the stage script into out_root on the host (ot-run admits a lane job whose inputs are under its --dir) -> ot-run argv"""
    q = " ".join(shlex.quote(x) for x in bind_argv(r, rt_dir, out_root, emit_j, types))
    script = f"{out_root}/ot_build_bind.sh"
    body = f"#!/bin/bash\n# ot-build bind stage ({lane}); written by ot_build_hub.py\ncd /\nexport {_bind_env(lane, out_root)}\nexec {q}\n"
    rc, _, err = remote(host, f"cat > {shlex.quote(script)}.tmp <<'OTB_EOF'\n{body}OTB_EOF\nmv {shlex.quote(script)}.tmp {shlex.quote(script)}",
                        timeout=60, run=run)
    if rc != 0:
        raise G.BuildError(f"cannot write {script} on {host}: {err.strip()[-200:]}")
    j = 8 if str(emit_j) == "auto" else int(emit_j)
    return ["python3", "-I", f"{rt_dir}/tools/fleet/ot-run", "--hosts", host, "--mem", str(mem), "--threads", str(j + 2),
            "--priority", "plan", "--plan-job", "bind", "--dir", out_root, "--", "bash", script]


def run_bind_stage(r, host, rt_dir, out_root, a, types, run=sh, stream=None):
    """status over ssh; when stale, the stage through ot-run on the host.  -> effective record (raises BuildError)"""
    rc, eff, out = bind_status(r, host, rt_dir, out_root, a.lane, a.emit_j, types, run=run)
    for ln in out.splitlines():
        if ln.startswith("ot-build:"):
            log("  " + ln)
    if rc == 0 and eff:
        log(f"ot-build: bind stage FRESH on {host}: {eff['out']}")
        return eff
    if rc not in (0, 3) or eff is None:
        raise G.BuildError(f"bind stage status on {host} failed (rc {rc}): {out.strip()[-800:]}")
    if a.dry:
        raise Dry("the bind stage has stale nodes (above)")
    cmd = bind_job(r, host, rt_dir, out_root, a.lane, a.emit_j, a.bind_mem, types, run=run)
    log("ot-build: bind stage through ot-run: " + " ".join(shlex.quote(c) for c in cmd))
    rc, out = (stream or stream_cmd)(cmd, dict(os.environ, OT_LANE=a.lane))
    eff = parse_bind(out)
    if rc != 0 or not eff or eff.get("rc") != 0:
        tail = [ln for ln in out.splitlines() if ln.startswith(("ot-build:", "    ", "ot-run:"))][-30:]
        raise G.BuildError(f"bind stage FAILED on {host} (ot-run rc {rc}):\n" + "\n".join(tail))
    return eff


# ---- wave rows (kit_wave.py) --------------------------------------------------------------------------------------------------------
WAVE_STATUS_TTL_S = 600
WAVE_FAIL_RETRY_S = 7200
# S81 J7 11-22 (OPUS-PIPELINE-R2): the first auto rebind started 07:56 on a tree whose plan lane had adopted its own bind at 07:17,
# on rt/current instead of the die's tools pin.  A die's rows must stay BIND-STALE this long before an auto rebind starts (the plan
# lane's own post-apply bind wins), and the rebind runs on the die's tools_sha rt when that snapshot exists.
AUTO_BIND_GRACE_S = int(os.environ.get("OT_AUTO_BIND_GRACE_S", "3600"))


def die_rt(cfg, die):
    """-> the rt snapshot name of the die's tools pin (dies.<die>.tools_sha) when it is on this host, else None (rt/current)"""
    sha = str((cfg.get("dies", {}).get(die) or {}).get("tools_sha") or "")[:12]
    return sha if sha and (RT_ROOT / sha / "tools" / "die_plan" / "bind.py").is_file() else None


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _home(p, eff, tree):
    """a path the bind host names inside ITS real path of the tree (epyc2: scratch2 -> scratch3) -> the same path under `tree`"""
    return swap_prefix(p, eff["tree"], tree) if p and eff and eff.get("tree") else p


def wave_rebind(cfg, die, st, lane="KIT-WAVE", now=None, run=sh, popen=None, alive=_alive, rt=None, emit_j="auto", mem="96"):
    """kit_wave tick, die option auto_bind: the wave rows of `die` are BIND-STALE (KIT_TOPOLOGY_BIND_STALE preflight / stage, R8_STALE)
    on the die's own tree and plan.  Instead of waiting for a hand-run bind: make the die's bind fresh with the ot-build bind stage
    and hand its OUT back.  One call per tick, never blocks on the bind:

        FRESH    {out, asbuilt, host}: every node's stamp equals the tree + plan now -> the caller points the stale rows' kit_rtl at it
        STARTED / RUNNING            : the stage runs through ot-run --priority plan on the least loaded holder of the tree
        FAILED   {why}               : the stage refused or failed (the message names the input); retried after WAVE_FAIL_RETRY_S or
                                       as soon as the die's src / plan / as-built change
    State is kept in st["auto_bind"][die] (the wave state file)."""
    now = time.time() if now is None else float(now)
    rec = st.setdefault("auto_bind", {}).get(die) or {}
    try:
        r = resolve(cfg, die)
        key = "|".join([r["tree"], r["plan"], str(r["asbuilt"]), json.dumps(r["env"], sort_keys=True)])
        if rec.get("key") != key:
            if rec.get("state") in ("STARTED", "RUNNING") and alive(rec.get("pid")):
                # COORD 11-22: at most ONE auto rebind per die at a time.  The inputs moved while a bind runs: let it end (its
                # verdict is for the old inputs and is dropped), then the next tick starts the bind of the new inputs
                rec.update(state="RUNNING", superseded=True)
                st["auto_bind"][die] = rec
                return dict(rec, why="inputs changed while a rebind runs; the next rebind starts when it ends (cap 1 per die)")
            rec = {"key": key}
        if rec.get("state") in ("STARTED", "RUNNING"):
            if alive(rec.get("pid")):
                rec["state"] = "RUNNING"
                st["auto_bind"][die] = rec
                return dict(rec)
            try:
                eff = parse_bind(Path(rec["log"]).read_text(errors="replace"))
            except OSError:
                eff = None
            if eff and eff.get("rc") == 0:
                rec.update(state="FRESH", out=eff["out"], asbuilt=_home(eff.get("asbuilt"), eff, r["tree"]), t=now)
            else:
                tail = ""
                try:
                    tail = " | ".join(ln.strip() for ln in Path(rec["log"]).read_text(errors="replace").splitlines()
                                      if ln.startswith(("ot-build:", "    ")))[-600:]
                except OSError:
                    pass
                rec.update(state="FAILED", why=tail or "the bind stage ended without a result", t=now)
            st["auto_bind"][die] = rec
            return dict(rec)
        if rec.get("state") == "FRESH" and now - float(rec.get("t") or 0) < WAVE_STATUS_TTL_S:
            return dict(rec)
        if rec.get("state") == "FAILED" and now - float(rec.get("t") or 0) < WAVE_FAIL_RETRY_S:
            return dict(rec)
        if rec.get("state") == "WAITING" and now - float(rec.get("stale_since") or now) < AUTO_BIND_GRACE_S:
            return dict(rec)
        rt_dir = Path(os.path.realpath(RT_ROOT / (rt or die_rt(cfg, die) or "current")))
        files = [r["plan"]] + ([r["asbuilt"]] if r["asbuilt"] else []) + [str(rt_dir / "tools" / "autopilot" / "ot_build.py")]
        host, _ = pick_host(r["hosts"], r["tree"], files, run=run)
        out_root = f"{SCRATCH}/{lane}/ot-build/{die}/{Path(r['tree']).name}"
        rc, eff, text = bind_status(r, host, rt_dir, out_root, lane, emit_j, [], run=run)
        if rc == 0 and eff:
            rec.update(state="FRESH", out=eff["out"], asbuilt=_home(eff.get("asbuilt"), eff, r["tree"]), host=host, t=now)
        elif rc == 3 and eff and now - float(rec.get("stale_since") or now) < AUTO_BIND_GRACE_S:
            rec.setdefault("stale_since", now)
            rec.update(state="WAITING", host=host, t=now, why=f"bind stale; the plan lane's own bind has until "
                       f"{time.strftime('%H:%M', time.localtime(float(rec['stale_since']) + AUTO_BIND_GRACE_S))} before an auto rebind starts")
        elif rc == 3 and eff:
            cmd = bind_job(r, host, rt_dir, out_root, lane, emit_j, mem, [], run=run)
            lf = AP_DIR / "auto_bind" / f"{die}_{time.strftime('%m%d%H%M%S', time.localtime(now))}.log"
            lf.parent.mkdir(parents=True, exist_ok=True)
            with open(lf, "w") as f:
                p = (popen or subprocess.Popen)(cmd, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                                start_new_session=True, env=dict(os.environ, OT_LANE=lane))
            rec.update(state="STARTED", pid=p.pid, log=str(lf), host=host, t=now,
                       why="; ".join(ln.split("STALE", 1)[1].strip()[:160] for ln in text.splitlines() if " STALE " in ln)[:500])
        else:
            rec.update(state="FAILED", why=" | ".join(ln.strip() for ln in text.splitlines() if ln.strip())[-600:], t=now)
    except G.BuildError as e:
        rec.update(state="FAILED", why=str(e)[:600], t=now)
    st["auto_bind"][die] = rec
    return dict(rec)


class Dry(Exception):
    pass


def stream_cmd(cmd, env):
    p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    buf = []
    for ln in p.stdout:
        buf.append(ln)
        if ln.startswith(("ot-build", "OT-BUILD", "ot-run", "ot-heavy", "private-spec", "KW_")):
            log("  " + ln.rstrip()[:400])
    return p.wait(), "".join(buf)


# ---- kit --------------------------------------------------------------------------------------------------------------------------
def kit_dir(lane, die, item):
    return AP_DIR / "private_specs" / re.sub(r"[^A-Za-z0-9_.-]", "_", lane) / "ot-build" / f"{die}_{item}"


def run_kit(r, item, host, eff, rt_dir, a, kd, stream=None):
    kw = f"{rt_dir}/tools/autopilot/kit_wave.py"
    exp = swap_prefix((r.get("asbuilt") or ""), r["tree"], r["tree"])
    # the bind host names the tree by ITS real path (epyc2: scratch2 -> scratch3 alias): its paths inside the tree map back onto
    # this side's tree path before any comparison or hand-on (e2e defect D5, OPUS-PIPELINE-R2 11-22)
    home = lambda p: swap_prefix(p, eff["tree"], r["tree"]) if p and eff.get("tree") else p
    eff = dict(eff, asbuilt=home(eff.get("asbuilt")), plan=home(eff.get("plan")))
    if eff.get("asbuilt") and exp and os.path.realpath(eff["asbuilt"]) != os.path.realpath(exp):
        raise G.BuildError("the bind used refreshed R8 tables OUTSIDE the tree (the tree is sealed): " + str(eff["asbuilt"]) + "\n"
                           "  a kit must be generated from a tree that carries them.  Fork the tree (tools/fleet/ot-tree-fork SRC DST),"
                           " run ot-build with --tree DST (the tables are then refreshed in place), or hand the rows to the die plan lane.")
    stamp = time.strftime("%m%d%H%M%S")
    sd = kd / stamp                                  # private-spec --out is a DIRECTORY: spec.json, later result.json, inside
    spec = sd / "spec.json"
    cmd = ["python3", "-I", kw, "private-spec", r["die"], item, "--tree", r["tree"], "--plan", eff.get("plan") or r["plan"],
           "--bind-out", eff["out"], "--lane", a.lane, "--out", str(sd), "--goal", "finish" if a.goal != "kit" else "geom",
           "--rt", Path(rt_dir).name]
    if a.kit_host or host:
        cmd += ["--host", a.kit_host or host]
    if not G.seal_of(r["tree"]) and a.src_manifest:
        cmd += ["--src-manifest", a.src_manifest]
    for kv in a.ab or []:
        cmd += ["--ab", kv]
    if a.why:
        cmd += ["--why", a.why]
    log("ot-build: " + " ".join(shlex.quote(c) for c in cmd))
    rc, out = (stream or stream_cmd)(cmd, dict(os.environ, OT_LANE=a.lane))
    if rc != 0 or not spec.is_file():
        raise G.BuildError(f"private-spec refused (rc {rc}): " + "\n".join(out.strip().splitlines()[-6:]))
    cmd = ["python3", "-I", kw, "run-item", str(spec)]
    log("ot-build: " + " ".join(shlex.quote(c) for c in cmd))
    rc, out = (stream or stream_cmd)(cmd, dict(os.environ, OT_LANE=a.lane))
    res = sd / "result.json"
    try:
        rj = json.loads(res.read_text())
    except (OSError, ValueError):
        raise G.BuildError(f"run-item ended rc {rc} without a result.json next to {spec}: " + "\n".join(out.strip().splitlines()[-6:]))
    want = "SIGNED" if a.goal != "kit" else "PASS"
    (kd / "last.json").write_text(json.dumps(dict(spec=str(spec), result=str(res), verdict=rj.get("verdict"), stage=rj.get("stage"),
                                                  kit=rj.get("kit"), signoff=rj.get("signoff")), indent=1) + "\n")
    if rj.get("verdict") != want:
        raise G.BuildError(f"kit {r['die']}/{item}: verdict {rj.get('verdict')} at stage {rj.get('stage')} (want {want}); "
                           f"{str(rj.get('chain_reason') or rj.get('errors') or rj.get('tail') or '')[:500]}\n  result {res}")
    return rj


def main(argv=None, run=sh, stream=None, cfg=None):
    ap = argparse.ArgumentParser(prog="ot-build", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("die")
    ap.add_argument("type")
    ap.add_argument("--plan")
    ap.add_argument("--tree")
    ap.add_argument("--asbuilt")
    ap.add_argument("--lane", default=os.environ.get("OT_LANE", ""))
    ap.add_argument("--goal", choices=GOALS, default="export")
    ap.add_argument("--host", help="pin the bind host (default: least loaded host that holds the tree)")
    ap.add_argument("--out-root", help="bind out root on the bind host (default <scratch>/claude/<lane>/ot-build/<die>/<tree name>)")
    ap.add_argument("--kit-host")
    ap.add_argument("--rt", help="runtime pin sha12 (default: rt/current, resolved once)")
    ap.add_argument("--emit-j", default="auto")
    ap.add_argument("--bind-mem", default="96")
    ap.add_argument("--src-manifest", choices=("on", "off"))
    ap.add_argument("--ab", action="append", default=[])
    ap.add_argument("--why")
    ap.add_argument("--dry", action="store_true", help="report what is stale; run nothing")
    ap.add_argument("--config")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", a.lane or ""):
        log("ot-build: --lane LANE (or OT_LANE) is required")
        return 2
    try:
        if cfg is None:
            cfg = json.loads(Path(a.config or (AP_DIR / "kit_wave.json")).read_text())
        r = resolve(cfg, a.die, a.tree, a.plan, a.asbuilt)
        rt_dir = Path(os.path.realpath(RT_ROOT / (a.rt or "current")))
        if not (rt_dir / "tools" / "autopilot" / "ot_build.py").is_file():
            raise G.BuildError(f"runtime pin {rt_dir} has no tools/autopilot/ot_build.py (older than ot-build); give --rt")
        files = [r["plan"]] + ([r["asbuilt"]] if r["asbuilt"] else []) + [str(rt_dir / "tools" / "autopilot" / "ot_build.py")]
        live_plan = cfg["dies"][a.die]["plan"]
        if os.path.normpath(live_plan) != os.path.normpath(r["plan"]):
            binder = rt_dir / "tools" / "autopilot" / "ot_build.py"
            if "--remap-base" in binder.read_text(errors="replace"):
                r["remap_base"] = live_plan
                files.append(live_plan)
        host, table = pick_host(r["hosts"], r["tree"], files, run=run, pin=a.host)
        log(f"ot-build: {a.die}/{a.type} tree {r['tree']} plan {r['plan']} rt {rt_dir.name} bind env {r['env']}")
        log("ot-build: bind host " + host + (" (pinned)" if a.host else " = least loaded holder of the tree") + "\n" + "\n".join(table))
        out_root = a.out_root or f"{SCRATCH}/{a.lane}/ot-build/{a.die}/{Path(r['tree']).name}"
        eff = run_bind_stage(r, host, rt_dir, out_root, a, [a.type], run=run, stream=stream)
        ty = (eff.get("types") or {}).get(a.type)
        if not ty or not ty.get("block"):
            raise G.BuildError(f"type {a.type!r} is not a partition type of the plan {eff.get('plan')}")
        log(f"ot-build: bind {eff['out']} on {host} (bind key {str((eff.get('keys') or {}).get('bind'))[:12]})")
        if a.goal == "bind":
            return 0
        kd = kit_dir(a.lane, a.die, a.type)
        state = {}

        def kit_rule(node):
            state["rj"] = run_kit(r, a.type, host, eff, rt_dir, a, kd, stream=stream)
            node.extra = dict(kit=state["rj"].get("kit"), verdict=state["rj"].get("verdict"))
            return 0

        def export_rule(node):
            last = json.loads((kd / "last.json").read_text())
            so = (last.get("signoff") or {}).get("path")
            if not so:
                raise G.BuildError(f"no sign-off record path in {kd / 'last.json'}")
            cmd = ["python3", "-I", f"{rt_dir}/tools/autopilot/auto_export.py", "enqueue", so, "--die", a.die, "--element", a.type]
            rc, out = (stream or stream_cmd)(cmd, dict(os.environ, OT_LANE=a.lane))
            if rc != 0:
                raise G.BuildError(f"auto_export enqueue rc {rc}: {out.strip()[-300:]}")
            node.extra = dict(signoff=so)
            return 0

        dd = cfg["dies"][a.die]
        kit_inputs = [G.Input.value("type_block", ty["block"]), G.Input.value("type_rtl", ty.get("rtl")),
                      G.Input.value("plan_rest", eff.get("plan_rest")),
                      G.Input.value("gen_env", [dd.get("die_gen_env"), (dd.get("item_env") or {}).get(a.type), dd.get("gen_args"),
                                                (dd.get("type_args") or {}).get(a.type)]),
                      G.Input.value("asbuilt", eff.get("asbuilt_sha")), G.Input.value("rt", rt_dir.name), G.Input.value("env", r["env"]),
                      G.Input.value("tree", eff.get("tree_id")), G.Input.value("goal", "finish" if a.goal != "kit" else "geom"),
                      G.Input.value("ab", sorted(a.ab or []))]
        nodes = [G.Node("kit", kit_inputs, run=kit_rule, out=kd, cost="slow"),
                 G.Node("export", [], deps=["kit"], run=export_rule, out=kd)]
        rc = G.build(nodes, "kit" if a.goal in ("kit", "finish") else "export", dry=a.dry, log=log)
        if rc == 0 and "rj" in state:
            log(f"ot-build: {a.die}/{a.type} {state['rj'].get('verdict')} kit {state['rj'].get('kit')}")
        return rc
    except Dry as e:
        log(f"ot-build: DRY {e}")
        return 3
    except G.BuildError as e:
        log(f"ot-build: REFUSED {e}")
        return 1
    except (OSError, ValueError) as e:
        log(f"ot-build: REFUSED {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
