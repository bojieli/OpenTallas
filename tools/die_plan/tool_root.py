#!/usr/bin/env python3
"""TOOLROOT-1123 (COORD 16:1x, FABLE flow review: KV / QC / S81 / HEAD gates ran tools from a relative or wrong root and
silently skipped rows): the tools root a gate step actually RUNS from must be the declared rt sha, else fail closed.

declared sha  = --expect SHA, else $OT_TOOLS_SHA, else the rt/<sha> directory $OT_RT_CURRENT names (rt_pin.py --export).
                No declaration -> nothing to compare (advisory line only).
running root  = the repo root holding this file (realpath; a symlinked rt/current resolves to rt/<sha>).
Checks, all exact:
  1. the running root's own sha: an rt/<sha> snapshot directory -> its name; a git checkout -> HEAD; else unknown.  It must
     equal the declared sha (12-hex prefix compare).  Unknown with a declaration is a FAIL (fail closed).
  2. content: every tools/die_plan/*.py and physical/common_flow/* file of the declared rt manifest (rt/<sha>.manifest.json)
     hashes the same in the running root, so a dirty checkout or a hand-patched copy at the right HEAD fails too.
     A declared sha with no manifest on this host is a FAIL (the content cannot be proven).
Gate scripts:   python3 -I <tools>/die_plan/tool_root.py --expect <sha>     (rc 1 on FAIL, prints the lines)
plan_gate_pre runs the same check as class TOOLROOT (seconds)."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE_ROOT = Path(__file__).resolve().parents[2]
RT_ROOTS = tuple(f"/srv/opentallas-scratch{n}/claude/rt" for n in ("2", "", "3"))
HEX = re.compile(r"[0-9a-f]{12,40}")
CONTENT_PREFIXES = ("tools/die_plan/", "physical/common_flow/")


def declared_sha(expect=None, env=None):
    """(sha, source) or (None, reason)"""
    env = os.environ if env is None else env
    if expect:
        return (expect.strip(), "--expect") if HEX.fullmatch(expect.strip()) else (None, f"--expect {expect!r} is not a sha")
    v = (env.get("OT_TOOLS_SHA") or "").strip()
    if v:
        return (v, "$OT_TOOLS_SHA") if HEX.fullmatch(v) else (None, f"$OT_TOOLS_SHA {v!r} is not a sha")
    rc = (env.get("OT_RT_CURRENT") or "").strip()
    if rc:
        b = os.path.basename(os.path.realpath(rc).rstrip("/"))
        if HEX.fullmatch(b):
            return b, "$OT_RT_CURRENT"
    return None, "no declared rt sha"


def root_sha(root):
    """Identify an immutable runtime, a composed launch tree or a Git checkout."""
    root = Path(root).resolve()
    if HEX.fullmatch(root.name) and (root.parent / f"{root.name}.manifest.json").exists():
        return root.name
    # The launch-tree receipt names the runtime that supplied these files.
    # The caller still hashes the launch tree against the declared manifest.
    try:
        receipt = json.loads((root / ".rt_launch_ok").read_text())
        runtime = Path(receipt["rt"])
    except (OSError, ValueError, KeyError, TypeError):
        runtime = None
    if (runtime is not None and runtime.is_absolute() and HEX.fullmatch(runtime.name)
            and (runtime.parent / f"{runtime.name}.manifest.json").is_file()):
        return runtime.name
    if (root / ".git").exists():
        try:
            p = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
            if p.returncode == 0 and HEX.fullmatch(p.stdout.strip()):
                return p.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return None


def find_manifest(sha, rt_roots=RT_ROOTS):
    for r in rt_roots:
        for cand in ([Path(r) / f"{sha}.manifest.json"] + sorted(Path(r).glob(f"{sha[:12]}*.manifest.json"))
                     if Path(r).is_dir() else []):
            if cand.is_file():
                return cand
    return None


def _same(a, b):
    n = min(len(a), len(b), 12)
    return n >= 12 and a[:n] == b[:n]


def check(expect=None, root=HERE_ROOT, env=None, rt_roots=RT_ROOTS, max_lines=8, quiet_undeclared=False):
    """FAIL / WARN lines (plan_gate_pre format); quiet_undeclared: no line at all when nothing is declared"""
    sha, src = declared_sha(expect, env)
    root = Path(root).resolve()
    if sha is None:
        if src.startswith("no declared"):
            if quiet_undeclared:
                return []
            return [f"WARN TOOLROOT-ADVISORY {src}; tools run from {root} ({root_sha(root) or 'sha unknown'}); "
                    f"set $OT_TOOLS_SHA or eval rt_pin.py --export to pin it"]
        return [f"FAIL TOOLROOT {src}"]
    out = []
    have = root_sha(root)
    if have is None:
        out.append(f"FAIL TOOLROOT tools root {root} has no resolvable sha (not rt/<sha>, not a git checkout); declared {sha[:12]} ({src})")
    elif not _same(have, sha):
        out.append(f"FAIL TOOLROOT tools root {root} is {have[:12]}, declared rt {sha[:12]} ({src}): "
                   f"run the gate from <rt>/{sha[:12]}/tools")
    man = find_manifest(sha, rt_roots)
    if man is None:
        out.append(f"FAIL TOOLROOT declared rt {sha[:12]} ({src}) has no rt manifest on this host: content not provable")
        return out
    try:
        files = json.loads(man.read_text()).get("files") or {}
    except (OSError, ValueError) as e:
        return out + [f"FAIL TOOLROOT manifest {man} unreadable ({type(e).__name__})"]
    bad = []
    for rel, want in sorted(files.items()):
        if not rel.startswith(CONTENT_PREFIXES):
            continue
        p = root / rel
        try:
            got = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            got = None
        if got != want:
            bad.append(rel + (" (missing)" if got is None else ""))
    if bad:
        out.append(f"FAIL TOOLROOT-CONTENT tools root {root} differs from rt {sha[:12]} in {len(bad)} file(s): "
                   + ", ".join(bad[:max_lines]) + (" ..." if len(bad) > max_lines else ""))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tool_root", description=__doc__.split("\n\n")[0])
    ap.add_argument("--expect", help="declared rt sha (default $OT_TOOLS_SHA, else the rt dir $OT_RT_CURRENT names)")
    ap.add_argument("--root", default=str(HERE_ROOT), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    lines = check(a.expect, a.root)
    for x in lines:
        print(x)
    fails = [x for x in lines if x.startswith("FAIL ")]
    print(f"TOOLROOT {'FAIL' if fails else 'PASS'} root={Path(a.root).resolve()}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
