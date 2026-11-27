#!/usr/bin/env python3
"""ROW-GATE (COMPOSE-FAST 11-25, OWNER via COORD): the ONE canonical row gate for every die and lane.

Each lane wrote its own job script (fork, row, reprice, tap fix, R8 refresh, PRE twice, hand diff, elab, bind); scripts skipped
elab, missed a repair step, ran PRE four times (base, row, inside elab, inside bind) or ran on a host without the tree.  This is
the one script; lanes and integrators call it with the row and get ROW-READY json.

  row_gate.py gate --die DIE --src TREE --base PLAN --asbuilt AB --row SPEC [--row SPEC ...] --out DIR
                   [--types auto|all|T1,T2] [--cow] [--rt RT] [--lane NAME] [--ledger DIR] [--env K=V ...] [--mem GB] [--keep-tree] [--local]

  TREE      the die tree the base plan lives in (a published / sealed tree; never written: the gate forks it)
  PLAN, AB  base plan and as-built, repository-relative in TREE (e.g. physical/die_plan/qwen_kvsys/plan_of_record/plan_X.json)
  SPEC      script:ROW.py[::ARGS]   a row script, run as python3 -I ROW.py ARGS (default ARGS "{in} {out} {report}") in the launch tree
            ops:OPS.json             plan_ops.v1 replace ops ({ops: [{op, path, old, value}]}; a path whose value is neither old nor
                                     value is a conflict)
            merge:ROWBASE:ROWPLAN    3-way merge of a finished row plan: its delta vs ROWBASE onto the running plan (a path the row
                                     changes whose running value is neither the row's base nor its value is a conflict)
            Several --row apply in the order given; the rows carry intent only, NORMALIZE derives the rest.

Steps (each timed in ROW-READY.seconds):
  1 FORK     ot-tree-fork TREE DIR/tree (private, nlink 1) + rt_launch_tree.sh DIR/tree RT DIR/launch (rt tools, fork data)
  2 APPLY    the rows on the base, in order -> DIR/tree/<plan dir>/plan_row_<lane>.json
  3 NORMALIZE row_normalize.py plan phase (reprice, bank legaliser, density tap names, retap)
  4 beside each other:
      PRE-DIFF  plan_gate_pre.py check --base PLAN (base findings in a launch tree of TREE, cached; R8STALE is left to the R8
                refresh + the strict bind, which is the authority on R8; ADVISORY runs in its own process beside, WARN only)
      ELAB -> R8 -> BIND -> LAT
                bind.py elab (always; its in-bind PRE off, PRE-DIFF is the PRE) -> bind.py r8-prepass (the bind head: bus_groups.json)
                -> row_normalize.py tables (r8_refresh from it, ALWAYS before the bind; drift reported as fixed) -> bind.py bind --strict --all-gaps
                --types T (auto = types the rows + normalize changed) -> LAT against probe_top for scoped geometry
                or the full die top when a row changes planned lane prices
  5 ROW-READY DIR/ROW-READY.json (and DIR copy into --ledger): verdict READY only when apply, normalize, PRE-DIFF (0 new),
            elab, R8 refresh, strict bind (0 errors) and latency (0 FAIL) all pass; row / base / plan / as-built / changed tables
            sha256, rt sha, src tree manifest, types, findings, per-step seconds.
  The fork and launch tree are deleted with ot-delete afterwards (--keep-tree keeps them); DIR keeps the plan, the changed
  R8 tables, the bind output and the logs.

--cow runs a terminal gate against an immutable sealed source in a private
kernel overlay. Explicit --types all enables the complete whole-die chain in
that overlay under an admitted parallel CPU and memory lease. The normal plan,
changed tables, binding reports and ROW-READY receipt remain. Materialized
publication requires the ordinary fork. OT_BIND_YOSYS must name an approved
namespace-local executable on the host.

The bind env is the die's (coord autopilot/kit_wave.json dies[DIE] die_gen_env + bind_env, read on the hub), overridden by --env.
Outside an ot-run job the command re-runs itself under `ot-run --die --mem GB --dir TREE` (the die slice); --local runs here.
Exit 0 READY, 1 NOT READY, 2 usage / input error."""
import argparse
import concurrent.futures as CF
import copy
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import row_normalize as RN  # noqa: E402
import row_gate_cow as COW  # noqa: E402

SCHEMA = "row-ready.v1"
MISSING = object()
SCRATCH = "/srv/opentallas-scratch2/claude"
OT_DELETE = [os.path.expanduser("~/.local/bin/ot-delete"), "/usr/local/bin/ot-delete"]
OT_RUN = [os.path.expanduser("~/.local/bin/ot-run"), "/usr/local/bin/ot-run"]
HUB = os.environ.get("OT_ROW_GATE_HUB", "intel2")


def sha(p, n=None):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:n] if n else h.hexdigest()


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ------------------------------------------------------------------ row specs and apply
def parse_spec(spec):
    kind, _, rest = spec.partition(":")
    if kind == "script":
        path, _, args = rest.partition("::")
        return dict(kind="script", path=os.path.abspath(path), args=args or "{in} {out} {report}")
    if kind == "ops":
        return dict(kind="ops", path=os.path.abspath(rest))
    if kind == "merge":
        b, _, r = rest.partition(":")
        if not b or not r:
            raise ValueError(f"merge row needs ROWBASE:ROWPLAN: {spec}")
        return dict(kind="merge", base=os.path.abspath(b), path=os.path.abspath(r))
    raise ValueError(f"unknown row kind {kind!r} in {spec!r} (script:, ops:, merge:)")


def spec_record(s):
    rec = dict(s)
    rec["sha256"] = sha(s["path"]) if os.path.isfile(s["path"]) else None
    if s["kind"] == "merge":
        rec["base_sha256"] = sha(s["base"]) if os.path.isfile(s["base"]) else None
    return rec


def _J(o):
    return "\0MISSING" if o is MISSING else json.dumps(o, sort_keys=True)


def _lkey(lst):
    if not isinstance(lst, list) or not lst or not all(isinstance(e, dict) for e in lst):
        return None
    for k in ("name", "id", "key", "inst", "conn"):
        vals = [e.get(k) for e in lst]
        if all(isinstance(v, (str, int)) for v in vals) and len(set(vals)) == len(vals):
            return k
    return None


def merge3(cur, base, row, path="", conf=None, applied=None):
    """the row's delta (row vs base) onto cur; lists of dicts with a unique name/id/key/inst/conn merge per element, other lists
    are atomic; a changed path whose cur value is neither base nor row is a conflict (cur kept).  -> new cur"""
    conf = [] if conf is None else conf
    applied = [] if applied is None else applied
    if _J(row) == _J(base) or _J(cur) == _J(row):
        return cur
    if isinstance(cur, dict) and isinstance(base, dict) and isinstance(row, dict):
        out = dict(cur)
        for k in list(base) + [k for k in row if k not in base]:
            v = merge3(cur.get(k, MISSING), base.get(k, MISSING), row.get(k, MISSING), f"{path}/{k}", conf, applied)
            if v is MISSING:
                out.pop(k, None)
            else:
                out[k] = v
        return out
    if isinstance(cur, list) and isinstance(base, list) and isinstance(row, list):
        k = _lkey(base) or _lkey(row)
        if k and _lkey(cur) == k and _lkey(base) == k and _lkey(row) == k:
            cm, bm, rm = ({e[k]: e for e in x} for x in (cur, base, row))
            res = {}
            for n in cm:
                v = merge3(cm[n], bm.get(n, MISSING), rm.get(n, MISSING), f"{path}[{k}={n}]", conf, applied)
                if v is not MISSING:
                    res[n] = v
            for n in rm:
                if n not in cm and n not in bm:
                    res[n] = rm[n]
                    applied.append(f"{path}[{k}={n}] +add")
            order = [e[k] for e in row if e[k] in res] + [n for n in res if n not in rm]
            return [res[n] for n in order]
    if _J(cur) == _J(base):
        applied.append(path)
        return row
    conf.append(path)
    return cur


def _ptr(path):
    return [p.replace("~1", "/").replace("~0", "~") for p in path.strip("/").split("/")]


def apply_ops(raw, ops):
    """plan_ops.v1 replace ops -> (applied, conflicts)"""
    ap, conf = 0, []
    for o in ops:
        if o.get("op", "replace") != "replace":
            conf.append(f"{o.get('path')}: op {o.get('op')} not supported")
            continue
        parts = _ptr(o["path"])
        cur = raw
        try:
            for p in parts[:-1]:
                cur = cur[int(p)] if isinstance(cur, list) else cur[p]
            k = int(parts[-1]) if isinstance(cur, list) else parts[-1]
            now = cur[k]
        except (KeyError, IndexError, ValueError, TypeError):
            conf.append(f"{o['path']}: missing")
            continue
        if _J(now) == _J(o.get("old")):
            cur[k] = o["value"]
            ap += 1
        elif _J(now) == _J(o.get("value")):
            ap += 1
        else:
            conf.append(o["path"])
    return ap, conf


def apply_row(s, plan_in, plan_out, report, cwd, env, log):
    """-> dict(rc, applied, conflicts)"""
    if s["kind"] == "script":
        args = [a.format(**{"in": plan_in, "out": plan_out, "report": report}) for a in shlex.split(s["args"])]
        with open(log, "a") as lf:
            lf.write(f"== {utc()} script {s['path']} {' '.join(args)}\n")
            lf.flush()
            rc = subprocess.run([sys.executable, "-I", s["path"], *args], cwd=cwd, env=env, stdout=lf, stderr=subprocess.STDOUT).returncode
        ok = os.path.isfile(plan_out) and os.path.getsize(plan_out) > 0
        return dict(rc=rc if ok else (rc or 2), applied=None, conflicts=[] if ok else ["no plan written"])
    raw = json.loads(Path(plan_in).read_text())
    if s["kind"] == "ops":
        ops = json.loads(Path(s["path"]).read_text())
        n, conf = apply_ops(raw, ops.get("ops") if isinstance(ops, dict) else ops)
    else:
        conf, applied = [], []
        raw = merge3(raw, json.loads(Path(s["base"]).read_text()), json.loads(Path(s["path"]).read_text()), "", conf, applied)
        n = len(applied)
    Path(plan_out).write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
    return dict(rc=3 if conf else 0, applied=n, conflicts=conf[:50], n_conflicts=len(conf))


def apply_rows(specs, plan_in, plan_out, work, cwd, env, drop_failed=False):
    """apply every row in order -> (rc, [per-row record]); rc != 0 at the first row that fails or conflicts, or, with drop_failed
    (rolling compose), that row is recorded dropped=True, the running plan stays as before it, and rc != 0 only when no row applied"""
    cur, recs = plan_in, []
    for i, s in enumerate(specs):
        nxt = str(Path(work) / f"apply_{i}.json")
        r = apply_row(s, cur, nxt, str(Path(work) / f"row_{i}_report.json"), cwd, env, str(Path(work) / "apply.log"))
        recs.append(dict(spec_record(s), **r))
        if r["rc"]:
            if not drop_failed:
                return r["rc"], recs
            recs[-1]["dropped"] = True
            continue
        cur = nxt
    if cur == plan_in:
        return (recs[-1]["rc"] if recs else 2), recs
    shutil.copyfile(cur, plan_out)
    return 0, recs


# ------------------------------------------------------------------ env, launch, cleanup
def die_env(die, extra=()):
    """the die's bind env (hub kit_wave.json dies[die]: die_gen_env + bind_env, OT_* str values) + --env K=V -> (env, how)"""
    env, how = {}, "none"
    txt = None
    local = Path.home() / "coord" / "autopilot" / "kit_wave.json"
    try:
        txt, how = local.read_text(), str(local)
    except OSError:
        try:
            r = subprocess.run(["timeout", "40", "ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", HUB,
                                "cat ~/coord/autopilot/kit_wave.json"], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                txt, how = r.stdout, f"{HUB}:~/coord/autopilot/kit_wave.json"
        except (OSError, subprocess.SubprocessError):
            pass
    if txt:
        try:
            d = (json.loads(txt).get("dies") or {}).get(die) or {}
            for blk in ("die_gen_env", "bind_env"):
                for k, v in (d.get(blk) or {}).items():
                    if str(k).startswith("OT_") and isinstance(v, (str, int, float)) and not isinstance(v, bool):
                        env[str(k)] = str(v)
        except ValueError:
            how = "unreadable"
    for kv in extra:
        k, _, v = kv.partition("=")
        env[k] = v
    return env, how


def _tool(cands):
    for c in cands:
        if os.access(c, os.X_OK):
            return c
    return os.path.basename(cands[0])


def ot_delete(path, log):
    if not os.path.lexists(path):
        return 0
    with open(log, "a") as lf:
        return subprocess.run([_tool(OT_DELETE), str(path)], stdout=lf, stderr=subprocess.STDOUT).returncode


def rt_dir(rt=None):
    for c in ([rt] if rt else []) + [os.environ.get("OT_RT_CURRENT"), f"{SCRATCH}/rt/current", str(HERE.parents[1])]:
        if c and (Path(c) / "tools" / "die_plan").is_dir():
            return os.path.realpath(c)
    raise SystemExit("row_gate: no rt snapshot (--rt)")


def launch_tree(src, rt, dst, log):
    with open(log, "a") as lf:
        return subprocess.run(["bash", str(Path(rt) / "tools/autopilot/rt_launch_tree.sh"), str(src), str(rt), str(dst)],
                              stdout=lf, stderr=subprocess.STDOUT).returncode


def base_launch(src, rt, log):
    """a shared launch tree of the (unchanged) source tree for the PRE-DIFF base run: one per (src, rt), reused by every gate"""
    key = hashlib.sha256(f"{os.path.realpath(src)}\0{os.path.realpath(rt)}".encode()).hexdigest()[:16]
    d = Path(os.environ.get("OT_PRE_BASE_CACHE") or f"{SCRATCH}/.cache/pre-base") / "launch" / key
    d.parent.mkdir(parents=True, exist_ok=True)
    return d if launch_tree(src, rt, d, log) == 0 else None


def run_logged(cmd, cwd, env, log):
    t0 = time.time()
    with open(log, "w") as lf:
        lf.write(f"# {utc()} cwd={cwd}\n# {' '.join(map(shlex.quote, cmd))}\n")
        lf.flush()
        rc = subprocess.run(cmd, cwd=cwd, env=env, stdout=lf, stderr=subprocess.STDOUT).returncode
    return rc, round(time.time() - t0, 1)


def bind_summary(bind_dir):
    try:
        r = json.loads((Path(bind_dir) / "bind_report.json").read_text())
    except (OSError, ValueError):
        return dict(report=False, errors=None, classes={})
    e = r.get("errors") or []
    cl = {}
    for x in e:
        k = str(x).split()[0] if str(x).split() else "?"
        cl[k] = cl.get(k, 0) + 1
    return dict(report=True, errors=len(e), classes=cl, first=[str(x)[:240] for x in e[:12]])


def r8_only(rep):
    """a strict bind that failed on R8 staleness only (R8_STALE / R8_STALE_TOTAL rows)"""
    cl = rep.get("classes") or {}
    return bool(cl) and all(k.startswith("R8_STALE") for k in cl)


def touched_bound_types(raw, braw):
    used = {p.get("type") for p in raw.get("partitions") or []}
    return [t for t in RN.touched_types(raw, braw) if t in used]


def whole_cow_r8_pin(src, asbuilt, pre, pre_sha, extra):
    """Resolve the deliberate R8 policy from the immutable source before applying any row."""
    from pin_r8_v2 import PIN_MARK

    table, _ = RN.r8_tables(src, asbuilt)
    reference = json.loads(table.read_text()) if table is not None else {}
    if not isinstance(reference, dict):
        raise ValueError(f"invalid sealed main R8 table: {table}")
    note = str(reference.get("note", ""))
    if PIN_MARK not in note:
        if pre is not None:
            raise ValueError("pinned R8 inputs require a deliberate pin in the sealed main R8 table")
        return {}
    if pre is None:
        raise ValueError("sealed main R8 table has a deliberate pin; --r8-pin-pre, --r8-pin-pre-sha256 and --r8-pin-extra are required")
    if f"{PIN_MARK} extra={extra}:" not in note:
        raise ValueError("--r8-pin-extra disagrees with the sealed main R8 table")
    pin = (src / pre).resolve()
    if pre.is_absolute() or not pin.is_relative_to(src) or not pin.is_file():
        raise ValueError(f"--r8-pin-pre must name a file inside the sealed source: {pre}")
    if sha(pin) != pre_sha:
        raise ValueError(f"--r8-pin-pre-sha256 disagrees with the sealed source file: {pre}")
    return dict(pin_pre=pin, pin_extra=extra)


# ------------------------------------------------------------------ the gate
def gate(a):
    t_all = time.time()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(exist_ok=True)
    work = out / "work"
    work.mkdir(exist_ok=True)
    log = str(out / "logs" / "gate.log")
    rt = rt_dir(a.rt)
    src = Path(a.src).resolve()
    lane = a.lane or os.environ.get("OT_LANE") or "row"
    os.environ["OT_LANE"] = lane                          # the fork's .fork.json lane: in-process tree writers (R8 refresh) must match it
    specs = [parse_spec(s) for s in a.row]
    sec, R = {}, dict(schema=SCHEMA, lane=lane, die=a.die, host=socket.gethostname(), started=utc(), out=str(out),
                      cmd=" ".join(map(shlex.quote, sys.argv)), rt=dict(path=rt, sha=os.path.basename(rt)),
                      src_tree=dict(path=str(src)), base=dict(path=a.base), asbuilt=dict(path=a.asbuilt))
    verdict, why = "READY", []

    def done(v, reason=None):
        nonlocal verdict
        if reason:
            why.append(reason)
        if v != "READY":
            verdict = "NOT-READY"

    def finish():
        R.update(verdict=verdict, why=why, seconds=dict(sec, total=round(time.time() - t_all, 1)), finished=utc())
        p = out / "ROW-READY.json"
        p.write_text(json.dumps(R, indent=1, default=str) + "\n")
        if a.ledger:
            ledger = os.environ[COW.LEDGER] if getattr(a, "cow", False) and COW.mounted(out) else a.ledger
            Path(ledger).mkdir(parents=True, exist_ok=True)
            key = hashlib.sha256("".join(r.get("sha256") or "" for r in R.get("rows", [])).encode()).hexdigest()[:12]
            q = Path(ledger) / f"{lane}__{key}.json"
            q.write_text(p.read_text())
            R["ledger_file"] = str(q)
        print(f"ROW-GATE {verdict} lane={lane} die={a.die} plan={R.get('plan', {}).get('sha256', '-')[:12]} "
              f"seconds={R['seconds']['total']} why={'; '.join(why) or '-'} -> {p}")
        return 0 if verdict == "READY" else 1

    # inputs
    for rel in (a.base, a.asbuilt):
        if not (src / rel).is_file():
            done("NOT", f"input missing: {src / rel}")
            return finish()
    R["base"]["sha256"] = sha(src / a.base)
    R["asbuilt"]["sha256"] = sha(src / a.asbuilt)
    try:
        fj = json.loads((src / ".fork.json").read_text())
        R["src_tree"].update(manifest=fj.get("src_manifest_hash"), fork_of=fj.get("src"))
    except (OSError, ValueError):
        pass
    for s in specs:
        if not os.path.isfile(s["path"]):
            done("NOT", f"row missing: {s['path']}")
            return finish()
    r8_pin = {}
    if a.cow and a.types == "all":
        try:
            r8_pin = whole_cow_r8_pin(src, a.asbuilt, a.r8_pin_pre, a.r8_pin_pre_sha256, a.r8_pin_extra)
        except (OSError, ValueError) as e:
            done("NOT", str(e))
            return finish()
        if r8_pin:
            R["r8_pin"] = dict(pre=str(a.r8_pin_pre), sha256=a.r8_pin_pre_sha256, extra=a.r8_pin_extra)
    env, how = die_env(a.die, a.env)
    R["bind_env"] = dict(env, _source=how)
    base_env = dict(os.environ, **env, PYTHONDONTWRITEBYTECODE="1", OT_LANE=lane, TMPDIR=str(work))

    # 1 FORK
    t0 = time.time()
    tree, L = out / "tree", out / "launch"
    if getattr(a, "cow", False):
        yosys = base_env.get("OT_BIND_YOSYS")
        if not yosys or not shutil.which(yosys, path=base_env.get("PATH")):
            done("NOT", "copy-on-write needs an explicit executable OT_BIND_YOSYS pin; "
                        "the Docker daemon cannot see this private tree")
            return finish()
        try:
            if not COW.mounted(out):
                raise ValueError("copy-on-write requires the private overlay")
            R["fork"] = COW.prepare(src, tree, rt, a.base, a.asbuilt, lane, RN.r8_tables)
            R["src_tree"].update(manifest=R["fork"]["src_manifest_hash"])
        except (OSError, ValueError) as e:
            done("NOT", str(e))
            return finish()
    if not tree.is_dir():
        with open(log, "a") as lf:
            rc = subprocess.run([sys.executable, "-I", str(Path(rt) / "tools/fleet/ot-tree-fork"), str(src), str(tree), "--jobs", "32"],
                                stdout=lf, stderr=subprocess.STDOUT, env=dict(base_env)).returncode
        if rc:
            done("NOT", f"ot-tree-fork rc {rc}")
            return finish()
    if launch_tree(tree, rt, L, log):
        done("NOT", "rt_launch_tree failed")
        return finish()
    LB = base_launch(src, rt, log)
    sec["fork"] = round(time.time() - t0, 1)

    # 2 APPLY
    t0 = time.time()
    pdir = (tree / a.base).parent
    plan = pdir / (a.plan_name or f"plan_row_{re.sub(r'[^A-Za-z0-9_.-]', '_', lane)}.json")
    rc, recs = apply_rows(specs, str(tree / a.base), str(plan), str(work), str(L), dict(base_env, OT_DIE_PLAN_TOOLS=str(L / "tools/die_plan")),
                          drop_failed=a.drop_failed_rows)
    R["rows"] = recs
    sec["apply"] = round(time.time() - t0, 1)
    if rc:
        done("NOT", f"row apply rc {rc} ({recs[-1].get('kind')} {os.path.basename(recs[-1]['path'])}: {recs[-1].get('conflicts')[:3]})")
        return finish()

    # 3 NORMALIZE (plan phase)
    t0 = time.time()
    braw = json.loads((tree / a.base).read_text())
    raw = json.loads(plan.read_text())
    tap_manifest = getattr(a, "tap_manifest", None)
    tap_types = []
    reach_types = []
    try:
        if tap_manifest:
            import tap_derive

            tap_types, report = tap_derive.derive(raw, plan, tree, tap_manifest)
            (out / "tap_derive.json").write_text(json.dumps(report, indent=1) + "\n")
            R["tap_derive"] = {"types": tap_types, "report": str(out / "tap_derive.json")}
        import tap_reach_fix                  # C-TAP-REACH: plan flag tap_reach.enable, default off (derive is then a no-op)

        reach_types, reach_report = tap_reach_fix.derive(raw, plan, tree)
        if tap_reach_fix.enabled(raw):
            (out / "tap_reach.json").write_text(json.dumps(reach_report, indent=1) + "\n")
            R["tap_reach"] = {"types": reach_types, "report": str(out / "tap_reach.json")}
        nrep = RN.normalize_plan(braw, raw, str(L), (tree / a.base).resolve(), plan.resolve(), a.skip_normalize)
        if tap_types:
            import tap_offset_cover

            density = tap_derive.density_results(raw, plan, tree, tap_types)
            for tn, result in density.items():
                report[tn].update(result)
            (out / "tap_derive.json").write_text(json.dumps(report, indent=1) + "\n")
            excess = [tn for tn, result in density.items() if not result["within_limits"]]
            if excess:
                raise ValueError(f"density tap load/span still exceeds the limit: {', '.join(excess)}")
            tap_pattern = "^(?:" + "|".join(re.escape(tn) for tn in tap_types) + ")$"
            with RN.in_tree(L):
                covered = tap_offset_cover.fill(raw, plan.resolve(), types=tap_pattern)
            R["tap_derive"]["tap_offset_cover"] = covered
        if reach_types:
            import tap_offset_cover

            reach_pattern = "^(?:" + "|".join(re.escape(tn) for tn in reach_types) + ")$"
            with RN.in_tree(L):
                R["tap_reach"]["tap_offset_cover"] = tap_offset_cover.fill(raw, plan.resolve(), types=reach_pattern)
    except Exception as e:  # noqa: BLE001 - a normalize crash is a named NOT-READY, never a silent pass
        nrep = dict(error=f"{type(e).__name__}: {str(e)[:400]}")
    (out / "normalize_plan.json").write_text(json.dumps(nrep, indent=1, default=str) + "\n")
    sec["normalize"] = round(time.time() - t0, 1)
    if nrep.get("error"):
        done("NOT", f"normalize crashed: {nrep['error']}")
        return finish()
    if nrep["changed"] or tap_types or reach_types:
        RN.dump(raw, plan)
    nfail = {k: [tn for tn, x in v.items() if isinstance(x, dict) and (x.get("failed") or x.get("bank_failed"))]
             for k, v in nrep["steps"].items() if isinstance(v, dict)}
    nfail = {k: v for k, v in nfail.items() if v}
    R["normalize"] = dict(changed=nrep["changed"], failed=nfail, seconds=nrep["seconds"], report=str(out / "normalize_plan.json"))
    if nfail:
        done("NOT", f"normalize could not legalise {nfail}")
    R["plan"] = dict(path=str(plan), rel=os.path.relpath(plan, tree), sha256=sha(plan))
    if a.types == "auto":
        types = touched_bound_types(raw, braw)
    elif a.types == "all":
        types = []
    else:
        types = sorted({t for t in a.types.split(",") if t} | set(tap_types) | set(reach_types))
    R["types"] = types or "all"
    if a.types == "auto" and not types:
        done("NOT", "the rows changed no bound partition type (nothing to bind; use --types)")
        return finish()
    bind_types = row_bind_scope(types, braw, raw)
    cow_whole = getattr(a, "cow", False) and a.types == "all"
    if getattr(a, "cow", False) and not bind_types and not cow_whole:
        done("NOT", "repriced lane transport requires explicit --types all for a whole-die gate")
        return finish()
    prel = os.path.relpath(plan, tree)
    benv = dict(base_env, OT_PLAN_GATE_PRE="off")              # PRE-DIFF below is this gate's PRE

    # 4 PRE-DIFF beside ELAB -> R8 -> BIND -> LAT
    def pre():
        cmd = [sys.executable, "-I", "-B", "tools/die_plan/plan_gate_pre.py", "check", "--tree", str(L), "--plan", prel,
               "--base", a.base, "--asbuilt", a.asbuilt, "--skip", "R8STALE", "--skip", "ADVISORY", "--json", str(out / "pre.json")]
        if LB:
            cmd += ["--base-tree", str(LB)]
        rc, s = run_logged(cmd, str(L), dict(base_env), str(out / "logs/pre.log"))
        return rc, s

    def adv():                                            # ADVISORY (WARN only, ~400 s of a KV PRE) runs beside, off the gating path
        import plan_gate_pre as G
        cmd = [sys.executable, "-I", "-B", "tools/die_plan/plan_gate_pre.py", "check", "--tree", str(L), "--plan", prel,
               "--asbuilt", a.asbuilt, "--json", str(out / "pre_advisory.json")]
        for c in G.CLASSES:
            if c != "ADVISORY":
                cmd += ["--skip", c]
        return run_logged(cmd, str(L), dict(base_env), str(out / "logs/pre_advisory.log"))

    def chain():
        B = out / "bind"
        r, s = {}, {}
        rc, s["elab"] = run_logged([sys.executable, "-I", "-B", "tools/die_plan/bind.py", "elab", prel, "--out", str(B), "--asbuilt", a.asbuilt,
                                    "--mem", str(a.bind_mem)], str(L), benv, str(out / "logs/elab.log"))
        r["elab"] = rc
        if rc:
            return r, s
        t0 = time.time()
        if not a.no_r8:                                   # the elab writes no bus_groups.json: the bind head does (r8-prepass, BIND-SPEED-1118)
            r["r8_prepass"], s["r8_prepass"] = run_logged([sys.executable, "-I", "-B", "tools/die_plan/bind.py", "r8-prepass", prel, "--out", str(B),
                                                           "--asbuilt", a.asbuilt, "--mem", str(a.bind_mem)], str(L), benv,
                                                          str(out / "logs/r8_prepass.log"))
            if not (B / "bus_groups.json").is_file():
                r["r8"] = dict(rc=2, r8=f"R8 refresh not run: r8-prepass rc {r['r8_prepass']} wrote no bus_groups.json", fixed={})
                return r, s
        try:
            tr = RN.normalize_tables(str(plan), str(tree), a.asbuilt, str(B / "bus_groups.json"), **r8_pin) if not a.no_r8 else dict(rc=0, r8="skipped", fixed={})
        except Exception as e:  # noqa: BLE001
            tr = dict(rc=2, r8=f"R8 refresh crashed: {type(e).__name__}: {str(e)[:300]}", fixed={})
        s["r8"] = round(time.time() - t0, 1)
        r["r8"] = tr
        if tr["rc"]:
            return r, s
        cmd = [sys.executable, "-I", "-B", "tools/die_plan/bind.py", "bind", prel, "--out", str(B), "--asbuilt", a.asbuilt,
               "--mem", str(a.bind_mem), "--strict", "--all-gaps"] + (["--types", ",".join(bind_types)] if bind_types else [])
        r["bind"], s["bind"] = run_logged(cmd, str(L), benv, str(out / "logs/bind.log"))
        r["bind_report"] = bind_summary(B)
        if r["bind"] and r8_only(r["bind_report"]) and not a.no_r8 and (B / "bus_groups.json").is_file():
            # R8 LOOP (bind_r8_loop of the die bind scripts): the pre-pass bus groups can price a member one stage off the full bind
            # (KV g4 11-25: pv_v_pads_ffkpv 68 members bound 43 vs table 42 after the pre-pass refresh) -> refresh from THIS bind, bind again once
            t1 = time.time()
            tr2 = RN.normalize_tables(str(plan), str(tree), a.asbuilt, str(B / "bus_groups.json"), **r8_pin)
            s["r8_loop"] = round(time.time() - t1, 1)
            r["r8_loop"] = tr2
            if not tr2["rc"]:
                r["bind"], s["bind2"] = run_logged(cmd, str(L), benv, str(out / "logs/bind2.log"))
                r["bind_report"] = bind_summary(B)
        if r["bind"] == 0 and (B / "bind_report.json").is_file():
            lat_cmd = [sys.executable, "-I", "-B", "tools/die_plan/lane_asbuilt_latency.py", str(B), prel,
                       "--asbuilt", a.asbuilt, "--json", str(out / "latency.json")]
            if bind_types:
                lat_cmd.append("--probe-top")
            r["lat"], s["lat"] = run_logged(lat_cmd, str(L), dict(base_env), str(out / "logs/latency.log"))
        return r, s

    with CF.ThreadPoolExecutor(3) as ex:
        fp, fc, fa = ex.submit(pre), ex.submit(chain), ex.submit(adv)
        (pre_rc, sec["pre"]), (cr, cs) = fp.result(), fc.result()
        _arc, sec["pre_advisory"] = fa.result()
    sec.update(cs)
    try:
        R["advisories"] = dict(n=len(json.loads((out / "pre_advisory.json").read_text()).get("advisories") or []),
                               json=str(out / "pre_advisory.json"))
    except (OSError, ValueError):
        R["advisories"] = dict(n=None, log=str(out / "logs/pre_advisory.log"))
    try:
        pj = json.loads((out / "pre.json").read_text())
    except (OSError, ValueError):
        pj = {}
    R["pre"] = dict(rc=pre_rc, new=pj.get("findings"), inherited=len(pj.get("inherited") or []), gone=len(pj.get("gone") or []),
                    changed=len(pj.get("changed") or []), json=str(out / "pre.json"))
    if pre_rc:
        done("NOT", f"PRE-DIFF: {len(pj.get('findings') or [])} new finding(s)" if pj else f"PRE rc {pre_rc}")
    R["elab"] = dict(rc=cr.get("elab"), log=str(out / "logs/elab.log"))
    if cr.get("elab"):
        done("NOT", f"elab rc {cr['elab']}")
    tr = cr.get("r8")
    if tr is not None and cr.get("r8_loop") and not cr["r8_loop"]["rc"]:
        tr = dict(tr, fixed=dict(tr.get("fixed") or {}, **(cr["r8_loop"].get("fixed") or {})))
        tr["r8"] = f"R8 drift fixed in {len(tr['fixed'])} table(s) (pre-pass + one bind loop)" if tr["fixed"] else tr["r8"]
    if tr is not None:
        R["r8"] = dict(rc=tr["rc"], status=tr["r8"], fixed=tr.get("fixed"), log=(tr.get("log") or "")[-800:] if tr["rc"] else "")
        if tr["rc"]:
            done("NOT", tr["r8"])
        keep = out / "tables"
        for rel in tr.get("fixed") or {}:                     # the refreshed tables travel with the ROW-READY (sha + copy)
            dst = keep / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(L / rel, dst)
            R["r8"].setdefault("tables", {})[rel] = sha(dst)
    if "bind" in cr:
        br = cr["bind_report"]
        R["bind"] = dict(rc=cr["bind"], **br, dir=str(out / "bind"), log=str(out / "logs/bind.log"))
        if cr["bind"] or not br["report"] or br["errors"]:
            done("NOT", f"strict bind rc {cr['bind']} errors {br['errors']} {br['classes']}")
    if "lat" in cr:
        try:
            lj = json.loads((out / "latency.json").read_text())
        except (OSError, ValueError):
            lj = {}
        sm = lj.get("summary") or {}
        nf = sm.get("failed")
        R["latency"] = dict(rc=cr["lat"], fail=nf, passed=sm.get("passed"), unobserved=sm.get("unobserved"), verdict=sm.get("verdict"),
                            scope=sm.get("scope"), json=str(out / "latency.json"))
        if cr["lat"] not in (0, 5) or nf:                       # 5 = lanes of unbound types unobserved (a scoped bind)
            done("NOT", f"latency check rc {cr['lat']} (fail {nf})")
    if cow_whole and not whole_latency_complete(cr.get("lat"), R.get("latency", {})):
        done("NOT", "whole copy-on-write gate requires a complete die LAT receipt with zero unobserved lanes")
    shutil.copy2(plan, out / "plan.json")
    R["plan"]["copy"] = str(out / "plan.json")
    R["tree_deleted"] = not a.keep_tree
    if not a.keep_tree and not getattr(a, "cow", False) and (out / "bind").is_dir():
        # the fork / launch tree are deleted below: re-point the bind output's recorded paths so a bound PRE can still run (P-RUNTIME-MANIFEST)
        gone = [str(L)] + ([] if a.keep_fork else [str(tree)])
        R["bind_paths"] = relocate_bind_paths(out / "bind", gone, src, out / "bind_inputs")
        print(f"row_gate: bind paths re-pointed off the deleted fork: {R['bind_paths']}", flush=True)
    rc = finish()                                         # ROW-READY first: the 50 GB fork delete is not on the reader's path
    if not a.keep_tree and not getattr(a, "cow", False):
        for p in (L, tree) if not a.keep_fork else (L,):
            ot_delete(p, log)
    return rc


def relocate_bind_paths(bind_dir, roots, src, keep_dir):
    """P-RUNTIME-MANIFEST: bind.f / bind_report.json / the other top-level bind lists record absolute paths into the gate's launch tree
    and fork, which the gate deletes after ROW-READY, so no bound PRE (--elab-dir) could run afterwards.  Every recorded file under
    one of ROOTS is re-pointed to the sealed source tree when it is byte-identical there, else copied under KEEP_DIR (a row that
    changed it) and pointed at the copy.  Returns {rewritten, copied, missing}."""
    roots = sorted({str(Path(r)) for r in roots}, key=len, reverse=True)
    pat = re.compile("(?:" + "|".join(re.escape(r) for r in roots) + r")/[^\s\"',\]\[]+")
    stat, memo = dict(rewritten=0, copied=0, missing=0), {}

    def target(m):
        q = m.group(0)
        if q in memo:
            return memo[q]
        root = next(r for r in roots if q.startswith(r + "/"))
        rel = q[len(root) + 1:]
        memo[q] = q
        if Path(q).is_file():
            cand = Path(src) / rel
            if cand.is_file() and sha(cand) == sha(Path(q)):
                memo[q] = str(cand)
            else:
                dst = Path(keep_dir) / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(q, dst)
                memo[q] = str(dst)
                stat["copied"] += 1
        else:
            stat["missing"] += 1
        return memo[q]

    for f in sorted(Path(bind_dir).iterdir()):
        if f.is_file() and f.suffix in (".f", ".json") and not f.is_symlink():
            try:
                t = f.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            n = pat.sub(target, t)
            if n != t:
                tmp = f.with_name(f.name + ".reloc")
                tmp.write_text(n)
                os.replace(tmp, f)
    stat["rewritten"] = sum(1 for k, v in memo.items() if k != v)
    return stat


def row_bind_scope(types, base, candidate):
    """A partial top can omit the other endpoint of a repriced lane."""
    base_prices = (base.get("latency") or {}).get("lanes")
    candidate_prices = (candidate.get("latency") or {}).get("lanes")
    return types if candidate_prices == base_prices else []


def whole_latency_complete(rc, receipt):
    return (rc == 0 and receipt.get("scope") == "die" and receipt.get("verdict") == "PASS"
            and receipt.get("fail") == 0 and receipt.get("unobserved") == 0)


def whole_cow_lease(a, env=None):
    env = os.environ if env is None else env
    try:
        return int(env["OT_HEAVY_THREADS"]) > 1 and int(env["OT_HEAVY_MEM_GB"]) >= max(a.mem, a.bind_mem)
    except (KeyError, ValueError):
        return False


def under_ot_run():
    return bool(os.environ.get("OT_HEAVY_PRIO") or os.environ.get("OT_HEAVY_THREADS") or os.environ.get("OT_ROW_GATE_LOCAL"))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--die", required=True)
    g.add_argument("--src", required=True)
    g.add_argument("--base", required=True)
    g.add_argument("--asbuilt", required=True)
    g.add_argument("--row", action="append", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--types", default="auto")
    g.add_argument("--rt")
    g.add_argument("--lane")
    g.add_argument("--ledger", help="directory ROW-READY json files are copied into (the die's ALLFIX ledger dir; row_compose reads it)")
    g.add_argument("--env", action="append", default=[], help="K=V over the die bind env")
    g.add_argument("--mem", type=int, default=96, help="ot-run --mem for the whole gate (GB)")
    g.add_argument("--bind-mem", type=int, default=48)
    g.add_argument("--tap-manifest", type=Path, help="native placed sink bins manifest for per-cut tap derivation")
    g.add_argument("--skip-normalize", action="append", default=[], choices=RN.STEPS)
    g.add_argument("--no-r8", action="store_true", help="do not refresh R8 tables (the strict bind still checks them)")
    g.add_argument("--r8-pin-pre", type=Path, help="sealed-source relative pre-derive R8 table for whole --cow")
    g.add_argument("--r8-pin-pre-sha256", help="expected SHA-256 of the sealed pre-derive R8 table")
    g.add_argument("--r8-pin-extra", type=int, help="deliberate R8 pin extra cycles from the sealed main R8 table")
    g.add_argument("--keep-tree", action="store_true", help="keep the fork and the launch tree")
    g.add_argument("--keep-fork", action="store_true", help="keep the fork (the rolling compose publishes it), delete the launch tree")
    g.add_argument("--drop-failed-rows", action="store_true", help="a row that fails to apply is dropped (recorded), the rest go on")
    g.add_argument("--plan-name", help="file name of the gated plan in the fork's plan dir (default plan_row_<lane>.json)")
    g.add_argument("--local", action="store_true", help="run here, not through ot-run --die")
    g.add_argument("--light", action="store_true", default=os.environ.get("OT_ROW_GATE_LIGHT") != "0",
                   help="P-POSTPUBLISH-DISK: use the sparse --cow overlay instead of a full 60 GB fork when the gate is eligible "
                        "(scoped types, sealed source, pinned OT_BIND_YOSYS, no --keep-*); otherwise the ordinary fork. DEFAULT ON (COORD 11-26); OT_ROW_GATE_LIGHT=0 turns it off")
    g.add_argument("--cow", action="store_true",
                   help="isolate a terminal gate in a copy-on-write overlay of a sealed source")
    a = ap.parse_args(argv)
    if a.light and not a.cow:
        use, why = COW.light_choice(Path(a.src).resolve(), rt_dir(a.rt), a.types, a.keep_tree or a.keep_fork)
        print(f"row_gate: light fork {'ON (' + why + ')' if use else 'off, ordinary fork: ' + why}", flush=True)
        if use:
            a.cow = True
            argv = [*argv, "--cow"]
    cow_whole = a.cow and a.types == "all"
    pin_flags = [v is not None for v in (a.r8_pin_pre, a.r8_pin_pre_sha256, a.r8_pin_extra)]
    if any(pin_flags):
        if not cow_whole or not all(pin_flags):
            g.error("R8 pin inputs require whole --cow and all three --r8-pin-* options")
        if not re.fullmatch(r"[0-9a-f]{64}", a.r8_pin_pre_sha256):
            g.error("--r8-pin-pre-sha256 requires a full lowercase SHA-256")
    if a.cow and (a.keep_tree or a.keep_fork):
        g.error("--cow cannot retain a materialized tree or fork")
    if cow_whole and (a.ledger or a.no_r8 or a.skip_normalize or a.drop_failed_rows):
        g.error("whole --cow requires the complete source gate and cannot stage a publication ledger")
    if not a.local and not under_ot_run():
        cmd = [_tool(OT_RUN), "--die", "--mem", str(a.mem)]
        if a.types == "all":
            cmd += ["--threads", "48"]
        cmd += ["--dir", str(Path(a.src).resolve()), "--",
                sys.executable, "-I", str(Path(__file__).resolve()), *argv, "--local"]
        print("row_gate: under ot-run --die:", " ".join(map(shlex.quote, cmd)), flush=True)
        return subprocess.run(cmd).returncode
    if a.cow:
        if cow_whole and not whole_cow_lease(a):
            g.error("whole --cow requires an admitted parallel ot-run lease covering --mem and --bind-mem")
        out, src = Path(a.out).resolve(), Path(a.src).resolve()
        try:
            if not COW.mounted(out):
                local = [] if a.local else ["--local"]
                return COW.run([str(Path(__file__).resolve()), *argv, *local], src, out, a.ledger)
        except (OSError, ValueError) as e:
            g.error(str(e))
    return gate(a)


if __name__ == "__main__":
    sys.exit(main())
