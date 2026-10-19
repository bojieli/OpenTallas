#!/usr/bin/env python3
"""submit_exact.py -- SUBMIT ORDER in one step: commit -> push -> gate on that exact commit -> submit, refused LOCALLY.

Why (ROOT, 2026-10-15): the daemon refuses ref_tile jobs whose committed gate result no longer binds to the route
source or to the gate-executed daemon overlays ("SUBMIT_LINT REF_GATE: source_binding ...").  Every refusal audited
was correct (a kit/spec/RTL edit after the gate, or a gate captured before main changed a gate-shipped overlay such
as tools/orfs_hold_mm.tcl), but each was found only after the job reached the daemon.  This helper runs the daemon's
own submit check (pre_route_gate.submit_check against the same repo and daemon tree) before the spec is dropped, prints
the exact differing files (and the main commits that moved an overlay), and optionally re-gates.

    tools/closure_loop/submit_exact.py SPEC.json                         # preflight + submit (no re-gate)
    tools/closure_loop/submit_exact.py SPEC.json --commit-paths P.. -m MSG  # commit those paths first (never -A)
    tools/closure_loop/submit_exact.py SPEC.json --regate [--gate-args "--remote auto --cts --mem 24"]
    tools/closure_loop/submit_exact.py SPEC.json --dry-run               # preflight only

Run it from the worktree that holds the spec's source commit.  Steps:
 1. optional commit by path (--commit-paths) and PUSH to origin/<source.branch> (--no-push to skip); the spec's
    source.commit / name suffix follow HEAD (--follow-head, the default when committing);
 2. fetch origin main (overlay resolution uses origin/main, exactly as the daemon does);
 3. refuse if any consumed path (kit dir, spec sources, source.extra_paths) is dirty in the worktree or differs from
    the spec commit;
 4. refuse unless the source commit is on origin/<source.branch> and every grant/provenance commit the kit names
    (m6_pin_grant source_commit, *grant_commit) exists and is on an origin branch; run the daemon's submit check; on a source_binding refusal print every differing file;
 5. --regate: run pre_route_gate.py <kit> --commit <C> <gate-args>, commit the gate result by path, move the spec to
    that commit, re-check;
 6. PRE-ROUTE VISUAL REVIEW: an element on critical_tiles.txt (block or kit name) or with >= 2 earlier non-CLOSED routes
    needs a committed <kit>/gate_layout/REVIEW.json {reviewer (= the coordinator lock holder: 'coordinator ...' when
    Claude holds COORDINATOR.lock, 'codex ...' when Codex does), time, gate_commit (= the kit gate's commit; or
    geometry_sha256 from --geometry: a re-gate with the same geometry keeps the review), verdict
    APPROVED|CHANGES, checklist {lattice, std_cell_band, pin_spread, clock_entry, shape}}; else REVIEW_REQUIRED + PNGs;
 7. drop the spec atomically into the closure-loop drop dir (only after a PASS/WARN).
BENCH EVIDENCE (ROOT-2345 2026-10-17): before anything else, refuse locally what the daemon would mark INVALID / REFUSED
after the gate: a closure candidate (not hold_merge / auto_merge false) needs a behavioural expect=pass bench and an
expect=fail mutant (stages.bench, or benched_by a composition gate), and every expect=fail bench needs a fail_regex.
A committed fail_witness (the captured real mutant log; bench_lint checks the regex matches it) is optional since
GATE-FRICTION 2026-10-18: without one this WARNs and the loop captures + commits the real mutant log itself.
Exit 0 submitted (or dry-run PASS), 1 refused locally, 2 usage/git error.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "ref_tile"))
DROP = Path(os.environ.get("CL_REVIEW", "/tmp/claude-review-20261003")) / "closure_jobs"
STATE = Path(os.environ.get("CL_STATE", str(Path.home() / ".local/state/closure_loop")))
SUFFIX = re.compile(r"-([0-9a-f]{7,40})$")


def git(root, *args, check=True):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=600)
    if check and p.returncode:
        raise SystemExit(f"submit_exact: git {' '.join(args)} failed: {p.stderr.strip()[:400]}")
    return p.stdout.strip()


def kit_of(spec):
    m = re.search(r"ref_route\.sh\s+(\S+)/kit\.env", ((spec.get("stages") or {}).get("route") or {}).get("cmd", ""))
    return m.group(1) if m else None


def consumed_paths(spec):
    src = spec.get("source") or {}
    out = [kit_of(spec)] + list(spec.get("sources") or []) + list(src.get("extra_paths") or [])
    return [p for p in out if p]


def move_spec(spec, commit):
    """spec at a new source commit; the conventional '-<commit>' name suffix follows it"""
    c9 = commit[:9]
    # a kit job.json written by `ref_tile.py gen` carries the literal placeholder COMMIT in its name and record paths
    # ("<name>-<tag>-COMMIT"): resolve it to the commit (S-NET+FILL 2026-10-15: five node jobs reached the daemon as
    # "...-n6-COMMIT-<c9>" with record paths ending in "-COMMIT")
    spec = json.loads(re.sub(r'-COMMIT(?=["/])', '-' + c9, json.dumps(spec)))
    spec.setdefault("source", {})["commit"] = c9
    m = SUFFIX.search(spec["name"])
    spec["name"] = (spec["name"][:m.start()] if m else spec["name"]) + "-" + c9
    return spec


GENERATED_RE = re.compile(r"(?:^|/)(?:gate_result\.json|source_snapshot\.json|source_binding_history/.*|gate_layout/.*)$")


def generated_only(paths):
    return bool(paths) and all(GENERATED_RE.search(p) for p in paths)


def gate_file_ok(root, path):
    """an uncommitted gate_result.json is committed automatically only when its verdict is PASS / WARN"""
    if not path.endswith("gate_result.json"):
        return True
    try:
        return json.loads((Path(root) / path).read_text()).get("verdict") in ("PASS", "WARN")
    except (OSError, ValueError):
        return False


def dirty(root, commit, paths):
    """(uncommitted, differs-from-commit) consumed paths"""
    # gate_layout/ (pre_route_gate layout PNGs) is never shipped nor gate-bound: an untracked copy is not a dirty kit.
    # An untracked lint_receipt.json (tools/ref_tile/lint_receipt.py) is a cache of the kit CDC lint written by the
    # gate's regeneration: the daemon re-derives (or re-runs on the fleet) the same lint at the commit, so it is not dirt.
    unc = [ln.split(None, 1)[1] for ln in git(root, "status", "--porcelain", "--", *paths).splitlines()
           if ln.strip() and not (ln.startswith("??") and ("/gate_layout/" in "/" + ln.split(None, 1)[1]
                                                          or ln.split(None, 1)[1].endswith("/lint_receipt.json")))]
    head = git(root, "rev-parse", "HEAD")
    diff = git(root, "diff", "--name-only", commit, head, "--", *paths).splitlines() if not head.startswith(commit) else []
    return unc, [d for d in diff if d]


def on_origin(root, commit, branch):
    """commit is an ancestor of origin/<branch> after a fresh fetch of that branch (the daemon's sync_source rule)"""
    git(root, "fetch", "-q", "origin", branch, check=False)
    return subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", commit, f"origin/{branch}"],
                          capture_output=True).returncode == 0


def referenced_commits(root, commit, kit):
    """grant/provenance commits a kit names: every '*source_commit' / '*grant_commit' value in the kit's JSON files
    at the spec commit, plus the die-contract slot's m6_pin_grant (ref_tile.contract_slot)"""
    found = {}

    def walk(x, where):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and k.endswith(("source_commit", "grant_commit")) and re.fullmatch(r"[0-9a-f]{7,40}", v):
                    found.setdefault(v, where + ":" + k)
                else:
                    walk(v, where)
        elif isinstance(x, list):
            for v in x:
                walk(v, where)
    for f in git(root, "ls-tree", "-r", "--name-only", commit, "--", kit).splitlines():
        if f.endswith(".json") and not f.endswith(("gate_result.json", "source_snapshot.json")):
            try:
                walk(json.loads(git(root, "show", f"{commit}:{f}")), f)
            except (SystemExit, ValueError):
                pass
    try:
        import ref_tile as RT
        spec = json.loads(git(root, "show", f"{commit}:{kit}/spec.json"))
        slot = RT.contract_slot(spec) or {}
        walk({"m6_pin_grant": slot.get("m6_pin_grant") or {}}, "die contract slot")
    except Exception:  # noqa: BLE001 -- best effort; the daemon's own check still runs below
        pass
    return found


def ff_push(root, commit, branch, dry=False):
    """HOUSEKEEPING (GATE-FRICTION 2026-10-18): push commit to origin/<branch> when that is a fast-forward (or the branch
    does not exist on origin yet).  Never forces.  Returns the text of what happened, or None when not safe."""
    exists = bool(git(root, "ls-remote", "--heads", "origin", branch, check=False))
    if exists and subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", f"origin/{branch}", commit],
                                 capture_output=True).returncode:
        return None
    if dry:
        return f"(dry run) would fast-forward push {commit[:9]} to origin/{branch}"
    p = subprocess.run(["git", "-C", str(root), "push", "-q", "origin", f"{commit}:refs/heads/{branch}"],
                       capture_output=True, text=True, timeout=600)
    if p.returncode:
        return None
    git(root, "fetch", "-q", "origin", branch, check=False)
    return f"fast-forward pushed {commit[:9]} to origin/{branch}" + ("" if exists else " (new branch)")


def origin_problems(root, commit, spec, kit, push=True, dry=False):
    out = []
    branch = (spec.get("source") or {}).get("branch")
    if not branch:
        out.append("spec source.branch missing")
    elif not on_origin(root, commit, branch):
        done = ff_push(root, commit, branch, dry) if push else None
        if done:
            print(f"HOUSEKEEPING: {done}")
        else:
            out.append(f"source commit {commit[:12]} is not on origin/{branch} and origin/{branch} is not its ancestor "
                       f"(no fast-forward possible: merge origin/{branch} first, or fix source.branch)"
                       if push else f"source commit {commit[:12]} is not on origin/{branch} (push it: drop --no-push)")
    for c, where in sorted(referenced_commits(root, commit, kit).items()) if kit else ():
        if subprocess.run(["git", "-C", str(root), "cat-file", "-e", c + "^{commit}"], capture_output=True).returncode:
            out.append(f"referenced commit {c} ({where}) does not exist")
        elif not git(root, "branch", "-r", "--contains", c, check=False):
            out.append(f"referenced commit {c} ({where}) is on no origin branch (push it)")
    return out


def binding_diff(root, kit, commit, daemon):
    """every file the committed gate result no longer binds to, with the reason (the daemon prints at most six)"""
    import hashlib
    import helper_overlay as HO
    rows = []
    try:
        d = json.loads(git(root, "show", f"{commit}:{kit}/gate_result.json"))
    except (SystemExit, ValueError):
        return ["(no committed gate_result.json at this commit: run with --regate)"]
    b = d.get("source_binding") or {}
    entries = b.get("files") or []
    used = set(((b.get("consumed") or {}).get("paths")) or [e["path"] for e in entries])
    frozen = b.get("route_overlay_plan") or {}
    gate_main = frozen.get("origin_main")
    ovl = [e["path"] for e in entries if e.get("source") == "daemon_overlay"]
    _, eff = HO.capture_plan(daemon, root, paths=[p for p in ovl if (Path(daemon) / p).is_file()])
    tree = {}
    for ln in git(root, "ls-tree", "-r", commit, "--", *sorted({e["path"] for e in entries if e.get("source") != "daemon_overlay"})).splitlines():
        meta, path = ln.split("\t", 1)
        tree[path] = meta.split()[2]
    for e in entries:
        p = e["path"]
        if e.get("source") == "daemon_overlay":
            now = hashlib.sha256(eff[p]).hexdigest() if p in eff else None
            if now != e["sha256"]:
                moved = git(root, "log", "--oneline", f"{gate_main}..origin/main", "--", p, check=False) if gate_main else ""
                rows.append(f"OVERLAY {p}: gate executed {e['git_blob'][:9]} (origin/main {str(gate_main)[:9]}), daemon now "
                            f"ships {HO.blob_id(eff[p])[:9] if p in eff else 'nothing'}"
                            + (f"; moved by: {' | '.join(moved.splitlines()[:4])}" if moved else ""))
        elif p in used and tree.get(p) != e["git_blob"]:
            rows.append(f"SOURCE  {p}: gate staged {e['git_blob'][:9]}, commit {commit[:9]} has {str(tree.get(p))[:9]}")
    return rows or ["(no per-file difference found; read the daemon message above)"]


def preflight(spec, root, daemon):
    import pre_route_gate as PRG
    PRG.DAEMON_TREE = Path(daemon)
    cfg = {}
    try:
        cfg = json.loads((STATE / "ref_gate.json").read_text())
    except (OSError, ValueError):
        pass
    if spec.get("ref_gate") is False:
        return {"verdict": "SKIP", "message": "spec ref_gate false"}
    closed = False
    c9 = str(spec["source"]["commit"])[:9]
    for f in (STATE / "jobs").glob("*.json") if spec.get("ref_tile") else []:
        try:
            t = f.read_text()
            if f'"block": "{spec["block"]}"' not in t or '"CLOSED"' not in t:
                continue
            x = json.loads(t)
        except (OSError, ValueError):
            continue
        if x.get("status") == "CLOSED" and x["spec"].get("block") == spec["block"] \
                and str((x["spec"].get("source") or {}).get("commit", ""))[:9] == c9:
            closed = True
    kw = dict(closed_stands=closed, clock_mode=str(cfg.get("clock", "refuse"))) if spec.get("ref_tile") else {}
    return PRG.submit_check(spec, str(root), **kw)


# PRE-ROUTE VISUAL REVIEW (owner via coordinator, 2026-10-17): elements on the critical list, or with >= 2 earlier
# non-CLOSED routes, need a human/agent layout review receipt bound to the kit's gate before they route.  Opt-in by list:
# every other job is unaffected.
CRITICAL_TILES = Path(os.environ.get("OT_CRITICAL_TILES", "/home/ubuntu/claude-takeover-20261007/critical_tiles.txt"))
REVIEW_FAILED_ROUTES = 2
REVIEW_CHECKLIST = ("lattice", "std_cell_band", "pin_spread", "clock_entry", "shape")
_ROUTE_FAIL = ("NEEDS_RTL", "NEEDS_HUMAN")


def critical_names():
    try:
        return {ln.split("#", 1)[0].strip() for ln in CRITICAL_TILES.read_text().splitlines()} - {""}
    except OSError:
        return set()


def failed_routes(block, jobs_dir=None):
    n = []
    for f in (jobs_dir or STATE / "jobs").glob("*.json"):
        try:
            j = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        st = str(j.get("status") or "")
        if (j.get("spec") or {}).get("block") == block and (st.startswith("EARLY_FAIL") or st in _ROUTE_FAIL):
            n.append(j.get("name"))
    return sorted(n)


def review_required(spec, kit, jobs_dir=None):
    """(why or None): critical list hit (block, kit dir or spec name prefix) or >= REVIEW_FAILED_ROUTES failed routes"""
    names, block = critical_names(), spec.get("block")
    kitname = Path(kit).name if kit else None
    # entries are element / kit PREFIXES (coordinator's list: 'ot_v41_bf_', 'qfd_c_b16', ...)
    hit = [(x, n) for x in (block, kitname, spec.get("name")) if x for n in sorted(names) if x.startswith(n)]
    if hit:
        return f"{hit[0][0]} matches '{hit[0][1]}' on {CRITICAL_TILES}"
    bad = failed_routes(block, jobs_dir)
    if len(bad) >= REVIEW_FAILED_ROUTES:
        return f"{block} has {len(bad)} earlier non-CLOSED routes ({', '.join(bad[-3:])})"
    return None


COORD_LOCK = Path(os.environ.get("OT_COORD_LOCK", "/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock"))


def reviewer_allowed(reviewer):
    """owner rule (HANDOFF 0co): the REVIEW.json reviewer is the coordinator -- the Claude coordinator when it holds
    COORDINATOR.lock ('coordinator ...'), Codex when Codex holds it ('codex ...').  ROOT and leads never self-approve.
    Returns None when allowed, else the refusal text."""
    try:
        owner = str(json.loads(COORD_LOCK.read_text()).get("owner") or "").strip().lower()
    except (OSError, ValueError):
        return f"coordinator lock {COORD_LOCK} unreadable: cannot verify the reviewer"
    r = reviewer.strip().lower()
    want = {"claude": "coordinator", "codex": "codex"}.get(owner)
    if not want:
        return f"coordinator lock owner {owner!r} unknown"
    if not r.startswith(want) or "root" in r.split():
        return (f"reviewer {reviewer!r} is not the coordinator (lock owner {owner}: reviewer must start with '{want}'); "
                "ROOT and stream leads cannot self-approve")
    return None


# GEOMETRY-BOUND REVIEW (GATE-FRICTION 2026-10-18, owner 0eg): the coordinator reviews the GEOMETRY (outline, macro
# placements, pin assignment, clock entry), so the receipt binds to a hash of exactly that, read from the kit
# (floorplan.json + spec.json + the pin / clock-entry files they name).  A re-gate with the same geometry keeps the review
# valid.  REVIEW.json "geometry_sha256" (submit_exact.py --geometry KIT prints it) is checked first; a receipt without
# it falls back to its gate_commit: valid when it names the kit's gate, or when the kit geometry at that commit equals
# the geometry now.
GEOMETRY_SCHEMA = "opentallas.ref_tile.review_geometry.v1"
_FP_OUTLINE, _FP_PINS, _FP_CLOCK = ("die", "core"), ("pins",), ("clock_port", "clock_ports", "clock_cts_roots")
_SPEC_OUTLINE, _SPEC_PINS = ("outline", "macros"), ("pins", "pin_regs", "io_flop_at_pins", "pin_reg_split")
_SPEC_CLOCK = ("clock", "clock_port", "clock_ports", "clock_entry_domains", "clock_cts_roots", "clock_relationship")


def _h(x):
    import hashlib
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def geometry_record(rd, kit, legacy=False):
    """{schema, sha256, components{outline, macros, pins, clock_entry}} of the kit geometry, rd(path) -> text or None;
    None when the kit has neither floorplan.json nor spec.json.
    ROOT 10-19 (HKV-D2D18): the pin / clock-entry files are keyed by their BASENAME (their role), not their path, which
    carries the kit name: a byte-identical layout under a new kit name (qkd_d2d_static_r7u -> r7v) hashes the same.
    legacy=True gives the pre-10-19 path-keyed hash, still accepted in REVIEW.json during the transition."""
    def js(p):
        try:
            t = rd(p)
            return json.loads(t) if t else None
        except ValueError:
            return None
    fp, sp = js(f"{kit}/floorplan.json"), js(f"{kit}/spec.json")
    if not isinstance(fp, dict) and not isinstance(sp, dict):
        return None
    fp, sp = fp if isinstance(fp, dict) else {}, sp if isinstance(sp, dict) else {}
    blocks = sorted(([b.get(k) for k in ("inst", "master", "x", "y", "w", "h", "orient")] for b in fp.get("blocks") or []
                     if isinstance(b, dict)), key=str)
    files = {}
    for ref in (sp.get("io_tcl"), f"{kit}/clock_entry.sdc", f"{kit}/io.tcl", f"{kit}/pins.tcl"):
        if isinstance(ref, str) and ref:
            for cand in (ref, f"{kit}/{ref}"):
                t = rd(cand)
                if t is not None:
                    files[ref if legacy else ref.rsplit("/", 1)[-1]] = _h(t)
                    break
    comp = dict(outline=_h([{k: fp.get(k) for k in _FP_OUTLINE}, {k: sp.get(k) for k in _SPEC_OUTLINE if k != "macros"}]),
                macros=_h([blocks, sp.get("macros")]),
                pins=_h([{k: fp.get(k) for k in _FP_PINS}, {k: sp.get(k) for k in _SPEC_PINS},
                         {k: v for k, v in files.items() if not k.endswith("clock_entry.sdc")}]),
                clock_entry=_h([{k: fp.get(k) for k in _FP_CLOCK}, {k: sp.get(k) for k in _SPEC_CLOCK},
                                {k: v for k, v in files.items() if k.endswith("clock_entry.sdc")}]))
    return dict(schema=GEOMETRY_SCHEMA, sha256=_h(comp), components=comp)


def review_check(root, commit, kit, show=None, show_at=None):
    """None when the committed REVIEW.json approves THIS gate (or this geometry), else the refusal text."""
    def at(c, p):
        if show_at:
            return show_at(c, p)
        r = subprocess.run(["git", "-C", str(root), "show", f"{c}:{p}"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None

    def rd(p):
        if show:
            return show(p)
        return at(commit, p)
    pngs = [str(root / kit / "gate_layout" / n) for n in ("floorplan.png", "density.png", "placed.png", "cts.png")
            if (root / kit / "gate_layout" / n).exists()]
    tail = " -- review these and commit physical/ref_tile/<kit>/gate_layout/REVIEW.json: " + (", ".join(pngs) or
                                                                                              f"{kit}/gate_layout/*.png")
    try:
        gate = json.loads(rd(f"{kit}/gate_result.json") or "null")
        rev = json.loads(rd(f"{kit}/gate_layout/REVIEW.json") or "null")
    except ValueError as ex:
        return f"REVIEW_REQUIRED: unreadable gate/review JSON ({ex})" + tail
    if not isinstance(rev, dict):
        return f"REVIEW_REQUIRED: no {kit}/gate_layout/REVIEW.json at {commit[:9]}" + tail
    missing = [k for k in ("reviewer", "time", "gate_commit", "verdict", "checklist") if not rev.get(k)]
    if missing:
        return f"REVIEW_REQUIRED: REVIEW.json lacks {', '.join(missing)}" + tail
    gc = str(rev["gate_commit"])
    ids = [str(x) for x in ((gate or {}).get("commit"), ((gate or {}).get("source_binding") or {}).get("commit"),
                            (gate or {}).get("generated")) if x]
    now = geometry_record(rd, kit)
    now_legacy = geometry_record(rd, kit, legacy=True)      # transition: receipts hashed with path-keyed files
    tail = (f" -- geometry_sha256 now {now['sha256']}" if now else "") + tail
    if rev.get("geometry_sha256"):
        if not now or rev["geometry_sha256"] not in (now["sha256"], (now_legacy or {}).get("sha256")):
            was = (rev.get("geometry") or {}).get("components") or {}
            moved = [k for k, v in (now or {}).get("components", {}).items() if was and was.get(k) != v]
            return (f"REVIEW_REQUIRED: the kit geometry changed since the review (geometry_sha256 "
                    f"{str(rev['geometry_sha256'])[:12]} -> {(now or {}).get('sha256', 'none')[:12]}"
                    + (f"; changed: {', '.join(moved)}" if moved else "") + ")" + tail)
    elif not ids or not any(i.startswith(gc) or gc.startswith(i) for i in ids if len(gc) >= 7 or i == gc):
        then = geometry_record(lambda p: at(gc, p), kit) if re.fullmatch(r"[0-9a-f]{7,40}", gc) else None
        if not (now and then and now["sha256"] == then["sha256"]):
            return (f"REVIEW_REQUIRED: REVIEW.json gate_commit {gc} does not match the kit's gate "
                    f"({', '.join(ids) or 'none'})" + ("" if then else " and its geometry is unreadable")
                    + ("; the geometry changed since the review" if then and now else "") + tail)
        print(f"visual review: gate re-run since review {gc}, geometry unchanged ({now['sha256'][:12]}): receipt stands")
    cl = rev["checklist"] if isinstance(rev["checklist"], dict) else {}
    absent = [k for k in REVIEW_CHECKLIST if k not in cl]
    if absent:
        return f"REVIEW_REQUIRED: checklist lacks {', '.join(absent)} (items: {', '.join(REVIEW_CHECKLIST)})" + tail
    who = reviewer_allowed(str(rev["reviewer"]))
    if who:
        return f"REVIEW_REQUIRED: {who}" + tail
    if rev["verdict"] != "APPROVED":
        return f"REVIEW_REQUIRED: reviewer {rev['reviewer']} verdict {rev['verdict']}" + tail
    return None


LINT_BENCH_RE = re.compile(r"(?:bench_)?lint(?:_.*)?", re.I)      # same as closure_loop.LINT_BENCH_RE
COMPOSITION_GATES = HERE.parent / "ref_tile" / "composition_gates.json"


def bench_evidence_problems(spec, allow_missing_witness=False):
    """(errors, warnings): the daemon's bench rule (validate + bench_gate_check) and the fail-witness rule, locally."""
    errs, warns = [], []
    st = spec.get("stages") if isinstance(spec.get("stages"), dict) else {}
    benches = [b for b in st.get("bench") or [] if isinstance(b, dict)]
    gate = spec.get("benched_by")
    if gate is not None:
        try:
            g = (json.loads(COMPOSITION_GATES.read_text()).get("gates") or {}).get(gate)
        except (OSError, ValueError):
            g = None
        if not isinstance(g, dict):
            errs.append(f"benched_by {gate!r} is not a composition gate of {COMPOSITION_GATES}")
        else:
            benches += [dict(b, name=f"{gate}_{b.get('name')}") for b in g.get("benches") or [] if isinstance(b, dict)]
    candidate = not (spec.get("auto_merge") is False or spec.get("hold_merge"))
    if candidate and not (benches or spec.get("no_bench_reason")):
        errs.append("no benches: a closure candidate needs a behavioural bench (expect pass) and a mutant (expect fail) "
                    "in stages.bench, or benched_by a composition gate (hold_merge for a job that never merges)")
    elif candidate and benches:
        if not any(b.get("expect") == "pass" and not LINT_BENCH_RE.fullmatch(str(b.get("name"))) for b in benches):
            errs.append("no behavioural expect=pass bench (lint alone is not exactness)")
        if not any(b.get("expect") == "fail" for b in benches):
            errs.append("no expect=fail mutant bench (the daemon marks the job INVALID after the gate)")
    # GATE-FRICTION 2026-10-18 (owner 0eg): a missing committed fail_witness is a WARN, not a refusal.  The loop's bench
    # track captures the real mutant output, checks the fail_regex against it and commits it with the record
    # (closure_loop.capture_fail_witness); a mutant that does not fail is still NEEDS_RTL there.  The fail_regex stays
    # required: without it a crash reads as a detected mutant and nothing can be captured.
    waiver = spec.get("fail_witness_waiver")
    waived = (isinstance(waiver, str) and waiver.strip()) or allow_missing_witness
    for b in benches:
        if b.get("expect") != "fail":
            continue
        if not b.get("fail_regex"):
            msg = (f"bench {b.get('name')}: expect=fail without fail_regex -- set it to the mutant's real verdict line "
                   f"(any rc != 0, a crash or a missing file, would read as a detected mutant)")
            (warns.append(msg + " [waived]") if waived else errs.append(msg))
        elif not b.get("fail_witness"):
            warns.append(f"bench {b.get('name')}: no committed fail_witness -- the closure loop captures the real mutant "
                         f"log, checks fail_regex against it and commits it with the record")
    return errs, warns


def drop_retired(spec):
    """RETIRED-HOST (HOSTFIX 2026-10-17): strip retired fleet hosts from hosts / host_require with a warning (an emptied
    list falls back to admission) instead of letting the daemon mark the job INVALID 'unknown host'."""
    import retired_hosts
    try:
        doc = json.loads((HERE / "hosts.json").read_text())
    except (OSError, ValueError):
        doc = {"hosts": []}
    spec, warns = retired_hosts.drop_retired_hosts(spec, {h.get("name") for h in doc.get("hosts", [])},
                                                   retired_hosts.retired_names(doc))
    for w in warns:
        print(w)
    return spec


def use_daemon_code(daemon):
    """import pre_route_gate / source_binding / helper_overlay from the DAEMON tree, not from this copy's tree.

    SUBMIT-FIX 2026-10-18: a tile worktree that synced only tools/closure_loop kept a stale tools/ref_tile, so the
    preflight ran pre-ROOT-0040 source_binding (no RELAXING_RULE_COMMITS) and refused gates the daemon accepts
    ("OVERLAY tools/textbook_lint.py ... moved by ef6a3af26").  The check must be the daemon's own code."""
    d = Path(daemon)
    for sub in ("tools/ref_tile", "tools/closure_loop"):
        if (d / sub).is_dir():
            sys.path.insert(0, str(d / sub))
    for m in ("pre_route_gate", "source_binding", "helper_overlay"):
        mod = sys.modules.get(m)
        if mod is not None and d not in Path(getattr(mod, "__file__", "/")).resolve().parents:
            del sys.modules[m]


MAIN_TOOLS_CACHE = Path(os.environ.get("OT_SUBMIT_EXACT_CACHE", str(Path.home() / ".cache/ot-submit-exact")))


def main_tools_reexec(argv):
    """HOUSEKEEPING (GATE-FRICTION 2026-10-18): run origin/main's tools/closure_loop, not this worktree's copy.  When any
    file of this copy differs from origin/main's, extract main's tools/closure_loop (+ composition_gates.json) once per
    main commit into MAIN_TOOLS_CACHE and re-exec it with the same argv.  Returns the exit code, or None to go on here
    (already main's code, OT_SUBMIT_EXACT_MAIN set, or git unavailable)."""
    import hashlib
    if os.environ.get("OT_SUBMIT_EXACT_MAIN") or "--local-tools" in (argv or sys.argv[1:]):
        return None
    try:
        root = git(Path.cwd(), "rev-parse", "--show-toplevel")
        git(root, "fetch", "-q", "origin", "main", check=False)
        head = git(root, "rev-parse", "origin/main")
        rows = [ln.split(None, 3) for ln in git(root, "ls-tree", "origin/main", "tools/closure_loop/").splitlines()]
    except SystemExit:
        return None
    stale = []
    for mode, kind, blob, path in rows:
        f = HERE / Path(path).name
        if kind != "blob":
            continue
        data = f.read_bytes() if f.is_file() else None
        if data is None or hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() != blob:
            stale.append(Path(path).name)
    if not stale:
        return None
    dest = MAIN_TOOLS_CACHE / head[:12]
    if not (dest / "tools/closure_loop/submit_exact.py").is_file():
        tmp = MAIN_TOOLS_CACHE / f".{head[:12]}.{os.getpid()}"
        tmp.mkdir(parents=True, exist_ok=True)
        a = subprocess.run(f"git -C {shlex.quote(root)} archive origin/main tools/closure_loop "
                           f"tools/ref_tile/composition_gates.json | tar -x -C {shlex.quote(str(tmp))}",
                           shell=True, capture_output=True, text=True, timeout=600)
        if a.returncode or not (tmp / "tools/closure_loop/submit_exact.py").is_file():
            print(f"submit_exact: WARN could not extract origin/main tools ({a.stderr.strip()[:200]}); using this copy")
            return None
        try:
            os.replace(tmp, dest)
        except OSError:
            subprocess.run(["rm", "-rf", str(tmp)])
    print(f"HOUSEKEEPING: this copy of tools/closure_loop differs from origin/main {head[:9]} "
          f"({', '.join(stale[:4])}{' ...' if len(stale) > 4 else ''}); running main's submit_exact", flush=True)
    env = dict(os.environ, OT_SUBMIT_EXACT_MAIN=head)
    return subprocess.run([sys.executable, str(dest / "tools/closure_loop/submit_exact.py"), *(argv or sys.argv[1:])],
                          env=env).returncode


def main(argv=None):
    rc = main_tools_reexec(argv)
    if rc is not None:
        return rc
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--commit-paths", nargs="+", help="commit exactly these paths first (git add -- <paths>)")
    ap.add_argument("-m", "--message", help="commit message for --commit-paths / the gate-result commit")
    ap.add_argument("--follow-head", action="store_true", help="move the spec to HEAD (name suffix too) before checking")
    ap.add_argument("--regate", action="store_true", help="on a source_binding refusal run the gate on the exact commit")
    ap.add_argument("--gate-args", default="--remote auto --cts --mem 24")
    ap.add_argument("--no-push", dest="push", action="store_false",
                    help="do not push HEAD to origin/<source.branch> (default: push after every commit, before the gate)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-missing-witness", action="store_true",
                    help="expect=fail benches without fail_regex WARN instead of refusing (a missing fail_witness always only WARNs)")
    ap.add_argument("--local-tools", action="store_true",
                    help="run this copy of tools/closure_loop even when it differs from origin/main (default: re-exec main's)")
    ap.add_argument("--geometry", action="store_true",
                    help="print the review geometry record (geometry_sha256 for REVIEW.json) of the spec's kit at HEAD; "
                         "SPEC may also be the kit directory")
    ap.add_argument("--daemon-tree", default=os.environ.get("OT_CLOSURE_DAEMON_TREE", "/home/ubuntu/wt-claude-closure-daemon-1010"))
    a = ap.parse_args(argv)
    use_daemon_code(a.daemon_tree)
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel"))
    if a.geometry:
        kp = Path(a.spec)
        kit = (str(kp.resolve().relative_to(root)) if kp.is_dir() else kit_of(json.loads(kp.read_text())))
        rec = geometry_record(lambda p: (root / p).read_text() if (root / p).is_file() else None, kit)
        print(json.dumps(dict(kit=kit, geometry_sha256=(rec or {}).get("sha256"), geometry=rec), indent=1))
        return 0 if rec else 2
    spec_path = Path(a.spec)
    spec = json.loads(spec_path.read_text())
    if a.commit_paths:
        if not a.message:
            raise SystemExit("submit_exact: --commit-paths needs -m")
        git(root, "add", "--", *a.commit_paths)
        if git(root, "diff", "--cached", "--name-only"):
            git(root, "commit", "-m", a.message, "--", *a.commit_paths)
        a.follow_head = True
    if a.follow_head:
        spec = move_spec(spec, git(root, "rev-parse", "HEAD"))
    spec = drop_retired(spec)

    def push():
        br = (spec.get("source") or {}).get("branch")
        if a.push and br:
            git(root, "push", "-q", "origin", f"HEAD:refs/heads/{br}")
    if a.commit_paths:
        push()
    # the daemon refuses these as INVALID after the gate (b2 upper x2, xcal216 10-16): same check + message, locally first
    # HERE is already on sys.path (module top); re-inserting it at 0 would shadow the daemon tree (use_daemon_code)
    import bench_count
    st = spec.get("stages") if isinstance(spec.get("stages"), dict) else {}
    ev_err, ev_warn = bench_evidence_problems(spec, a.allow_missing_witness)
    for w in ev_warn:
        print(f"BENCH-EVIDENCE WARN: {w}")
    if ev_err:
        print("REFUSED LOCALLY (BENCH-EVIDENCE: benches / fail witnesses missing): " + "; ".join(ev_err))
        return 1
    mcr_bad = bench_count.count_regex_errors(st.get("bench", []))
    if mcr_bad:
        print("REFUSED LOCALLY (INVALID spec, the daemon would reject it): " + "; ".join(mcr_bad))
        return 1
    git(root, "fetch", "-q", "origin", "main", check=False)
    # BENCH-LINT (ROOT 2026-10-16): git in benches (non-git export), unverified/unmatched fail_regex -- before the gate
    bcommit = (spec.get("source") or {}).get("commit", "")

    def bshow(p):
        r = subprocess.run(["git", "-C", str(root), "show", f"{bcommit}:{p}"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None
    blint_err, blint_warn = bench_count.bench_lint(st.get("bench", []), bshow if bcommit else None)
    for w in blint_warn:
        print(f"BENCH-LINT WARN: {w}")
    if blint_err:
        print("REFUSED LOCALLY (BENCH-LINT, the daemon would refuse it at intake): " + "; ".join(blint_err))
        return 1
    for attempt in (1, 2):
        commit = git(root, "rev-parse", f"{spec['source']['commit']}^{{commit}}")
        paths = consumed_paths(spec)
        unc, diff = dirty(root, commit, paths)
        # HOUSEKEEPING (GATE-FRICTION 2026-10-18): generated gate files (gate_result.json of a PASS/WARN gate,
        # source_binding_history/, gate_layout/) are committed by path and the spec follows HEAD, instead of refusing
        if unc and generated_only(unc) and all(gate_file_ok(root, u) for u in unc) and not a.dry_run:
            gen = sorted({str(Path(u)) for u in unc})
            git(root, "add", "--", *gen)
            if git(root, "diff", "--cached", "--name-only", "--", *gen):
                git(root, "commit", "-m", a.message or f"{kit_of(spec)}: generated gate files (submit_exact housekeeping)",
                    "--", *gen)
                print(f"HOUSEKEEPING: committed generated gate files {', '.join(gen[:6])}")
            spec = move_spec(spec, git(root, "rev-parse", "HEAD"))
            push()
            commit = git(root, "rev-parse", f"{spec['source']['commit']}^{{commit}}")
            unc, diff = dirty(root, commit, paths)
        elif unc and generated_only(unc) and a.dry_run:
            print("HOUSEKEEPING (dry run): would commit generated gate files " + ", ".join(unc[:6]))
            unc = []
        if diff and not unc and generated_only(diff):
            print(f"HOUSEKEEPING: HEAD differs from the spec commit only in generated gate files; spec follows HEAD")
            spec = move_spec(spec, git(root, "rev-parse", "HEAD"))
            commit = git(root, "rev-parse", f"{spec['source']['commit']}^{{commit}}")
            unc, diff = dirty(root, commit, paths)
        if unc or diff:
            print("REFUSED LOCALLY (SUBMIT ORDER): consumed paths are not exactly the spec commit "
                  f"{commit[:9]} -- commit first, then gate on that commit:")
            for x in unc:
                print(f"  uncommitted {x}")
            for x in diff:
                print(f"  HEAD differs from spec commit: {x}")
            return 1
        bad = origin_problems(root, commit, spec, kit_of(spec), push=a.push, dry=a.dry_run)
        if bad:
            print("REFUSED LOCALLY (not on origin): " + "; ".join(bad))
            return 1
        res = preflight(spec, root, a.daemon_tree)
        v, msg = res.get("verdict"), res.get("message", "")
        print(f"daemon submit check at {commit[:9]}: {v}: {msg[:1500]}")
        rr = res.get("relaxing_rule_allowlist")
        if isinstance(rr, dict):
            print("RELAXING-RULE ALLOWLIST used (recorded in the job at intake): commits "
                  + ", ".join(c[:9] for c in rr.get("commits") or []) + "; "
                  + "; ".join(x.get("text", "") for x in rr.get("requirements") or []))
        if v != "REFUSE":
            break
        kit = kit_of(spec)
        if "source_binding" in msg and kit:
            print("exact gate-binding differences:")
            for r in binding_diff(root, kit, commit, a.daemon_tree):
                print("  " + r)
        if not (a.regate and kit and "source_binding" in msg and attempt == 1):
            print("REFUSED LOCALLY: nothing was submitted" + ("" if a.regate else " (re-gate: add --regate)"))
            return 1
        cmd = [sys.executable, str(root / "tools/ref_tile/pre_route_gate.py"), kit, "--commit", commit,
               *shlex.split(a.gate_args)]
        print("re-gate on the exact commit: " + " ".join(cmd), flush=True)
        if subprocess.run(cmd, cwd=root).returncode:
            print("REFUSED LOCALLY: the gate failed; nothing was submitted")
            return 1
        out = [p for p in (f"{kit}/gate_result.json", f"{kit}/source_binding_history") if (root / p).exists()]
        git(root, "add", "--", *out)
        git(root, "commit", "-m", a.message or f"{kit}: gate result on {commit[:9]} (submit_exact)", "--", *out)
        spec = move_spec(spec, git(root, "rev-parse", "HEAD"))
        push()
    kit = kit_of(spec)
    why = review_required(spec, kit) if kit else None
    if why:
        rr = review_check(root, git(root, "rev-parse", f"{spec['source']['commit']}^{{commit}}"), kit)
        if rr:
            print(f"REFUSED LOCALLY ({why}): {rr}")
            return 1
        print(f"visual review receipt OK ({why})")
    if a.dry_run:
        print(f"DRY RUN: would submit {spec['name']} at {spec['source']['commit']}")
        return 0
    DROP.mkdir(parents=True, exist_ok=True)
    tmp = DROP / f".{spec['name']}.json.tmp"
    tmp.write_text(json.dumps(spec, indent=1) + "\n")
    os.replace(tmp, DROP / f"{spec['name']}.json")
    if spec != json.loads(spec_path.read_text()):
        if root in spec_path.resolve().parents:
            print(f"note: the submitted spec moved to {spec['source']['commit']}; {spec_path} (in the worktree) left as is")
        else:
            spec_path.write_text(json.dumps(spec, indent=1) + "\n")
    print(f"SUBMITTED {spec['name']} (source {spec['source']['commit']}) -> {DROP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
