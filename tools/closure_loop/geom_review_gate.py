#!/usr/bin/env python3
"""GEOM-REVIEW intake gate (OWNER RULE 2026-10-23).

"For the failing elements, you must perform thorough and independent visual geometry review before submitting another
place and route."  A ref_tile route whose element (spec "block") has failure history is REFUSED at closure-loop intake
(and by `closure_loop.py validate`, which ttv.py runs before it queues) unless the independent reviewer (GEOM-REVIEW,
lanes/GEOM-REVIEW.md) recorded a PASS for the CONTENT HASH of the kit being routed.

Failure history of a block (any one):
  loop   a closure-loop job of that block ended in a failure state (NEEDS_RTL / NEEDS_HUMAN / EARLY_FAIL_* /
         FLOORPLAN_MARGIN / PREROUTE_MARGIN) and no CLOSED job of the block finished after it;
  api    the fleet-viz element row is open (not closed*, not superseded) with failed > 0;
  coord  the coordinator's visual review (COORD_VERDICTS.tsv) marked a kit of that top BAD / BAD-PARENT and the element
         is not closed since.
REFUSED / INVALID / CANCELLED jobs spent no route and are not failures.

Kit content hash: sha256 over "<relative path> <git blob id>\\n" of every file under physical/ref_tile/<kit>/ (sorted),
excluding views/, gate_layout/ and record/ (route outputs).  Same value from git (kit@commit) or from a working tree.

Verdict store (latest record per hash wins; a FAIL after a PASS blocks):
  - JSON files in GEOM_REVIEW_DIR (default /home/ubuntu/claude-takeover-20261007/geom_review/verdicts) and in
    <repo>/results/geom_review/ (working tree), and results/geom_review/*.json on origin/main;
  - VERDICT lines in lanes/GEOM-REVIEW.md: "VERDICT <element> <kit@commit> PASS|FAIL hash=<h> ...".
Mode: STATE/geom_review.json {"mode": "refuse"|"warn"|"off"} (closure_loop._state_mode), default refuse.

CLI:
  geom_review_gate.py hash physical/ref_tile/<kit>[@<commit>] [--repo R]
  geom_review_gate.py check <spec.json> [--repo R]
  geom_review_gate.py history <block>
  geom_review_gate.py record <element> <kit@commit> PASS|FAIL --reasons ... --fixes ... [--repo R]   (reviewer only)
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

COORD = Path(os.environ.get("GEOM_REVIEW_COORD", "/home/ubuntu/claude-takeover-20261007"))
VERDICT_DIR = Path(os.environ.get("GEOM_REVIEW_DIR", str(COORD / "geom_review" / "verdicts")))
LANE = Path(os.environ.get("GEOM_REVIEW_LANE", str(COORD / "lanes" / "GEOM-REVIEW.md")))
COORD_VERDICTS = Path(os.environ.get("GEOM_REVIEW_COORD_VERDICTS",
                                     "/home/ubuntu/scratch/tile-review-1023/COORD_VERDICTS.tsv"))
ELEMENTS_URL = os.environ.get("GEOM_REVIEW_ELEMENTS_URL", "http://localhost:8765/api/elements")
STATE = Path(os.environ.get("CL_STATE", str(Path.home() / ".local/state/closure_loop")))
API_CACHE_S = 600

FAIL_STATES = {"NEEDS_RTL", "NEEDS_HUMAN", "FLOORPLAN_MARGIN", "PREROUTE_MARGIN"}
EXCLUDED_DIRS = ("views/", "gate_layout/", "record/")
KIT_RE = re.compile(r"physical/ref_tile/([A-Za-z0-9_.-]+)/kit\.env")
VERDICT_RE = re.compile(r"^\s*-?\s*VERDICT\s+(\S+)\s+(\S+)\s+(PASS-CONDITIONAL|PASS|FAIL)(?![\w-]).*?\bhash=([0-9a-f]{12,64})", re.M)
BAD = ("BAD", "BAD-PARENT")


def is_fail_state(status: str) -> bool:
    return status in FAIL_STATES or str(status).startswith("EARLY_FAIL")


# ------------------------------------------------------------------------------------------------- kit content hash
def _blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _digest(entries) -> str:
    h = hashlib.sha256()
    for rel, blob in sorted(entries):
        if rel.startswith(EXCLUDED_DIRS):
            continue
        h.update(f"{rel} {blob}\n".encode())
    return h.hexdigest()


def kit_hash_git(repo: str, commit: str, kitdir: str) -> str | None:
    kitdir = kitdir.rstrip("/")
    r = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", commit, "--", kitdir + "/"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None
    ents = []
    for ln in r.stdout.splitlines():
        meta, _, path = ln.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob":
            ents.append((path[len(kitdir) + 1:], parts[2]))
    return _digest(ents) if ents else None


def kit_hash_fs(kitdir: str) -> str | None:
    base = Path(kitdir)
    ents = []
    for p in base.rglob("*"):
        if p.is_file():
            ents.append((p.relative_to(base).as_posix(), _blob_id(p.read_bytes())))
    return _digest(ents) if ents else None


def kit_hash(ref: str, repo: str = ".") -> str | None:
    """'physical/ref_tile/<kit>@<commit>' (git) or a kit directory (working tree)"""
    if "@" in ref:
        kitdir, commit = ref.rsplit("@", 1)
        return kit_hash_git(repo, commit, kitdir)
    return kit_hash_fs(ref)


def spec_kit(spec: dict) -> str | None:
    """physical/ref_tile/<kit> of a ref_tile route spec (the route command's kit.env), else spec 'kit'"""
    st = (spec.get("stages") or {}).get("route")
    cmd = st.get("cmd", "") if isinstance(st, dict) else ""
    m = KIT_RE.search(cmd or "")
    if m:
        return f"physical/ref_tile/{m.group(1)}"
    k = spec.get("kit")
    if isinstance(k, str) and k:
        return k if k.startswith("physical/") else f"physical/ref_tile/{k}"
    return None


# ------------------------------------------------------------------------------------------------- verdict store
def _ts(s) -> float:
    try:
        return dt.datetime.fromisoformat(str(s)).timestamp()
    except (TypeError, ValueError):
        return 0.0


def load_verdicts(repo: str | None = None, extra_dirs=()) -> list[dict]:
    """every recorded verdict: {element, kit, verdict, hash, at(float), src}"""
    out = []
    dirs = [VERDICT_DIR, *map(Path, extra_dirs)]
    if repo:
        dirs.append(Path(repo) / "results" / "geom_review")
    for d in dirs:
        for p in sorted(glob.glob(str(d / "*.json"))):
            try:
                r = json.loads(Path(p).read_text())
            except (OSError, ValueError):
                continue
            if isinstance(r, dict) and r.get("hash") and r.get("verdict") in ("PASS", "PASS-CONDITIONAL", "FAIL"):
                out.append(dict(r, at=_ts(r.get("at")), src=p))
    if repo:
        try:
            ls = subprocess.run(["git", "-C", str(repo), "ls-tree", "--name-only", "origin/main", "results/geom_review/"],
                                capture_output=True, text=True, timeout=60)
            for p in ls.stdout.split():
                if p.endswith(".json"):
                    s = subprocess.run(["git", "-C", str(repo), "show", f"origin/main:{p}"],
                                       capture_output=True, text=True, timeout=60)
                    try:
                        r = json.loads(s.stdout)
                    except ValueError:
                        continue
                    if isinstance(r, dict) and r.get("hash") and r.get("verdict") in ("PASS", "PASS-CONDITIONAL", "FAIL"):
                        out.append(dict(r, at=_ts(r.get("at")), src=f"origin/main:{p}"))
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        text = LANE.read_text()
    except OSError:
        text = ""
    mt = LANE.stat().st_mtime if text else 0.0
    for i, m in enumerate(VERDICT_RE.finditer(text)):
        # lane lines carry no machine time: order of appearance, just before the lane's mtime
        out.append(dict(element=m.group(1), kit=m.group(2), verdict=m.group(3), hash=m.group(4),
                        at=mt - 1e6 + i, src=f"{LANE}:VERDICT#{i}"))
    return out


def verdict_for(h: str, verdicts) -> dict | None:
    """latest verdict whose hash matches (12+ hex prefix accepted on either side)"""
    best = None
    for v in verdicts:
        vh = v["hash"]
        if h.startswith(vh) or vh.startswith(h):
            if best is None or v["at"] >= best["at"]:
                best = v
    return best


def record(element: str, kitref: str, verdict: str, h: str, reasons: str, fixes: str, reviewer: str = "GEOM-REVIEW",
           out_dirs=()) -> dict:
    at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    kit = kitref.rsplit("@", 1)[0].rstrip("/").split("/")[-1]
    rec = dict(element=element, kit=kitref, verdict=verdict, hash=h, reasons=reasons, fixes=fixes, reviewer=reviewer,
               at=at, rule="OWNER 2026-10-23 independent visual geometry review before P&R of a failing element")
    for d in [VERDICT_DIR, *map(Path, out_dirs)]:
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{element}__{kit}__{h[:12]}.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


# ------------------------------------------------------------------------------------------------- failure history
_API = {"t": 0.0, "rows": None}


def api_rows(timeout: float = 8.0) -> dict | None:
    if _API["rows"] is not None and time.time() - _API["t"] < API_CACHE_S:
        return _API["rows"]
    try:
        with urllib.request.urlopen(ELEMENTS_URL, timeout=timeout) as r:
            rows = json.loads(r.read()).get("rows") or []
        _API.update(t=time.time(), rows={x["element"]: x for x in rows if isinstance(x, dict) and x.get("element")})
    except Exception:  # noqa: BLE001  (the viz being down never decides the gate on its own)
        _API.update(t=time.time(), rows={})
    return _API["rows"]


def coord_bad(path: Path = COORD_VERDICTS) -> dict:
    """top -> [(row element, verdict, reason)] for COORD BAD rows; plus the file mtime under key None"""
    out = {}
    try:
        lines = path.read_text().splitlines()
        out[None] = path.stat().st_mtime
    except OSError:
        return out
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) >= 3 and f[2] in BAD:
            out.setdefault(f[0].split("__")[0], []).append((f[0], f[2], f[6] if len(f) > 6 else ""))
    return out


def failure_history(block: str, jobs, api: dict | None = None, coord: dict | None = None) -> list[str]:
    """reasons the element counts as FAILING (empty: not failing).  jobs = closure-loop job states"""
    mine = [x for x in jobs if (x.get("spec") or {}).get("block") == block]
    fails = [x for x in mine if is_fail_state(x.get("status", ""))]
    closed = [x for x in mine if x.get("status") == "CLOSED"]
    last_closed = max((_ts(x.get("updated")) for x in closed), default=0.0)
    why = []
    late = [x for x in fails if _ts(x.get("updated")) > last_closed]
    if late:
        lf = max(late, key=lambda x: _ts(x.get("updated")))
        why.append(f"loop: {len(late)} failed route(s) since the last CLOSED (latest {lf.get('name')} "
                   f"{lf.get('status')} {str(lf.get('updated'))[:16]})")
    row = (api or {}).get(block)
    cat = str((row or {}).get("category") or "")
    open_ = bool(row) and not cat.startswith("closed") and cat != "superseded"
    if open_ and int(row.get("failed") or 0) > 0:
        why.append(f"api: open element ({cat}) with {row.get('failed')} failed job(s)")
    coord = coord if coord is not None else {}
    if block in coord and not (row and cat.startswith("closed")) and last_closed < float(coord.get(None) or 0):
        e, v, r = coord[block][0]
        why.append(f"coord: {v} {e} ({r[:120]})")
    return why


# ------------------------------------------------------------------------------------------------- the gate
def check(spec: dict, repo: str, jobs, api: dict | None = None, coord: dict | None = None,
          verdicts=None) -> dict:
    """{"verdict": PASS|REFUSE|SKIP, "message", "hash", "kit", "failing"}"""
    if not spec.get("ref_tile"):
        return {"verdict": "SKIP", "message": "not a ref_tile route"}
    kit = spec_kit(spec)
    block = spec.get("block")
    commit = str((spec.get("source") or {}).get("commit", ""))
    if not kit or not block or not commit:
        return {"verdict": "SKIP", "message": "no kit / block / commit to judge"}
    why = failure_history(block, jobs, api if api is not None else api_rows(),
                          coord if coord is not None else coord_bad())
    if not why:
        return {"verdict": "SKIP", "message": f"{block}: no failure history", "kit": kit}
    h = kit_hash_git(repo, commit, kit)
    if not h:
        return {"verdict": "REFUSE", "kit": kit, "failing": why,
                "message": f"GEOM_REVIEW: {block} is a FAILING element ({'; '.join(why)}) and kit {kit}@{commit[:9]} "
                           f"cannot be hashed at its commit (not in the repo?)"}
    v = verdict_for(h, verdicts if verdicts is not None else load_verdicts(repo))
    req = (f"REQ {block} {kit}@{commit[:9]} <render png> <stats json> <author> in {LANE} "
           f"(OWNER 10-23: independent visual geometry review before another P&R of a failing element)")
    if v is None:
        return {"verdict": "REFUSE", "kit": kit, "hash": h, "failing": why,
                "message": f"GEOM_REVIEW: {block} is a FAILING element ({'; '.join(why)}); no GEOM-REVIEW verdict for "
                           f"kit {kit}@{commit[:9]} hash={h[:16]}. File: {req}"}
    if v["verdict"] not in ("PASS", "PASS-CONDITIONAL"):
        return {"verdict": "REFUSE", "kit": kit, "hash": h, "failing": why,
                "message": f"GEOM_REVIEW: kit {kit}@{commit[:9]} hash={h[:16]} has a GEOM-REVIEW FAIL ({v['src']}): "
                           f"apply its required fixes, then file a new {req}"}
    cond = v["verdict"] == "PASS-CONDITIONAL"
    return {"verdict": "PASS", "kit": kit, "hash": h, "failing": why, "conditional": cond,
            "message": f"GEOM_REVIEW {v['verdict']}{' (route allowed; open condition logged, see the verdict)' if cond else ''} for {kit}@{commit[:9]} hash={h[:16]} ({v['src']})"}


def load_jobs(state: Path = STATE) -> list[dict]:
    out = []
    for p in glob.glob(str(state / "jobs" / "*.json")):
        try:
            out.append(json.loads(Path(p).read_text()))
        except (OSError, ValueError):
            continue
    return out


def jobs_for_block(block: str, state: Path = STATE) -> list[dict]:
    """cheap: only the job files that mention the block (grep), for CLI use"""
    r = subprocess.run(["grep", "-lE", f'"block": ?"{re.escape(block)}"', "-r", "--include=*.json", str(state / "jobs")],
                       capture_output=True, text=True)
    out = []
    for p in r.stdout.split():
        try:
            out.append(json.loads(Path(p).read_text()))
        except (OSError, ValueError):
            continue
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=os.environ.get("CL_REPO", "/home/ubuntu/OpenTallas"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("hash"); s.add_argument("ref")
    s = sub.add_parser("check"); s.add_argument("spec")
    s = sub.add_parser("history"); s.add_argument("block")
    s = sub.add_parser("record"); s.add_argument("element"); s.add_argument("kitref")
    s.add_argument("verdict", choices=("PASS", "PASS-CONDITIONAL", "FAIL")); s.add_argument("--reasons", required=True)
    s.add_argument("--fixes", default="-"); s.add_argument("--hash"); s.add_argument("--out", action="append", default=[])
    a = ap.parse_args(argv)
    if a.cmd == "hash":
        h = kit_hash(a.ref, a.repo)
        print(h or "")
        return 0 if h else 1
    if a.cmd == "history":
        why = failure_history(a.block, jobs_for_block(a.block), api_rows(), coord_bad())
        print("\n".join(why) if why else "no failure history")
        return 0
    if a.cmd == "check":
        spec = json.loads(Path(a.spec).read_text())
        res = check(spec, a.repo, jobs_for_block(spec.get("block", "")))
        print(f"{res['verdict']}: {res['message']}")
        return 1 if res["verdict"] == "REFUSE" else 0
    if a.cmd == "record":
        h = a.hash or kit_hash(a.kitref, a.repo)
        if not h:
            print("cannot hash kit", file=sys.stderr)
            return 1
        rec = record(a.element, a.kitref, a.verdict, h, a.reasons, a.fixes, out_dirs=a.out)
        print(f"VERDICT {a.element} {a.kitref} {a.verdict} hash={h[:16]} {a.reasons} | FIX: {a.fixes}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
