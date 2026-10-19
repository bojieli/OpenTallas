"""Content binding for the exact effective gate archive (including daemon overlays).

A commit is provenance only unless every shipped file matches it. Qualification
uses the immutable manifest, never a HEAD observed after the remote run.
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import posixpath
import re
import subprocess
import tarfile
from pathlib import Path

SCHEMA = "opentallas.ref_tile.source_snapshot.v1"
EXCLUDED = {"gate_result.json", "source_snapshot.json"}
CONSUMED_SCHEMA = "opentallas.ref_tile.gate_consumed.v1"
# working-tree tools the remote gate script runs itself (REMOTE_SH), besides the daemon overlays (SHIP_HELPERS)
GATE_TOOLS = ("tools/ref_tile/ref_route.sh", "tools/textbook_lint.py", "tools/closure_loop/ck_insertion.py",
              "tools/ref_tile/path_classes.tcl", "tools/ref_tile/keep_module_audit.py")
# Non-Python source read by an imported generator and embedded in its kit.
PY_DATA = {"tools/ref_tile/direct_macro_clock_entries.py": ("tools/ref_tile/sta_scene_binding.cc",)}
PY_DIRS = ("tools", "tools/ref_tile", "tools/closure_loop", "tools/w18")
SCAN = (".tcl", ".sdc", ".sh", ".env", ".mk", ".cfg", ".f")    # flow scripts: every repo path they name is consumed
HDL = (".v", ".sv", ".svh", ".vh")
INCLUDE_RE = re.compile(r'^\s*`include\s+"([^"]+)"', re.M)


def git_head(repo):
    p = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def git_files(repo, commit):
    if not commit:
        return {}
    p = subprocess.run(["git", "-C", str(repo), "ls-tree", "-rz", commit], capture_output=True)
    if p.returncode:
        return {}
    return {path.decode(): meta.decode().split()[2] for row in p.stdout.split(b"\0") if row
            for meta, path in [row.split(b"\t", 1)]}


def blob_hash(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical_digest(entries):
    return hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def overlay_module():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "closure_loop"))
    import helper_overlay
    return helper_overlay


def snapshot(data, root, start_commit, daemon, daemon_commit, helpers):
    """Read the completed bytes, resolving duplicate tar members as extraction does."""
    current, overlays = git_files(root, start_commit), git_files(daemon, daemon_commit)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        for m in tf:
            if not (m.isfile() or m.issym()):
                if m.islnk():
                    raise ValueError("hard links are unsupported in gate source snapshots")
                continue
            payload = m.linkname.encode() if m.issym() else tf.extractfile(m).read()
            source = "daemon_overlay" if m.name in helpers and (daemon / m.name).exists() else "working_tree"
            expected = (overlays if source == "daemon_overlay" else current).get(m.name)
            files[m.name] = {"path": m.name, "kind": "symlink" if m.issym() else "file",
                             "sha256": hashlib.sha256(payload).hexdigest(), "git_blob": blob_hash(payload),
                             "source": source, "matches_provenance_commit": expected == blob_hash(payload)}
    entries = [files[k] for k in sorted(files)]
    clean = all(e["matches_provenance_commit"] and current.get(e["path"]) == e["git_blob"] for e in entries)
    return {"schema": SCHEMA, "start_commit": start_commit, "commit": start_commit if clean else None,
            "identity": "commit" if clean else "exact_content_snapshot", "daemon_tree": str(daemon),
            "daemon_start_commit": daemon_commit, "daemon_overlays": sorted(set(helpers) & files.keys()),
            "archive_sha256": hashlib.sha256(data).hexdigest(), "manifest_sha256": canonical_digest(entries),
            "files": entries}


def archive_contents(data):
    """{path: bytes} of the regular files of a gate archive, last member winning as extraction does."""
    out = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        for m in tf:
            if m.isfile():
                out[m.name] = tf.extractfile(m).read()
    return out


def _py_imports(path, text, files):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        names = [(m, 0) for m in re.findall(r"^\s*(?:from|import)\s+([\w.]+)", text, re.M)]
    else:
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [(a.name, 0) for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                names.append((base, node.level))
                names += [((base + "." if base else "") + a.name, node.level) for a in node.names]
    here = posixpath.dirname(path)
    found = set()
    for mod, level in names:
        if not mod:
            continue
        rel = mod.replace(".", "/")
        if level:
            up = here
            for _ in range(level - 1):
                up = posixpath.dirname(up)
            roots = [up]
        else:
            roots = [here, *PY_DIRS]
        for r in roots:
            for c in (f"{r}/{rel}.py", f"{r}/{rel}/__init__.py"):
                if c in files:
                    found.add(c)
    return found


def consumed_closure(files, seeds, prefixes, path_re):
    """Every staged path the gate consumes: the seeds (kit files, RTL file list, hooks, SDCs, pin files, gate-run tools
    and overlays) closed over the repo paths their text names (path_re), Python imports and Verilog `include, plus every
    staged file under the prefixes (child/macro view directories, the job's extra_paths).  files: {path: bytes} of the
    staged archive.  Kit JSON is not scanned (its inputs are the seeds: spec sources, floorplan referenced); flow
    scripts are scanned conservatively (any path they name outside a comment is consumed); a Python tool consumes the
    modules it imports."""
    pre = [q.rstrip("/") for q in prefixes if q]
    out = {p for p in files for q in pre if p == q or p.startswith(q + "/")}
    # (path, named): named = reached as a seed or named by a flow script, i.e. executed/read by the flow; a module
    # reached only by import is not scanned for path strings (they are its options, not this gate's inputs)
    todo = [(q, True) for q in list(seeds) + sorted(out)]
    scanned = set()
    while todo:
        raw, named = todo.pop()
        p = posixpath.normpath(raw[5:] if raw.startswith("/src/") else raw)
        if (p, named) in scanned or (p, True) in scanned or p not in files:
            continue
        scanned.add((p, named))
        out.add(p)
        if not p.endswith(SCAN + HDL + (".py",)):
            continue
        text = files[p].decode(errors="replace")
        if p.endswith(SCAN) or (p.endswith(".py") and named):
            body = re.sub(r"(?m)^\s*#.*$", "", text)     # comments name paths they do not use
            todo += [(m.group(1), True) for m in path_re.finditer(body) if "$" not in m.group(1)
                     and (not p.endswith(".py") or m.group(1).endswith((".tcl", ".sdc", ".sh", ".env")))]
        if p.endswith(".py"):
            todo += [(q, False) for q in sorted(_py_imports(p, text, files))]
            todo += [(q, True) for q in PY_DATA.get(p, ())]
        if p.endswith(".f"):
            todo += [(ln.strip(), True) for ln in text.splitlines()
                     if ln.strip() and not ln.lstrip().startswith(("-", "/", "#"))]
        if p.endswith(HDL):
            for inc in INCLUDE_RE.findall(text):
                local = posixpath.normpath(posixpath.join(posixpath.dirname(p), inc))
                todo += [(q, True) for q in ([local] if local in files else
                                             [f for f in files if f.endswith("/" + inc.lstrip("./"))])]
    return out


def consumed_record(paths, entries, basis):
    staged = {e["path"] for e in entries}
    paths = sorted(set(paths) & staged)
    return {"schema": CONSUMED_SCHEMA, "basis": basis, "count": len(paths), "paths": paths,
            "sha256": {e["path"]: e["sha256"] for e in entries if e["path"] in set(paths)},
            "digest": canonical_digest(paths)}


def validate(binding, root, daemon, commit=None, route_overlay=True, frozen_recovery=False, clock=None, tile=None,
             gate=None):
    """Match immutable staged contents against the requested route source and current tool overlay.

    clock: the gate result's "clock" record.  With it, drift made only by RELAXING-ONLY rule commits
    (helper_overlay.RELAXING_RULE_COMMITS) is tolerated when the gate report meets the relaxed rule's requirement; the
    use is recorded in binding["relaxing_rule_allowlist"] (the caller copies it into the job).
    GATE-FRICTION 2026-10-18: every commit on the chain is classified (helper_overlay.rule_span: relaxing / neutral /
    tightening / unclassified); only a tightening that applies to `tile` (kit / top / block names), or an unclassified
    change, keeps the strict refusal.
    gate: the whole gate result (gate_result.json), for requirements judged from more than its clock record
    (trial_grt: the every-kit trial global route)."""
    if not isinstance(binding, dict) or binding.get("schema") != SCHEMA:
        return False, "missing immutable source snapshot; legacy result is unqualified"
    if frozen_recovery and not route_overlay:
        return False, "frozen helper recovery requires executed overlay verification"
    entries = binding.get("files")
    if not entries or canonical_digest(entries) != binding.get("manifest_sha256"):
        return False, "source manifest missing or digest mismatch"
    tree = git_files(root, commit) if commit else None
    effective = {}
    if route_overlay:
        HO = overlay_module()
        frozen = binding.get("route_overlay_plan")
        paths = None if frozen else [e["path"] for e in entries if e["source"] == "daemon_overlay"]
        try:
            if frozen_recovery:
                receipt = binding.get("helper_recovery") or {}
                executed = sorted(e["path"] for e in entries if e["source"] == "daemon_overlay")
                if ((binding.get("recovery") or {}).get("kind") != "full_original_snapshot_verified"
                        or not executed
                        or not binding.get("remote_archive_verified")
                        or receipt.get("status") != "verified_original_gate"
                        or receipt.get("content_sha256") != (frozen or {}).get("content_sha256")
                        or receipt.get("origin_main") != (frozen or {}).get("origin_main")
                        or receipt.get("executed_paths") != executed
                        or receipt.get("manifest_sha256") != binding["manifest_sha256"]):
                    return False, "original gate executed-helper verification missing or mismatched"
                effective = HO.committed_frozen_payloads(root, frozen)
            else:
                current, effective = HO.capture_plan(daemon, root, paths=paths)
        except (OSError, ValueError, subprocess.SubprocessError) as ex:
            return False, f"cannot resolve effective route helpers: {ex}"
        if frozen and not frozen_recovery:
            # Precise binding (2026-10-14): the gate is bound to what it EXECUTED -- the staged working-tree files
            # (checked against the route source commit below) and the daemon overlays it shipped (entries with
            # source "daemon_overlay", checked against today's effective bytes below).  The frozen route plan's other
            # helpers are route-only: their drift is reported, never a reason to invalidate the gate.  The frozen plan
            # itself must still be intact and agree with what the gate shipped.
            try:
                rows = {r["path"]: r for r in HO.frozen_rows(frozen)}
            except ValueError as ex:
                return False, str(ex)
            for e in entries:
                if e["source"] == "daemon_overlay" and e["path"] in rows and rows[e["path"]]["sha256"] != e["sha256"]:
                    return False, f"frozen route plan disagrees with the gate's staged overlay: {e['path']}"
    overlay_diff, source_diff, missing = [], [], []
    for e in entries:
        p = Path(e["path"])
        if p.is_absolute() or ".." in p.parts:
            return False, "unsafe manifest path"
        if e["source"] == "daemon_overlay" and route_overlay:
            if str(p) not in effective or hashlib.sha256(effective[str(p)]).hexdigest() != e["sha256"]:
                overlay_diff.append(str(p))
            continue
        if e["source"] == "daemon_overlay":
            f = daemon / p
        elif tree is not None:
            if tree.get(str(p)) != e["git_blob"]:
                source_diff.append(str(p))
            continue
        else:
            f = root / p
        try:
            payload = str(f.readlink()).encode() if e["kind"] == "symlink" else f.read_bytes()
        except OSError:
            missing.append(str(p))
            continue
        if hashlib.sha256(payload).hexdigest() != e["sha256"]:
            (overlay_diff if e["source"] == "daemon_overlay" else source_diff).append(str(p))
    def name(files):
        return ", ".join(files[:6]) + (f" (+{len(files) - 6} more)" if len(files) > 6 else "")
    unconsumed = []
    consumed = binding.get("consumed")
    if consumed is not None:
        # Precise source binding (r2, 2026-10-14): a gate carrying its consumed-file record is bound only to the files it
        # actually used (kit, RTL file list closure, hooks, SDCs, pin files, extra_paths, gate-run tools + overlays);
        # differences elsewhere in the staged snapshot (another job's spec, unrelated RTL) are reported, not refused.
        if (not isinstance(consumed, dict) or consumed.get("schema") != CONSUMED_SCHEMA
                or canonical_digest(consumed.get("paths") or []) != consumed.get("digest")):
            return False, "gate consumed-file record missing or digest mismatch"
        staged = {e["path"]: e["sha256"] for e in entries}
        used = set(consumed["paths"])
        if not used or any(staged.get(q) != h for q, h in (consumed.get("sha256") or {}).items()) or used - staged.keys():
            return False, "gate consumed-file record disagrees with the staged manifest"
        unconsumed = sorted(q for q in source_diff + missing if q not in used)
        source_diff = [q for q in source_diff if q in used]
        missing = [q for q in missing if q in used]
    # LINT-TOLERANT (ROOT 2026-10-16, coordinator): a gate stays valid across a tools/textbook_lint.py change from one main
    # revision to a later one when the change touches only comments/docstrings or SUBMIT-ONLY constants (CLOSED-STANDS
    # kinds/text; helper_overlay.lint_change_is_submit_only): the gate's own checks are unchanged.  Reported, not refused.
    lint_ok = []
    try:
        HO_ = overlay_module()
        head = HO_.main_head(root)
        by = {e["path"]: e for e in entries}
        for q in [q for q in overlay_diff + source_diff if q in getattr(HO_, "LINT_ONLY", ())]:
            blob = by.get(q, {}).get("git_blob")
            if not head or blob not in HO_._main_blobs(root, head, q):
                continue
            old = subprocess.run(["git", "-C", str(root), "cat-file", "blob", blob], capture_output=True, timeout=60)
            cur = effective.get(q) if q in effective else (daemon / q if q in overlay_diff else root / q).read_bytes()
            if not old.returncode and HO_.lint_change_is_submit_only(old.stdout, cur):
                lint_ok.append(q)
    except Exception:  # noqa: BLE001 -- unresolvable: keep the strict verdict
        lint_ok = []
    overlay_diff = [q for q in overlay_diff if q not in lint_ok]
    source_diff = [q for q in source_diff if q not in lint_ok]
    # BENCH-ONLY KIT SPEC EDIT (ROOT-0040 2026-10-18): a kit spec.json / job.json that changed since the gate only in its
    # bench list (stages.bench / job.benches) (a mutant dropped or added) leaves the pre-route gate's inputs unchanged: the gate never runs
    # benches (submit_exact BENCH-EVIDENCE and the route's bench stage judge them).  Reported, not refused.
    bench_ok = []
    try:
        by_ = {e["path"]: e for e in entries}
        for q in [q for q in source_diff if q.startswith("physical/ref_tile/") and q.endswith(("/spec.json", "/job.json"))]:
            new_ = (subprocess.run(["git", "-C", str(root), "cat-file", "blob", tree[q]], capture_output=True,
                                   timeout=60).stdout if tree is not None and tree.get(q) else
                    None if tree is not None else (root / q).read_bytes())
            old_ = subprocess.run(["git", "-C", str(root), "cat-file", "blob", by_[q]["git_blob"]], capture_output=True,
                                  timeout=60)
            if new_ and not old_.returncode and spec_change_is_bench_only(old_.stdout, new_):
                bench_ok.append(q)
    except Exception:  # noqa: BLE001 -- unresolvable: keep the strict verdict
        bench_ok = []
    source_diff = [q for q in source_diff if q not in bench_ok]
    # RELAXING-ONLY RULE ALLOWLIST (ROOT-0040 2026-10-18, owner 10-17 "rules must never delay closure"): a file whose
    # every change since the gate's version is an allowlisted relaxing rule commit (0dq: clock FAIL -> WARN) keeps the
    # gate valid, provided the existing gate report meets the relaxed rule (pin-flop spread <= 80 ps at TT; FF when
    # reported, else left to the routed audit).  Without the gate's clock record the strict verdict stands.
    relaxed, relax_why = [], None
    # rule classification applies to tool / flow files only (a kit or RTL edit is a design change: re-gate)
    rule_files = [q for q in overlay_diff + source_diff
                  if q in overlay_diff or q.startswith(("tools/", "physical/common_flow/"))]
    if rule_files and len(rule_files) == len(overlay_diff) + len(source_diff) and not missing and not frozen_recovery:
        try:
            HO_ = overlay_module()
            heads = [HO_.main_head(root), commit]
            by = {e["path"]: e for e in entries}
            rows = []
            for q in rule_files:
                if q in overlay_diff and route_overlay:
                    now = HO_.blob_id(effective[q]) if q in effective else None
                elif q in overlay_diff:
                    now = blob_hash((daemon / q).read_bytes())
                elif tree is not None:
                    now = tree.get(q)
                else:
                    now = blob_hash((root / q).read_bytes())
                if hasattr(HO_, "rule_span"):
                    ok_, crow, why_ = HO_.rule_span(root, q, by[q]["git_blob"], now, heads, tile=tile)
                else:                                                   # pre-GATE-FRICTION daemon helper_overlay
                    ok_, chain = HO_.relaxing_only_span(root, q, by[q]["git_blob"], now, heads)
                    crow = [dict(commit=c, kind="relaxing", **HO_.RELAXING_RULE_COMMITS.get(c, {})) for c in chain]
                    why_ = f"{q}: commit {chain[-1][:9]} is not a relaxing-only rule change" if chain else None
                if not ok_:
                    rows = None
                    relax_why = why_
                    break
                rows.append(dict(path=q, gate_git_blob=by[q]["git_blob"], current_git_blob=now,
                                 commits=[r["commit"] for r in crow],
                                 classes=[dict(commit=r["commit"], kind=r["kind"], source=r.get("source"),
                                               rule=r.get("rule"), requires=r.get("requires"), applies=r.get("applies"))
                                          for r in crow],
                                 rules=sorted({str(r.get("rule")) for r in crow if r.get("rule")}),
                                 needs=sorted({r["requires"] for r in crow if r.get("requires")
                                               and (r["kind"] == "relaxing" or r.get("applies"))})))
            if rows:
                needs = sorted({n for r in rows for n in r.pop("needs")})
                req_ok, req = relaxed_rule_requirement(needs, clock, gate, root=root)
                if req_ok:
                    relaxed = rows
                    binding["relaxing_rule_allowlist"] = dict(
                        schema="opentallas.ref_tile.relaxing_rule_allowlist.v1", files=rows, requirements=req,
                        commits=sorted({c for r in rows for c in r["commits"]}), origin_main=heads[0])
                else:
                    relax_why = "relaxing-rule allowlist not applicable: " + "; ".join(
                        x["text"] for x in req if not x["ok"])
        except Exception as ex:  # noqa: BLE001 -- unresolvable: keep the strict verdict
            relaxed, relax_why = [], f"relaxing-rule allowlist unresolvable: {type(ex).__name__}: {ex}"[:200]
    relaxed_paths = {r["path"] for r in relaxed}
    overlay_diff = [q for q in overlay_diff if q not in relaxed_paths]
    source_diff = [q for q in source_diff if q not in relaxed_paths]
    if overlay_diff or source_diff or missing:
        parts = ([f"gate-executed daemon overlay changed: {name(overlay_diff)}"] if overlay_diff else []) + \
                ([f"route source differs from staged snapshot: {name(source_diff)}"] if source_diff else []) + \
                ([f"staged source missing: {name(missing)}"] if missing else [])
        return False, "; ".join(parts) + (f" (gate-consumed; {len(unconsumed)} unconsumed difference(s) not counted)"
                                          if unconsumed else "") + (f" [{relax_why}]" if relax_why else "")
    notes = [f"{len(unconsumed)} staged file(s) the gate did not consume differ (reported, not refused): {name(unconsumed)}"] \
        if unconsumed else []
    if lint_ok:
        notes.append(f"lint-only drift tolerated (earlier main revision): {name(lint_ok)}")
    if bench_ok:
        notes.append(f"bench-only kit spec edit tolerated (bench list): {name(bench_ok)}")
    if relaxed:
        rec = binding["relaxing_rule_allowlist"]
        notes.append("RELAXING-RULE ALLOWLIST used: " + ", ".join(
            f"{r['path']} {r['gate_git_blob'][:9]}->{str(r['current_git_blob'])[:9]} via "
            + "+".join(c[:9] for c in r["commits"]) + (f" ({'/'.join(r['rules'])})" if r["rules"] else "")
            for r in relaxed) + "; " + "; ".join(x["text"] for x in rec["requirements"]))
    if route_overlay and not frozen_recovery and binding.get("route_overlay_plan"):
        drift = route_only_drift(binding["route_overlay_plan"], current, entries)
        if drift:
            notes.append("route-only helper drift (not gate-relevant): " + ", ".join(drift))
    head = ("exact original source and committed executed helpers match; current helpers unchanged" if frozen_recovery
            else "gate-consumed source and gate-executed overlays match" if consumed is not None
            else "exact staged source and gate-executed overlays match" if notes else "exact staged source and daemon overlay match")
    return True, "; ".join([head] + notes)


def spec_change_is_bench_only(old, new):
    """True when two kit spec.json / job.json versions differ only in their bench lists: job.json stages.bench
    (also under "spec"), kit spec.json job.benches."""
    def norm(data):
        d = json.loads(data)
        for x in (d, d.get("spec") if isinstance(d, dict) else None):
            if isinstance(x, dict) and isinstance(x.get("stages"), dict):
                x["stages"].pop("bench", None)
        if isinstance(d, dict) and isinstance(d.get("job"), dict):
            d["job"].pop("benches", None)
        return d
    try:
        return norm(old) == norm(new)
    except (ValueError, TypeError, AttributeError):
        return False


CLOCK_PIN_SPREAD_MAX_PS = 80.0     # textbook_lint.CLK_SPREAD_MAX_PS (owner 10-17 0dq)


def gate_pin_spreads(clock):
    """{corner: (spread_ps, basis)} from a gate clock record: "<c>_pin_spread_ps" when recorded, else the boundary
    (pin-flop) min..max of every measured domain that reports one (pre-0dq records), else the all-register leaf
    spread "<c>_spread_ps" (conservative)."""
    out = {}
    doms = [d for d in (clock or {}).get("clock_measurements") or [] if isinstance(d, dict)]
    for c in ("tt", "ff"):
        v = (clock or {}).get(f"{c}_pin_spread_ps")
        if isinstance(v, (int, float)):
            out[c] = (float(v), "pin-flop")
            continue
        bds = [((d.get(c) or {}).get("boundary") or {}) for d in doms]
        bds = [b for b in bds if b.get("min") is not None and b.get("max") is not None]
        if bds:
            out[c] = (round(max(float(b["max"]) - float(b["min"]) for b in bds), 1), "pin-flop")
        elif isinstance((clock or {}).get(f"{c}_spread_ps"), (int, float)):
            out[c] = (float(clock[f"{c}_spread_ps"]), "leaf")
    return out


def child_flop_reference_macros(root, kit):
    """ROOT-0615 10-18 (dcd8111e5): the kit's macro views that give ck_insertion a CHILD-FLOP reference R (a views
    insertion.json beside the lib, or a lib with max_clock_tree_path).  None when the kit.env cannot be read."""
    import shlex
    env = Path(root) / "physical" / "ref_tile" / str(kit) / "kit.env"
    try:
        text = env.read_text()
    except OSError:
        return None
    m = re.search(r"^MACROS=\((.*)\)\s*$", text, re.M)
    out = []
    for stem in shlex.split(m.group(1)) if m else []:
        p = Path(root) / stem
        libs = [p.parent / f"{p.name}_{c}.lib" for c in ("tt", "ff")]
        if (p.parent / "insertion.json").is_file() or any(
                lib.is_file() and "max_clock_tree_path" in lib.read_text(errors="replace") for lib in libs):
            out.append(stem)
    return out


def relaxed_rule_requirement(needs, clock, gate=None, root=None):
    """(ok, [{"requires", "ok", "text", ...}]): the relaxed rules' own conditions, judged from the existing gate report.
    clock_pin_spread (0dq): pin-flop spread <= 80 ps at TT (required); FF too when reported, else left to the routed
    native audit.
    trial_grt (ROOT-0330-GRT 10-18, the gate runs a trial global route for EVERY kit): a gate result without a
    "trial_route" record predates the rule and stays valid (its verdict already holds the parent / cluster trial, which
    is unchanged); a gate that ran it must show overflow 0.  Without the gate result the strict refusal stands."""
    rows = []
    for n in needs:
        if n == "trial_grt":
            tr = gate.get("trial_route") if isinstance(gate, dict) else None
            if not isinstance(gate, dict):
                rows.append(dict(requires=n, ok=False, text="trial_grt: no gate result to judge"))
            elif tr is None:
                rows.append(dict(requires=n, ok=True, predates=True,
                                 text="trial_grt: gate predates the every-kit trial GRT (no trial_route record): kept"))
            else:
                ovf = tr.get("overflow") if isinstance(tr, dict) else None
                rows.append(dict(requires=n, ok=ovf == 0, overflow=ovf,
                                 text=f"trial_grt: gate trial GRT overflow {ovf}" + ("" if ovf == 0 else " (FAIL)")))
            continue
        if n == "reset_landing":
            # ROOT-RST 10-19: the gate FAILS a reset input reaching > rst_land_max sinks without a landing register.  A
            # gate result without a "reset_landing" record predates the rule and stays valid (a fresh gate of the same
            # kit judges it); a gate that ran it must show no unlanded reset port (or the kit's recorded waiver).
            rl = gate.get("reset_landing") if isinstance(gate, dict) else None
            if not isinstance(gate, dict):
                rows.append(dict(requires=n, ok=False, text="reset_landing: no gate result to judge"))
            elif rl is None:
                rows.append(dict(requires=n, ok=True, predates=True,
                                 text="reset_landing: gate predates the reset-landing rule (no reset_landing record): kept"))
            else:
                ok = bool(rl.get("ok")) if isinstance(rl, dict) else False
                over = (rl.get("over") if isinstance(rl, dict) else None) or []
                rows.append(dict(requires=n, ok=ok, over=over,
                                 text="reset_landing: " + ("every reset input landed" if ok and not over else
                                                           "waived by the kit" if ok else
                                                           f"unlanded reset input(s) {over[:4]} (FAIL)")))
            continue
        if n == "child_flop_basis":
            bases = [(clock or {}).get(f"{c}_pin_spread_basis") for c in ("tt", "ff")] if isinstance(clock, dict) else []
            if bases and all(b in ("child_flop", "child_pair") for b in bases):
                rows.append(dict(requires=n, ok=True, text="child_flop_basis: wires-only parent judged on with_child_flops "
                                                         f"({'/'.join(bases)}): dcd8111e5 does not change it"))
                continue
            refs = child_flop_reference_macros(root or Path(__file__).resolve().parents[2],
                                               (gate or {}).get("kit") if isinstance(gate, dict) else None)
            if refs is None:
                rows.append(dict(requires=n, ok=False, text="child_flop_basis: kit.env unreadable (re-gate)"))
            else:
                rows.append(dict(requires=n, ok=not refs, macros=refs,
                                 text="child_flop_basis: " + ("no macro with an insertion reference: R = 0, verdict "
                                                              "unchanged" if not refs else
                                                              f"{len(refs)} referenced macro(s) {refs[:3]}: re-gate")))
            continue
        if n == "landed_cluster_roots":
            # PL-GATE 10-18: per-root child-flop judgement + the unlanded cross-region FAIL apply only to a cluster kit
            # with children and clock "multiple_cts_roots"; every other gate is unchanged by that commit
            ck = clock if isinstance(clock, dict) else {}
            if ck.get("declared_clock") != "multiple_cts_roots" or "landed_child_links" in ck:
                rows.append(dict(requires=n, ok=True, text="landed_cluster_roots: not a multi-root cluster gate, or "
                                                          "already judged per root: unchanged"))
                continue
            kit = (gate or {}).get("kit") if isinstance(gate, dict) else None
            try:
                sp = json.loads((Path(root or Path(__file__).resolve().parents[2]) / "physical" / "ref_tile" / str(kit)
                                 / "spec.json").read_text())
                ok = not (sp.get("kind") == "cluster" and sp.get("children"))
            except (OSError, ValueError, AttributeError):
                ok = False
            rows.append(dict(requires=n, ok=ok, text="landed_cluster_roots: " + (
                "multi-root kit without hard children: unchanged" if ok else
                "multi-root cluster gated before the per-root child-flop rule (or spec unreadable): re-gate")))
            continue
        if n == "clock_pin_spread":
            sp = gate_pin_spreads(clock if isinstance(clock, dict) else {})
            tt, ff = sp.get("tt"), sp.get("ff")
            ok = tt is not None and tt[0] <= CLOCK_PIN_SPREAD_MAX_PS and (ff is None or ff[0] <= CLOCK_PIN_SPREAD_MAX_PS)
            waived = ""
            w = clock.get("clock_rule_waiver") if isinstance(clock, dict) else None
            if not ok and tt is not None and isinstance(w, dict):
                # S81-DEC5 10-18: the kit job's recorded per-pair waiver (HANDOFF 0ga), the same rule as the gate's
                import sys
                sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
                import textbook_lint as TL
                ok, note, _ = TL.clock_waiver_eval(clock, w)
                waived = f" -- WAIVED: {note}" if ok else ""
            text = ("0dq: no TT spread in the gate report" if tt is None else
                    f"0dq: TT {tt[1]} spread {tt[0]:.1f} ps" + (f", FF {ff[1]} spread {ff[0]:.1f} ps" if ff else
                                                               ", FF not reported (left to the routed audit)")
                    + (waived if waived else f" <= {CLOCK_PIN_SPREAD_MAX_PS:.0f}" if ok
                       else f" (limit {CLOCK_PIN_SPREAD_MAX_PS:.0f}: FAIL)"))
            rows.append(dict(requires=n, ok=ok, text=text, tt=tt and list(tt), ff=ff and list(ff),
                             ff_left_to_routed_audit=ff is None))
        else:
            rows.append(dict(requires=n, ok=False, text=f"unknown relaxed-rule requirement {n!r}"))
    return all(r["ok"] for r in rows), rows


def gate_overlay_paths(binding):
    """The daemon overlays the gate shipped and executed (orfs_hold_mm, fp_margin_lint, textbook_lint,
    macro_cts_cluster: pre_route_gate.SHIP_HELPERS).  Every other route-plan helper is route-only for the gate; a
    gate-run helper that is not an overlay (ck_insertion.py, path_classes.tcl, ref_route.sh) is a working-tree entry
    bound to the route source commit."""
    return sorted(e["path"] for e in binding.get("files", []) if e.get("source") == "daemon_overlay")


def route_only_drift(frozen, current, entries):
    """Route-plan helpers whose effective content changed since the gate and that the gate did not execute."""
    gate = {e["path"] for e in entries if e.get("source") == "daemon_overlay"}
    old = {r["path"]: r for r in frozen.get("files", [])}
    new = {r["path"]: r for r in (current or {}).get("files", [])}
    keys = ("sha256", "git_blob", "mode")
    return sorted(p for p in set(old) | set(new) if p not in gate
                  and tuple((old.get(p) or {}).get(k) for k in keys) != tuple((new.get(p) or {}).get(k) for k in keys))


def recover_verified_snapshot(binding, staged_root, log_bytes, script_bytes):
    """Recover original source identity after a parser failure, never infer a later commit.

    This verifies the complete shipping sidecar, all extracted bytes, the exact
    executed script, its SOURCE_COMMIT marker, and the remote archive-digest log.
    The returned binding describes that original run; current route qualification
    must still compare it against the requested route commit and live overlays.
    """
    import copy
    import re
    ok, why = validate(binding, staged_root, staged_root, route_overlay=False)
    if not ok:
        raise ValueError(why)
    if hashlib.sha256(script_bytes).hexdigest() != binding.get("remote_script_sha256"):
        raise ValueError("executed script differs from shipping manifest")
    log = log_bytes.decode(errors="replace")
    hashes = re.findall(r"^GATE_SOURCE_ARCHIVE_SHA256=(\S+)\s*$", log, re.M)
    if hashes != [binding.get("archive_sha256")]:
        raise ValueError("archive verification absent, ambiguous, or mismatched in original log")
    identity = binding.get("commit") or "snapshot-sha256:" + binding["manifest_sha256"]
    if (staged_root / "SOURCE_COMMIT").read_text().strip() != identity:
        raise ValueError("original SOURCE_COMMIT marker differs from exact snapshot identity")
    recovered = copy.deepcopy(binding)
    recovered["remote_archive_verified"] = True
    recovered["runtime_tool_provenance"] = re.findall(r"^GATE_TOOL_.*$", log, re.M)
    recovered["recovery"] = {"kind": "full_original_snapshot_verified", "log_sha256": hashlib.sha256(log_bytes).hexdigest(),
                             "staged_root": str(staged_root), "qualification": "original_source_only_not_current_HEAD"}
    return recovered


def staged_measurement_script(original_script, run):
    """Only resume original post-floorplan commands; never reconstruct old stdout."""
    start = original_script.index('C=$R/routes/gate/work/orfs;')
    tail = original_script[start:].replace('[ $FRC -eq 0 ] || exit 0', '')
    line = next(x for x in tail.splitlines() if 'make DESIGN_CONFIG=' in x and ' cts" >' in x)
    tail = tail.replace(line, '  echo GATE_CTS_RC=0; echo RECOVERY_CTS_REUSED_EXISTING_DATABASE')
    return ('set -uo pipefail\nR=' + str(run) + '\nexport PATH="$R/bin:$PATH"\n'
            'export OT_ORFS_CORNER_OVERRIDE=TC\ncd "$R/src"\n'
            "docker image inspect --format 'GATE_TOOL_IMAGE_ID={{.Id}} GATE_TOOL_IMAGE_DIGESTS={{json .RepoDigests}}' openroad/orfs:latest || exit 1\n"
            'echo RECOVERY_STAGED_REMEASUREMENT\n' + tail)


def staged_measurement_artifacts(run):
    """The physical state reused by the new measurement, including constraints."""
    run = Path(run)
    base = list((run / 'routes/gate/work/orfs/results/asap7').glob('*/base'))
    if len(base) != 1:
        raise ValueError('one original ORFS database directory required')
    required = [base[0] / n for n in ('1_2_yosys.v', '3_2_place_iop.odb', '4_1_cts.odb', '4_cts.sdc')]
    required += [run / 'routes/gate/work/orfs/config.mk']
    for p in required:
        if not p.is_file() or not p.stat().st_size:
            raise ValueError('missing original physical artifact: ' + str(p))
    return {str(p.relative_to(run)): hashlib.sha256(p.read_bytes()).hexdigest() for p in required}


def verify_staged_measurement_inputs(binding, run, original_script):
    run = Path(run)
    ok, why = validate(binding, run / 'src', run / 'src', route_overlay=False)
    if not ok:
        raise ValueError(why)
    if hashlib.sha256(original_script).hexdigest() != binding.get('remote_script_sha256'):
        raise ValueError('original execution script digest differs')
    identity = binding.get('commit') or 'snapshot-sha256:' + binding['manifest_sha256']
    if (run / 'src/SOURCE_COMMIT').read_text().strip() != identity:
        raise ValueError('original SOURCE_COMMIT marker differs')
    return staged_measurement_artifacts(run)


def staged_measurement_image(log_bytes):
    """New log must identify its actual tool and contain no reused-flow errors."""
    text = log_bytes.decode(errors='replace')
    if re.search(r'^GATE_FLOWERR\b', text, re.M):
        raise ValueError('new measurement reports a flow error')
    codes = re.findall(r'\bGATE_FLOW_RC=(\S+)', text)
    if any(code != '0' for code in codes):
        raise ValueError('new measurement reports nonzero flow status')
    identities = re.findall(r'^GATE_TOOL_IMAGE_ID=(sha256:[a-f0-9]{64})(?:\s|$)', text, re.M)
    if len(identities) != 1:
        raise ValueError('new measurement requires one actual tool image identity')
    return identities[0]


def run_staged_remeasurement(binding, run, original_script_path):
    """Execute a NEW canonical measurement on a verified, completed CTS database.

    Caller must use fleet admission. Original archive stdout remains unavailable.
    A before/after artifact check forbids changing the reused physical state.
    """
    run = Path(run)
    original = Path(original_script_path).read_bytes()
    artifacts = verify_staged_measurement_inputs(binding, run, original)
    script = staged_measurement_script(original.decode(), run).encode()
    script_path = run / 'staged_remeasurement.sh'
    log_path = run / 'staged_remeasurement.log'
    receipt_path = run / 'staged_remeasurement.json'
    if receipt_path.exists():
        raise ValueError('staged remeasurement already has a receipt; verify it instead of duplicating work')
    script_path.write_bytes(script)
    with log_path.open('wb') as log:
        result = subprocess.run(['bash', str(script_path)], stdout=log, stderr=subprocess.STDOUT)
    after = verify_staged_measurement_inputs(binding, run, original)
    if artifacts != after:
        raise ValueError('remeasurement modified original physical artifacts')
    if result.returncode or b'GATE_DONE' not in log_path.read_bytes():
        raise ValueError('new measurement did not finish successfully')
    image = staged_measurement_image(log_path.read_bytes())
    receipt = dict(schema='opentallas.ref_tile.staged_remeasurement.v1', tool_image_identity=image,
                   original_archive_stdout='unavailable', original_script_sha256=hashlib.sha256(original).hexdigest(),
                   manifest_sha256=binding['manifest_sha256'], artifacts_sha256=artifacts,
                   measurement_script_sha256=hashlib.sha256(script).hexdigest(),
                   measurement_log_sha256=hashlib.sha256(log_path.read_bytes()).hexdigest(),
                   new_measurement_only=True, physical_thresholds='unchanged')
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def recover_staged_remeasurement(binding, run, original_script_path, expected_log):
    """Rehash remote source, script, database, persisted new script/log and receipt."""
    import copy
    run = Path(run)
    original = Path(original_script_path).read_bytes()
    artifacts = verify_staged_measurement_inputs(binding, run, original)
    receipt = json.loads((run / 'staged_remeasurement.json').read_text())
    canonical = staged_measurement_script(original.decode(), run).encode()
    checks = {
        'schema': 'opentallas.ref_tile.staged_remeasurement.v1',
        'tool_image_identity': staged_measurement_image(expected_log),
        'original_archive_stdout': 'unavailable',
        'original_script_sha256': hashlib.sha256(original).hexdigest(),
        'manifest_sha256': binding['manifest_sha256'],
        'artifacts_sha256': artifacts,
        'measurement_script_sha256': hashlib.sha256(canonical).hexdigest(),
        'measurement_log_sha256': hashlib.sha256(expected_log).hexdigest(),
        'new_measurement_only': True, 'physical_thresholds': 'unchanged'}
    if receipt != checks:
        raise ValueError('new staged measurement receipt differs from rehashed evidence')
    if (run / 'staged_remeasurement.sh').read_bytes() != canonical:
        raise ValueError('new measurement script is not the canonical original-script continuation')
    if (run / 'staged_remeasurement.log').read_bytes() != expected_log:
        raise ValueError('new persisted measurement log differs')
    if b'GATE_DONE' not in expected_log:
        raise ValueError('new measurement log lacks completion')
    recovered = copy.deepcopy(binding)
    recovered.pop('remote_archive_verified', None)
    recovered['staged_remeasurement'] = receipt
    return recovered


def staged_remeasurement_matches_log(binding, log_bytes):
    """Receipt integrity guard; only remote rehash recovery can produce this receipt."""
    r = binding.get('staged_remeasurement') or {}
    try:
        image = staged_measurement_image(log_bytes)
    except ValueError:
        return False
    return (isinstance(r, dict) and r.get('tool_image_identity') == image and r.get('schema') == 'opentallas.ref_tile.staged_remeasurement.v1'
            and r.get('original_archive_stdout') == 'unavailable'
            and r.get('manifest_sha256') == binding.get('manifest_sha256')
            and r.get('original_script_sha256') == binding.get('remote_script_sha256')
            and r.get('measurement_log_sha256') == hashlib.sha256(log_bytes).hexdigest()
            and bool(r.get('artifacts_sha256')) and bool(r.get('measurement_script_sha256'))
            and r.get('new_measurement_only') is True and r.get('physical_thresholds') == 'unchanged'
            and not binding.get('remote_archive_verified'))
