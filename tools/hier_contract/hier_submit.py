#!/usr/bin/env python3
"""Closure-loop submit hook for the TOP-DOWN HIERARCHY CONTRACT (owner 2026-10-11).

check(spec, git, mode) finds every hard-child view a parent job names (calibrate / route commands and the scripts
they call, one level: a directory D whose D/<basename>.lef exists at the source commit, --macro-view NAME=D, or a
literal .lef path; generated memory macros under physical/asap7_memory_macros/ are not hard children) and runs
child_lint on each (libs = <cell>_{tt,ff,ss}.lib beside the LEF; contract from spec "hier_contract":
{"file": <die.json>, "slots": {<cell>: <slot>}} when given).

mode "warn" (default): verdict WARN with the failures (the loop logs them and notes them in the job's checks);
mode "refuse": verdict REFUSE.  Spec "hier_lint": false opts out; {"mode": ..., "skip": "f,g"} overrides per job.
CLI: hier_submit.py SPEC.json [...] [--repo DIR] [--mode warn|refuse]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import child_lint  # noqa: E402
import macro_grid_lint as mgl  # noqa: E402

MEMORY_MACROS = "physical/asap7_memory_macros/"
MEMORY_CELL = re.compile(r"^ot_(?:sram|rom|rf|regfile)_")        # generated memory macros, wherever their view sits
PATH_TOK = re.compile(r"(?:\{SRC\}/|/src/|\$\{?SRC\}?/)?((?:physical|results)/[\w./+-]+)")


def child_views(spec: dict, git) -> list[str]:
    """repo paths of the hard-child LEFs a parent job names"""
    commit = str((spec.get("source") or {}).get("commit", ""))
    st = spec.get("stages") or {}
    cmds = [st[k]["cmd"] for k in ("route", "calibrate") if isinstance(st.get(k), dict) and st[k].get("cmd")]
    texts = []
    for cmd in cmds:
        env: dict = {}
        mgl.run_assigns(cmd.replace("&&", ";"), env, set())
        texts.append(mgl.expand(cmd, env))
        for sc in re.findall(r"[\w./${}:-]+\.(?:sh|py)\b", cmd):
            p = mgl.norm(mgl.expand(sc, env))
            body = git.show(commit, p) if p else None
            if body and len(body) < 400_000:
                senv = dict(env)
                mgl.run_assigns(body, senv, set(env))
                texts.append(mgl.expand(re.sub(r"(?m)#.*$", "", body), senv))
    cands = set()
    for t in texts:
        for name, d in re.findall(r"--macro-view\s+(?:([\w.-]+)=)?(\S+)", t):
            d = mgl.norm(d.rstrip("/").strip("'\""))
            if d and not d.endswith(".lef"):
                cands.add(f"{d}/{name or d.rsplit('/', 1)[-1]}.lef")
        for tok in PATH_TOK.findall(t):
            tok = tok.rstrip("/.,;:")
            if "$" in tok:
                continue
            if tok.endswith(".lef"):
                cands.add(tok)
            elif "." not in tok.rsplit("/", 1)[-1]:
                cands.add(f"{tok}/{tok.rsplit('/', 1)[-1]}.lef")
    out = []
    for c in sorted(cands):
        if c.startswith(MEMORY_MACROS) or MEMORY_CELL.match(c.rsplit("/", 1)[-1]) or not git.exists(commit, c):
            continue
        txt = git.show(commit, c) or ""
        if re.search(r"(?m)^\s*CLASS\s+BLOCK\b", txt):
            out.append(c)
    return out


def lint_view(lef_path: str, git, commit: str, contract: dict | None, skip: set) -> dict:
    d, cellfile = lef_path.rsplit("/", 1)
    with tempfile.TemporaryDirectory(prefix="hsub-") as td:
        lef = Path(td) / cellfile
        lef.write_text(git.show(commit, lef_path) or "")
        cell = child_lint.parse_lef(lef.read_text())["name"]
        for c in ("tt", "ff", "ss"):
            p = f"{d}/{cell}_{c}.lib"
            if c == "tt":
                txt = git.show(commit, p)
                if txt is not None:
                    (Path(td) / f"{cell}_tt.lib").write_text(txt)
            elif git.exists(commit, p):
                (Path(td) / f"{cell}_{c}.lib").write_text("")     # (d) checks presence only
        cpath = slot = None
        if contract and contract.get("file") and (contract.get("slots") or {}).get(cell):
            txt = git.show(commit, contract["file"])
            if txt:
                cpath = str(Path(td) / "contract.json")
                Path(cpath).write_text(txt)
                slot = contract["slots"][cell]
        return child_lint.lint(str(lef), td, cpath, slot, skip)


def check(spec: dict, git, mode: str = "warn") -> dict:
    cfg = spec.get("hier_lint", True)
    if cfg is False:
        return {"verdict": "SKIP", "message": "hier_lint opted out"}
    skip = set()
    if isinstance(cfg, dict):
        mode = cfg.get("mode", mode)
        skip = {x.strip() for x in str(cfg.get("skip", "")).split(",") if x.strip()}
    if mode == "off":
        return {"verdict": "SKIP", "message": "hier_lint mode off"}
    commit = str((spec.get("source") or {}).get("commit", ""))
    views = child_views(spec, git)
    if not views:
        return {"verdict": "SKIP", "message": "no hard-child views named by the job"}
    res, bad = {}, []
    for v in views:
        try:
            r = lint_view(v, git, commit, spec.get("hier_contract"), skip)
        except (OSError, ValueError, KeyError) as ex:
            res[v] = {"verdict": "ERROR", "error": str(ex)[:200]}
            continue
        res[v] = {k: r[k] for k in ("verdict", "fails", "warns", "summary")}
        if r["verdict"] == "FAIL":
            bad.append(f"{v.rsplit('/', 1)[-1]}: " + " | ".join(f[:220] for f in r["fails"]))
    if not bad:
        return {"verdict": "PASS", "views": res, "message": f"hier lint: {len(views)} hard-child views PASS "
                + "; ".join(r.get("summary", "")[:120] for r in res.values())}
    verdict = "REFUSE" if mode == "refuse" else "WARN"
    return {"verdict": verdict, "views": res,
            "message": f"HIER_LINT{'' if verdict == 'REFUSE' else ' WARN'}: {len(bad)} of {len(views)} hard children fail "
                       f"tools/hier_contract/child_lint.py: " + " || ".join(bad)}


class Git(mgl.Git):
    def exists(self, commit, path):
        return subprocess.run(["git", "-C", self.repo, "cat-file", "-e", f"{commit}:{path}"],
                              capture_output=True, timeout=60).returncode == 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--repo", default=str(HERE.parent.parent))
    ap.add_argument("--mode", default="warn", choices=("warn", "refuse"))
    a = ap.parse_args(argv)
    g = Git(a.repo)
    for s in a.specs:
        d = json.loads(Path(s).read_text())
        spec = d.get("spec", d)
        r = check(spec, g, a.mode)
        print(f"{spec.get('name')}: {r['verdict']} {r['message'][:1200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
