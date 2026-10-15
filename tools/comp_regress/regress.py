#!/usr/bin/env python3
"""comp_regress: die-level composition regression (diesim-1012).

Registry tools/comp_regress/runs.json: builds (one simulator binary each), vectors (one exported stimulus + golden
each) and runs (build x vector, or build x stage, with the expected verdict: pass, or fail for a mutant).
Coverage results/rtl/comp_regress/coverage.json: the repo files each build read (its Verilator __ver.d files, plus
the build's cover_extra generator globs) and the files every vector depends on (vector_cover globs).

    regress.py plan    --base A --head B             runs whose covered files changed in A..B (unknown coverage = rerun)
    regress.py emit    --sha S --root DIR --runs ... the host driver script (builds in memory-capped waves, each
                                                     build's runs start as soon as it links)
    regress.py launch  --host H --sha S --root DIR --runs ... [--vec-from HOST:DIR]
                                                     stage the source on H (worktree of ~/OpenTallas, else git archive
                                                     piped from here), copy vectors from a fixture host if H has no
                                                     fixtures, start the driver detached (nohup setsid)
    regress.py collect --host H --root DIR           fetch per-run verdicts + build coverage -> results/rtl/comp_regress/
    regress.py nightly --host H [--vec-from ...]     plan(last tested main .. origin/main) then launch; the cron entry

Run selectors (--runs): run ids, build ids (all of its runs), 'all', or 'affected:A..B'.
Cron (documented, not installed; localhost, every 6 h, results land in the host root then `collect`):
    17 */6 * * * cd $HOME/OpenTallas && git fetch -q origin && python3 tools/comp_regress/regress.py nightly \\
        --host ot-epyc1tb >> $HOME/comp_regress_cron.log 2>&1
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shlex
import subprocess as sp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "tools/comp_regress/runs.json"
OUTD = ROOT / "results/rtl/comp_regress"
COV = OUTD / "coverage.json"
SSH = ["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes"]


def reg():
    return json.loads(REG.read_text())


def git(*a):
    return sp.run(["git", "-C", str(ROOT), *a], check=True, capture_output=True, text=True).stdout


def select(R, spec):
    """--runs tokens -> ordered run ids."""
    ids = [r["id"] for r in R["runs"]]
    out = []
    for t in spec:
        if t == "all":
            out += ids
        elif t.startswith("affected:"):
            a, b = t.split(":", 1)[1].split("..")
            out += plan(R, a, b)["runs"]
        elif t in R["builds"]:
            out += [r["id"] for r in R["runs"] if r["build"] == t]
        elif t in ids:
            out.append(t)
        else:
            raise SystemExit(f"unknown run / build '{t}'")
    return list(dict.fromkeys(out))


def match(f, globs):
    return any(fnmatch.fnmatch(f, g) or (g.endswith("/**") and f.startswith(g[:-2])) for g in globs)


def plan(R, base, head):
    """Runs whose build or vector reads a file changed in base..head."""
    changed = [x for x in git("diff", "--name-only", f"{base}..{head}").split("\n") if x]
    cov = json.loads(COV.read_text()) if COV.exists() else {"builds": {}}
    hit_b, why = set(), {}
    for b, spec in R["builds"].items():
        files = cov["builds"].get(b, {}).get("files")
        globs = spec.get("cover_extra", [])
        if files is None:
            hit_b.add(b)
            why[b] = "no recorded coverage"
            continue
        fs = set(files)
        hits = [f for f in changed if f in fs or match(f, globs)]
        if hits:
            hit_b.add(b)
            why[b] = hits[:8]
    vec_hits = [f for f in changed if match(f, R["vector_cover"])]
    runs = [r["id"] for r in R["runs"] if r["build"] in hit_b or (r.get("vector") and vec_hits)]
    return dict(base=base, head=head, changed=len(changed), builds=why, vector_files=vec_hits[:8],
                reexport=bool(vec_hits), runs=runs)


def waves(builds, budget):
    """First-fit-decreasing packing of builds into memory waves."""
    out = []
    for b, m in sorted(builds.items(), key=lambda x: -x[1]):
        for w in out:
            if sum(builds[x] for x in w) + m <= budget:
                w.append(b)
                break
        else:
            out.append([b])
    return out


def emit(R, sha, root, run_ids, budget, par, reexport=False):
    runs = [r for r in R["runs"] if r["id"] in run_ids]
    bids = list(dict.fromkeys(r["build"] for r in runs))
    vecs = sorted({r["vector"] for r in runs if r.get("vector")} |
                  {R["builds"][r["build"]]["needs"] for r in runs if R["builds"][r["build"]].get("needs")})
    env = R["env"]
    L = ["#!/bin/bash", f"# comp_regress driver: src {sha}, {len(runs)} runs, {len(bids)} builds (generated by "
         "tools/comp_regress/regress.py emit)", "set -u",
         f"G={root}; SRC=$G/src; VEC=$G/vec; export G SRC VEC",
         "mkdir -p $G/bld $G/out $G/res $G/cover $G/logs $VEC; cd $G",
         "st(){ echo \"$(date '+%F %T %Z') $*\" >> $G/STATUS.log; }; export -f st",
         "cap(){ m=$1; t=$2; shift 2; timeout $t systemd-run --user --scope -q -p MemoryMax=${m}G -p MemorySwapMax=0 "
         "-- \"$@\"; }; export -f cap"]
    for k, v in env.items():
        L.append(f'export {k}="{v}"')
    L += ['export NPY_DISABLE_CPU_FEATURES="AVX512F AVX512CD AVX512_SKX AVX512_CLX AVX512_CNL AVX512_ICL AVX512_SPR '
          'AVX512_KNL AVX512_KNM" OT_V41_FLASH_SNAPSHOT=$DS_CKPT HDC_V41_ARITH=chunk8',
          "export QWEN_FX_HISTORY=$QWEN_FX/fx/history QWEN_FX_GOLD=$QWEN_FX/gold/tp4_hs/P8191 "
          "QWEN_FX_REF=$QWEN_FX/gold/tp4_hs/oracle.json",
          'export PATH=$(dirname $VERILATOR):$PATH',
          '[ -x "$PY" ] || export PY=python3                  # a host without the fixture venv (b2.py / tput generators)',
          f'st "start src {sha} runs {len(runs)}"',
          # coverage: every repo file a build's Verilator read (all __ver.d under the build dir)
          "cover(){ find $G/bld/$1 -name '*__ver.d' -exec cat {} + 2>/dev/null | tr ' ' '\\n' | "
          "grep -oE \"^$SRC/[^ :]+\" | sed \"s|^$SRC/||\" | sort -u > $G/cover/$1.txt; }; export -f cover",
          # one run -> res/<id>.json (verdict pass / fail / error; ok = verdict == expect)
          "rec(){ python3 $SRC/tools/comp_regress/regress.py record --root $G \"$@\"; }; export -f rec"]
    # vectors: export where the fixtures are (a vector already present is reused unless the plan asked to re-export)
    for v in vecs:
        a = R["vectors"][v]["export"]
        # (a vector path that already exists -- a dir, or a link to an export still running elsewhere -- is kept)
        L.append(f'if [ {"1" if reexport else "0"} = 1 ] || [ ! -e $VEC/{v} ]; then rm -rf $VEC/{v}; '
                 f'( cd $SRC/tools && cap 80 3h $PY -m hgi_e2e.export {a} --out $VEC/{v} > $G/logs/exp_{v}.log 2>&1 ) '
                 f'&& python3 $SRC/tools/hgi_e2e/run.py prep $VEC/{v} > $G/logs/prep_{v}.log 2>&1; '
                 f'st "export {v} rc=$?"; fi &')
    L.append("wait")
    # per build: build, coverage, then its runs (background, so the next wave starts while they simulate)
    for b in bids:
        s = R["builds"][b]
        args = s.get("args", "")
        for k, v in R.get("macros", {}).items():
            args = args.replace(k, v)
        mine = [r for r in runs if r["build"] == b]
        if s["kind"] == "hgi":
            d = s.get("define")
            bld = (f"python3 $SRC/tools/hgi_e2e/run.py script --vehicle X {args} --out $G/b_{b}.sh > /dev/null && "
                   f"sed -i '/^set +e/,$d' $G/b_{b}.sh && "
                   + (f"sed -i 's|--top-module tb_hgi_e2e|+define+{d} --top-module tb_hgi_e2e|' $G/b_{b}.sh && " if d else "")
                   + f"SRC=$SRC VEC=$VEC OUT=$G/bld/{b} VERILATOR=$VERILATOR cap {s['mem_gb']} 4h bash $G/b_{b}.sh")
            rl = []
            for r in mine:
                o = f"$G/out/{r['id']}"
                rl.append(f"( mkdir -p {o}; for i in $(seq 360); do [ -f $VEC/{r['vector']}/prep.txt ] && break; sleep 60; done; "
                          f"B=$(ls $G/bld/{b}/*/obj/tb 2>/dev/null | head -1); t0=$(date +%s); "
                          + (f"$PY $SRC/tools/hgi_e2e/b2.py traffic $VEC/{r['vector']} --out {o}/b2_traffic.json > {o}/b2.log 2>&1; "
                             if re.search(r"--g B2=[12]", args) else "") +
                          f"if [ -x \"$B\" ] && [ -f $VEC/{r['vector']}/prep.txt ]; then ( cd {o} && cap {r.get('mem_gb', 6)} 6h $B "
                          f"+DIR=$VEC/{r['vector']} +OUT={o}/e2e_records.txt > {o}/run.log 2>&1; echo rc=$? >> {o}/run.log ); "
                          f"python3 $SRC/tools/hgi_e2e/run.py report {o} --out {o}/report.json > {o}/report.log 2>&1; fi; "
                          f"rec --id {r['id']} --kind hgi --dir {o} --expect {r['expect']} --secs $(( $(date +%s)-t0 )) ) &")
        elif s["kind"] == "tput":
            # a per-class unit THROUGHPUT bench (tools/hgi_unit_tput/run_*.sh, rtl/.../run_sm_tput.sh): the script builds its
            # PASS + mutant simulators into the build dir (so cover() sees their __ver.d), runs them and writes a gate;
            # the run reads the gate (pass = PASS build exact AND every mutant FAIL) and the PASS log's throughput ratio
            o = f"$G/bld/{b}"
            gen = (s["gen"].replace("{vec}", f"{o}/vec") + " && ") if s.get("gen") else ""
            bld = (f"( mkdir -p {o}; " + (f"for i in $(seq 360); do [ -f $VEC/{s['needs']}/prep.txt ] && break; sleep 60; done; "
                                          if s.get("needs") else "") +
                   f"cd $SRC && {gen}cap {s['mem_gb']} 4h bash -c {shlex.quote(s['cmd'].replace('{vec}', o + '/vec').replace('{out}', o))} )")
            rl = [f"( t0=$(date +%s); rec --id {r['id']} --kind tput --dir {o} --expect {r['expect']} "
                  f"--secs $(( $(date +%s)-t0 )) --unit {s.get('unit', '-')} --log {s.get('log', '-')} ) &" for r in mine]
        else:
            bld = (f"( cd $SRC && cap {s['mem_gb']} 4h python3 tools/qwen_missing/partition_token.py build {args} "
                   f"--build $G/bld/{b} --jobs 16 )")
            rl = []
            for r in mine:
                o = f"$G/out/{r['id']}"
                rl.append(f"( t0=$(date +%s); ( cd $SRC && cap {r.get('mem_gb', 48)} 6h python3 tools/qwen_missing/partition_token.py "
                          f"run {args} --build $G/bld/{b} --work {o} --stages {r['stage']} --threads {r.get('threads', 16)} "
                          f"> $G/logs/{r['id']}.log 2>&1 ); rec --id {r['id']} --kind qrom --log $G/logs/{r['id']}.log "
                          f"--expect {r['expect']} --secs $(( $(date +%s)-t0 )) ) &")
        L.append(f"b_{b}(){{ {bld} > $G/logs/build_{b}.log 2>&1; rc=$?; st \"build {b} rc=$rc\"; cover {b}; "
                 + " ".join(rl) + " }")
    sizes = {b: R["builds"][b]["mem_gb"] for b in bids}
    for i, w in enumerate(waves(sizes, budget)):
        L.append(f'st "wave {i}: {" ".join(w)}"; ' + " ".join(f"b_{b} &" for b in w) + " wait")
    n = len(runs)
    L.append(f'until [ $(ls $G/res | wc -l) -ge {n} ]; do sleep 120; done; st "ALL DONE"; touch $G/DONE')
    return "\n".join(L) + "\n"


def record(a):
    """Host side: one run's verdict -> res/<id>.json."""
    root = Path(a.root)
    d = dict(id=a.id, expect=a.expect, secs=int(a.secs), when=time.strftime("%F %T %Z"))
    if a.kind == "hgi":
        rep = Path(a.dir) / "report.json"
        log = Path(a.dir) / "run.log"
        if rep.exists():
            j = json.loads(rep.read_text())
            sm_ = j.get("summary") or {}
            d.update(verdict="pass" if j.get("pass_") else "fail", completion=j.get("completion"), cfg=j.get("cfg"),
                     summary=sm_, cycles=sm_.get("cycles"), b2=sm_.get("b2"))
            bt = j.get("b2_traffic")
            if bt:
                d["b2_traffic"] = {x: bt.get(x) for x in ("placement", "records", "remote_records", "remote_words",
                                                           "bcast_words", "ring_cycles_serial", "budget_cycles_per_layer",
                                                           "within_budget", "ratio")}
        else:
            d.update(verdict="error", detail="no report (no binary / vector, or the bench died)")
        if log.exists():
            tail = log.read_text(errors="replace").splitlines()[-6:]
            d["log_tail"] = [x[:240] for x in tail]
    elif a.kind == "tput":
        o = Path(a.dir)
        gate = (o / "gate").read_text().strip() if (o / "gate").exists() else ""
        d.update(gate=gate, verdict="pass" if "GATE PASS" in gate else ("fail" if gate else "error"))
        lg = o / (a.log or "-")
        if a.unit not in (None, "-") and lg.is_file():
            rp = o / "tput_report.json"
            q = sp.run([sys.executable, str(Path(__file__).resolve().parents[1] / "hgi_unit_tput/report.py"), "--unit", a.unit,
                        "--log", str(lg), "--out", str(rp)], capture_output=True, text=True)
            if rp.exists():
                j = json.loads(rp.read_text())
                pu = j.get("per_unit") or {}
                busy, cost = sum(v.get("rtl_busy", 0) for v in pu.values()), sum(v.get("sim_cost", 0) for v in pu.values())
                ratio = j.get("ratio") or (round(busy / cost, 3) if cost else None)
                d.update(ratio=ratio, rtl_service=busy, sim_cost=cost, per_op=j.get("per_op"),
                         qualified=(ratio is not None and ratio <= 1.10))
            else:
                d["report_err"] = q.stderr[-400:]
    else:
        txt = Path(a.log).read_text(errors="replace").splitlines() if Path(a.log).exists() else []
        last = next((x for x in reversed(txt) if x.startswith("{")), None)
        if last:
            j = json.loads(last)
            d.update(verdict="pass" if j.get("exact") else "fail", result=j)
        else:
            d.update(verdict="error", log_tail=[x[:240] for x in txt[-6:]])
    d["ok"] = d["verdict"] == a.expect
    (root / "res").mkdir(exist_ok=True)
    (root / "res" / f"{a.id}.json").write_text(json.dumps(d, indent=1) + "\n")


def ssh(host, cmd, inp=None, check=True):
    return sp.run(SSH + [host, cmd], input=inp, capture_output=True, text=inp is None or isinstance(inp, str),
                  check=check)


def launch(R, a, run_ids):
    root = a.root
    has_repo = ssh(a.host, "test -d ~/OpenTallas/.git && echo y", check=False).stdout.strip() == "y"
    if has_repo:
        ssh(a.host, f"mkdir -p {root} && cd ~/OpenTallas && git fetch -q origin && "
                    f"(test -d {root}/src || git worktree add -q --detach {root}/src {a.sha})")
    else:
        arc = sp.run(["git", "-C", str(ROOT), "archive", a.sha, *R["archive_paths"]],
                     capture_output=True, check=True).stdout
        sp.run(SSH + [a.host, f"mkdir -p {root}/src && tar x -C {root}/src"], input=arc, check=True)
    fixture = a.host in R["fixture_hosts"]
    runs = [r for r in R["runs"] if r["id"] in run_ids]
    if not fixture:
        bad = [r["id"] for r in runs if R["builds"][r["build"]].get("fixture")]
        if bad:
            raise SystemExit(f"{a.host} has no fixtures for {bad}")
        vecs = sorted({r["vector"] for r in runs if r.get("vector")} |
                      {R["builds"][r["build"]]["needs"] for r in runs if R["builds"][r["build"]].get("needs")})
        if vecs:
            if not a.vec_from:
                raise SystemExit("vectors live on a fixture host: pass --vec-from HOST:DIR")
            vh, vd = a.vec_from.split(":", 1)
            tar = sp.run(SSH + [vh, f"cd {vd} && tar ch {' '.join(vecs)}"], capture_output=True, check=True).stdout
            sp.run(SSH + [a.host, f"mkdir -p {root}/vec && tar x -C {root}/vec"], input=tar, check=True)
    elif a.vec_from:                                   # same host: link a previous root's vectors
        vh, vd = a.vec_from.split(":", 1)
        vecs = sorted({r["vector"] for r in runs if r.get("vector")})
        ssh(a.host, f"mkdir -p {root}/vec && cd {root}/vec && for b in {' '.join(vecs)}; do "
                    f"[ -e $b ] || [ -L $b ] || ln -s {vd}/$b $b; done")
    script = emit(R, a.sha, root, run_ids, a.mem_budget, 24, a.reexport)
    ssh(a.host, f"cat > {root}/drive.sh && chmod +x {root}/drive.sh", inp=script)
    meta = dict(sha=a.sha, host=a.host, root=root, runs=run_ids, launched=time.strftime("%F %T %Z"))
    ssh(a.host, f"cat > {root}/launch.json", inp=json.dumps(meta, indent=1))
    ssh(a.host, f"cd {root} && (nohup setsid bash drive.sh > drive.out 2>&1 < /dev/null &); echo started")
    print(json.dumps(meta))


def collect(R, a):
    meta = json.loads(ssh(a.host, f"cat {a.root}/launch.json").stdout)
    res = ssh(a.host, f"cd {a.root}/res 2>/dev/null && for f in *.json; do cat $f; echo '\x1e'; done", check=False).stdout
    rows = [json.loads(x) for x in res.split("\x1e") if x.strip()]
    covs = ssh(a.host, f"cd {a.root}/cover 2>/dev/null && for f in *.txt; do echo \"== $f\"; cat $f; done",
               check=False).stdout
    cov = json.loads(COV.read_text()) if COV.exists() else {"schema": "opentallas.comp_regress.coverage.v1", "builds": {}}
    cur = None
    for ln in covs.splitlines():
        if ln.startswith("== "):
            cur = ln[3:-4]
            cov["builds"][cur] = {"sha": meta["sha"], "files": []}
        elif cur and ln:
            cov["builds"][cur]["files"].append(ln)
    for b in list(cov["builds"]):
        if not cov["builds"][b]["files"]:
            del cov["builds"][b]                      # a build that never verilated has no coverage (rerun next time)
    OUTD.mkdir(parents=True, exist_ok=True)
    COV.write_text(json.dumps(cov, indent=1) + "\n")
    want = set(meta["runs"])
    got = {r["id"]: r for r in rows}
    summ = dict(schema="opentallas.comp_regress.summary.v1", sha=meta["sha"], host=meta["host"], root=meta["root"],
                launched=meta["launched"], collected=time.strftime("%F %T %Z"),
                complete=want <= set(got), ok=all(r["ok"] for r in rows) and want <= set(got),
                pending=sorted(want - set(got)),
                runs=[dict(id=k, **{x: got[k].get(x) for x in ("expect", "verdict", "ok", "secs", "cycles", "completion",
                                                                   "result", "detail", "b2", "b2_traffic", "gate", "ratio",
                                                                   "qualified")}) for k in meta["runs"] if k in got])
    d = OUTD / meta["sha"][:9]
    d.mkdir(parents=True, exist_ok=True)
    tag = a.host.replace("ot-", "")
    (d / f"summary_{tag}.json").write_text(json.dumps(summ, indent=1, default=str) + "\n")
    for r in rows:
        (d / "runs").mkdir(exist_ok=True)
        (d / "runs" / f"{r['id']}.json").write_text(json.dumps(r, indent=1) + "\n")
    if summ["complete"] and summ["ok"]:
        (OUTD / "last_green.json").write_text(json.dumps(dict(sha=meta["sha"], when=summ["collected"]), indent=1) + "\n")
    print(f"{meta['sha'][:9]} {a.host}: {len(got)}/{len(want)} runs, ok={summ['ok']}, "
          f"fails={[k for k, r in got.items() if not r['ok']]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    s = ap.add_subparsers(dest="cmd", required=True)
    p = s.add_parser("plan"); p.add_argument("--base", required=True); p.add_argument("--head", default="origin/main")
    for n in ("emit", "launch"):
        e = s.add_parser(n)
        e.add_argument("--sha", required=True); e.add_argument("--root", required=True)
        e.add_argument("--runs", nargs="+", default=["all"]); e.add_argument("--mem-budget", type=int, default=500)
        e.add_argument("--reexport", action="store_true")
        if n == "launch":
            e.add_argument("--host", required=True); e.add_argument("--vec-from")
    c = s.add_parser("collect"); c.add_argument("--host", required=True); c.add_argument("--root", required=True)
    r = s.add_parser("record")
    for k in ("--root", "--id", "--kind", "--expect", "--secs"):
        r.add_argument(k, required=True)
    r.add_argument("--dir"); r.add_argument("--log"); r.add_argument("--unit")
    nt = s.add_parser("nightly"); nt.add_argument("--host", required=True); nt.add_argument("--vec-from")
    nt.add_argument("--mem-budget", type=int, default=500)
    a = ap.parse_args()
    if a.cmd == "record":
        return record(a)
    R = reg()
    if a.cmd == "plan":
        print(json.dumps(plan(R, a.base, a.head), indent=1))
    elif a.cmd == "emit":
        sys.stdout.write(emit(R, a.sha, a.root, select(R, a.runs), a.mem_budget, 24, a.reexport))
    elif a.cmd == "launch":
        launch(R, a, select(R, a.runs))
    elif a.cmd == "collect":
        collect(R, a)
    elif a.cmd == "nightly":
        lg = OUTD / "last_green.json"
        head = git("rev-parse", "origin/main").strip()
        base = json.loads(lg.read_text())["sha"] if lg.exists() else None
        pl = plan(R, base, head) if base else dict(runs=[x["id"] for x in R["runs"]], reexport=True)
        if not pl["runs"]:
            print(f"nothing affected in {base}..{head}")
            return 0
        a.sha, a.root, a.reexport = head, f"/srv/opentallas-scratch/claude/comp_regress/{head[:9]}", pl["reexport"]
        launch(R, a, pl["runs"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
