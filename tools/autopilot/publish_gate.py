#!/usr/bin/env python3
"""publish_gate: the pre-apply gate every tree switch must pass (PUBLISH-GATE, FABLE-FLOW-2000 class B, third request).

Three KV trees (D3, D5, D8) failed only after the switch: D5 in pilot GEN (face_guard hash != provenance, 3 wrong frozen view
files), D8 in PRE/G0 (advisory clock.die_tree unknown to the schema).  Publish checked that files were copied, not that gen and
PRE/G0 accept them.  This gate runs, on the gen host that holds the tree and before apply_reviewed_tree_marker.py applies it:

  schema   tree/tools/die_plan/schema.py validate PLAN       (the schema the tree's own PRE/G0/bind use)
  pre_g0   plan_gate_pre.py check (SCHEMA unknown keys, INPUT, TOOLS, GEOM, ROWS) + check.py PLAN (G0)  - both of the tree
  contained the plan and every sidecar file it names lie INSIDE the tree (S81 D4: census/s81_lanes.tsv lived in a lane dir on one host,
           so no other host could reproduce PRE/G0); a plan outside the tree, or a named /srv file outside it, is a FAIL
  hashes   every provenance hash the tree bytes can answer: each view's landing_evidence/manifest.json sha256 map against the
           files, provenance.json kit.face_guard_sha256 against landing_evidence/face_guard_source.py, the plan sha256
  dry_gen  kit_wave.py run-item with spec dry_gen on ONE representative item of the die (the pilot item): kit_snap, kit_rtl,
           gen, gen_lint and kit preflight, the same code and the cfg the apply would write; it stops before place (no P&R)

  foreign_tree (ADVISORY, never part of the verdict; r693/r704) the candidate's inputs point outside the tree being published:
           kit_rtl.bind_out, the as-built manifest's base / land_r8, or any absolute path in the plan, asbuilt, sidecar, bind.f and
           injected manifest that lies in ANOTHER published tree or in a missing sibling of the candidate tree (QC N1B pre-rename
           tree 11-17; KV D22 11-18: asbuilt base + land_r8 still named the composer's scratch mirror, one gate run lost)

and writes autopilot/publish_gate/<die>/<tree manifest sha>.json = verdict PASS | FAIL with the four check results.  The apply
script refuses without a PASS record whose die, tree, manifest sha and plan sha256 match the candidate (require_pass()).

    publish_gate.py run --candidate JSON --expect-source OLD_TREE --expect-event OLD_EVENT [--item ITEM] [--kind type|core]
                        [--coord ~/coord] [--commit] [--work DIR] [--hub NAME] [--no-dry-gen-run (tests: skip the unit)]
    publish_gate.py static --tree T --plan P [--asbuilt A] [--plan-sha256 S] [--work DIR]   (runs on the gen host, prints PG_STATIC {json})
    publish_gate.py check --coord C --die D --tree T --manifest SHA --plan-sha256 S           (exit 0 = a matching PASS record)

Reviewed inherited G0 findings require candidate.g0_baseline={path,sha256}: a pinned record naming the exact reviewed plan hash, G0 report hash and complete ERROR identities. Only the same or a subset of those identities may pass; PRE/schema errors and every new finding still fail.

Nothing here changes a live config: the apply is projected on a scratch copy of the coord config, the dry gen runs in its own
work root, the only coord write is the record (committed by bin/coord-commit.sh with --commit)."""
import argparse
import hashlib
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path(".")   # shipped inline to the gen host (-c): no file
if "__file__" in globals() and str(HERE) not in sys.path:      # python3 -I does not put the script directory on sys.path
    sys.path.insert(0, str(HERE))
SCHEMA_ID = "opentallas.publish_gate.v1"
CHECKS = ("schema", "pre_g0", "hashes", "contained", "dry_gen")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------------------------------- record + apply-side check
def record_path(C, die, want):
    return Path(C) / "autopilot" / "publish_gate" / die / (str(want) + ".json")


def require_pass(C, die, tree, want, plan_sha256):
    """-> '' when a matching PASS record exists, else the reason the apply must refuse"""
    if not HEX64.match(str(want or "")):
        return "publish gate: tree manifest sha is not a 64-hex sha256"
    p = record_path(C, die, want)
    try:
        r = json.loads(p.read_text())
    except (OSError, ValueError):
        return f"publish gate: no PASS record {p} (run tools/autopilot/publish_gate.py run on this candidate first)"
    for k, v in (("schema", SCHEMA_ID), ("die", die), ("tree", tree), ("manifest_hash", want), ("plan_sha256", plan_sha256)):
        if r.get(k) != v:
            return f"publish gate: record {p.name} {k} {str(r.get(k))[:80]!r} != candidate {str(v)[:80]!r}"
    bad = [c for c in CHECKS if ((r.get("checks") or {}).get(c) or {}).get("verdict") != "PASS"]
    if r.get("verdict") != "PASS" or bad:
        return f"publish gate: record {p.name} is {r.get('verdict')}, checks not PASS: {','.join(bad) or '-'}"
    return ""


# --------------------------------------------------------------------------------------------------- static checks (run on the gen host)
def check_hashes(tree, plan=None, plan_sha256=None):
    """-> (findings, n_views).  Pure stdlib, reads tree bytes only.  A finding is one line 'HASH <what>: <detail>'."""
    out, n = [], 0
    if plan and plan_sha256:
        try:
            got = sha256_file(plan)
            if got != plan_sha256:
                out.append(f"HASH plan {plan}: sha256 {got[:12]} != candidate plan_sha256 {plan_sha256[:12]}")
        except OSError as e:
            out.append(f"HASH plan {plan}: unreadable ({e})")
    root = Path(tree) / "physical"
    for dp, dns, fns in os.walk(root):
        if os.path.basename(dp) != "landing_evidence":
            continue
        dns[:] = []
        n += 1
        le, view = Path(dp), Path(dp).parent
        name = str(view.relative_to(tree))
        try:
            man = json.loads((le / "manifest.json").read_text())
        except (OSError, ValueError) as e:
            out.append(f"HASH {name}: landing_evidence/manifest.json unreadable ({type(e).__name__})")
            continue
        for fn, want in sorted((man.get("sha256") or {}).items()):
            try:
                got = sha256_file(le / fn)
            except OSError:
                out.append(f"HASH {name}: landing_evidence/{fn} missing (manifest names it)")
                continue
            if got != want:
                out.append(f"HASH {name}: landing_evidence/{fn} sha256 {got[:12]} != manifest {str(want)[:12]}")
        try:
            prov = json.loads((view / "provenance.json").read_text())
        except (OSError, ValueError):
            out.append(f"HASH {name}: provenance.json unreadable")
            continue
        fg = (prov.get("kit") or {}).get("face_guard_sha256")
        if fg:
            try:
                got = sha256_file(le / "face_guard_source.py")
            except OSError:
                out.append(f"HASH {name}: landing_evidence/face_guard_source.py missing (provenance records face_guard_sha256)")
                continue
            if got != fg:
                out.append(f"HASH {name}: face_guard_source.py sha256 {got[:12]} != provenance kit.face_guard_sha256 {str(fg)[:12]}")
    return out, n


SIDECAR_EXT = (".json", ".tsv", ".gz", ".csv", ".v", ".sv", ".lef", ".lib", ".yaml", ".py", ".txt")


def check_contained(tree, plan, roots=("/srv/",)):
    """-> findings.  The published tree must reproduce PRE/G0 on any host that holds it: the plan file is inside the tree (its sidecars
    census/, core_conns.json ... are found relative to the plan dir), and every absolute /srv file path the plan names exists inside
    the tree, not in a lane directory."""
    out = []
    root = os.path.realpath(tree) + os.sep
    rp = os.path.realpath(plan)
    if not (rp + os.sep).startswith(root):
        out.append(f"CONTAINED plan {plan} is outside the tree: its sidecars (census/, core_conns.json, ...) live next to it, not in the published tree")
        d = os.path.dirname(rp)
        if os.path.isdir(os.path.join(d, "census")):
            out.append(f"CONTAINED sidecar dir {d}/census is outside the tree")
    try:
        obj = json.loads(Path(plan).read_text())
    except (OSError, ValueError):
        return out
    seen = set()

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str) and v.startswith(tuple(roots)) and v.endswith(SIDECAR_EXT) and v not in seen:
            seen.add(v)
            if os.path.isfile(v) and not (os.path.realpath(v) + os.sep).startswith(root):
                out.append(f"CONTAINED plan names {v}, a file outside the tree")
    walk(obj)
    return out[:30]


# QC M5 11-17: the QC plan (37 MB, 133 types) takes ~48 min in check.py G0 on E8; a 1800 s cap failed a clean tree on time.
# One wall-clock budget per static step, the same 6 h the dry gen already has; the remote static run gets all three steps.
STEP_TIMEOUT_S = 6 * 3600


def _sub(argv, cwd, timeout=STEP_TIMEOUT_S):
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)
    except (OSError, subprocess.SubprocessError) as e:
        return 99, f"{type(e).__name__}: {e}"


def load_g0_baseline(spec):
    """Read an explicitly pinned review record; it never changes plan or check output."""
    if not spec:
        return None
    path, want = spec.get("path"), spec.get("sha256")
    if not path or not HEX64.fullmatch(str(want or "")) or sha256_file(path) != want:
        raise ValueError("G0 baseline record path/hash mismatch")
    record = json.loads(Path(path).read_text())
    record["_record_sha256"] = want
    return record


def g0_baseline_check(plan, report, baseline, rc):
    """Compare complete ERROR identity/context multisets, with no numeric/path masking."""
    if baseline is None:
        return {"verdict": "PASS" if rc == 0 else "FAIL", "inherited": False}
    def refuse(why):
        return {"verdict": "FAIL", "inherited": False, "why": why}
    if baseline.get("schema") != "opentallas.publish_gate.g0_baseline.v1":
        return refuse("invalid G0 baseline schema")
    if baseline.get("reviewed_plan_sha256") != sha256_file(plan):
        return refuse("G0 baseline reviewed plan hash differs from candidate")
    if not HEX64.fullmatch(str(baseline.get("reviewed_g0_sha256") or "")) or not baseline.get("review"):
        return refuse("G0 baseline needs a pinned reviewed G0 report and review")
    accepted = baseline.get("accepted_errors")
    if not isinstance(accepted, list) or any(not isinstance(x, dict) or x.get("level") != "ERROR"
                                           or not x.get("check") or not x.get("msg") for x in accepted):
        return refuse("G0 baseline accepted_errors must contain complete ERROR identities")
    if rc == 0:
        return {"verdict": "PASS", "inherited": False, "record_sha256": baseline.get("_record_sha256")}
    if rc != 1 or not isinstance(report, dict) or report.get("schema") != "opentallas.die_plan.g0.v1":
        return refuse("G0 did not produce a complete failing report")
    current = [x for x in report.get("findings", []) if isinstance(x, dict) and x.get("level") == "ERROR"]
    if report.get("verdict") != "FAIL" or not current or report.get("errors") != len(current) or report.get("pending_view", 0):
        return refuse("G0 exit/report/error census mismatch")
    # Canonical serialization normalizes dictionary order only; message values,
    # coordinates, bus widths, instance names and every context field stay exact.
    remaining = [json.dumps(x, sort_keys=True, separators=(",", ":")) for x in accepted]
    extra = []
    for error in current:
        identity = json.dumps(error, sort_keys=True, separators=(",", ":"))
        if identity in remaining:
            remaining.remove(identity)
        else:
            extra.append(error)
    if extra:
        return dict(refuse("new G0 ERROR identities outside the reviewed baseline"), new_errors=extra)
    return {"verdict": "PASS", "inherited": True, "errors": len(current), "accepted": len(accepted),
            "review": baseline["review"], "reviewed_plan_sha256": baseline["reviewed_plan_sha256"],
            "reviewed_g0_sha256": baseline["reviewed_g0_sha256"], "record_sha256": baseline.get("_record_sha256")}


def proof_paths(tree, rows_proofs):
    """candidate.rows_proofs (files INSIDE the tree, absolute or tree-relative) -> absolute paths, in order"""
    return [p if os.path.isabs(p) else os.path.join(str(tree), p) for p in (str(x) for x in (rows_proofs or []))]


def check_proofs_contained(tree, rows_proofs):
    """FABLE-FIX-QC-N 11-17: a rows proof PRE reads must be a file of the published tree (the same rule as every plan input)"""
    root = os.path.realpath(str(tree)) + os.sep
    out = []
    for p in proof_paths(tree, rows_proofs):
        if not (os.path.realpath(p) + os.sep).startswith(root):
            out.append(f"CONTAINED rows proof {p} is outside the tree")
        elif not os.path.isfile(p):
            out.append(f"CONTAINED rows proof {p} is missing")
    return out


_PATH_RE = re.compile(r"/[A-Za-z0-9_.+@=-]+(?:/[A-Za-z0-9_.+@=-]+)+")
ASBUILT_PATH_KEYS = ("base", "land_r8")


def check_foreign_trees(tree, files, asbuilts=(), bind_out=None, max_depth=12):
    """-> findings (ADVISORY: reported in the record, never part of the gate verdict).  The inputs of a publish must lie in the
    tree being published, or a host that holds only that tree cannot reproduce the bind / kit RTL:
      (a) named fields: kit_rtl.bind_out and each as-built manifest's base / land_r8, when absolute, resolve inside TREE
          (KV D22 11-18: base + land_r8 still pointed at the composer's scratch mirror);
      (b) every absolute path in FILES (plan, asbuilt, sidecar, bind_out bind.f / injected manifest) is resolved to the nearest
          ancestor holding .src-manifest.sha256: another published tree is a finding, and so is a sibling of TREE that is
          missing on this host (FABLE-FLOW-1700 11-17, QC N1B: stale pre-rename tree names).  Other paths (lane dirs, PDK) pass."""
    root = os.path.realpath(str(tree))
    roots, out, seen = {}, [], set()

    def inside(path):
        rp = os.path.realpath(path)
        return rp == root or rp.startswith(root + os.sep)

    if bind_out and str(bind_out).startswith("/") and not inside(str(bind_out)):
        out.append(f"FOREIGN-TREE kit_rtl.bind_out {bind_out} is outside the candidate tree {root}")
        seen.add(str(bind_out))
    for ab in asbuilts or []:
        try:
            obj = json.loads(Path(str(ab)).read_text())
        except (OSError, ValueError, TypeError):
            continue
        for k in ASBUILT_PATH_KEYS:
            v = obj.get(k) if isinstance(obj, dict) else None
            if isinstance(v, str) and v.startswith("/") and not inside(v):
                out.append(f"FOREIGN-TREE asbuilt {ab} {k} = {v} is outside the candidate tree {root}")
                seen.add(v)

    def tree_of(path):
        d = os.path.dirname(path)
        chain = []
        for _ in range(max_depth):
            if d in roots:
                hit = roots[d]
                break
            chain.append(d)
            if os.path.isfile(os.path.join(d, ".src-manifest.sha256")):
                hit = d
                break
            nd = os.path.dirname(d)
            if nd == d:
                hit = None
                break
            d = nd
        else:
            hit = None
        for c in chain:
            roots[c] = hit
        return hit

    parent = os.path.dirname(root) + os.sep
    for f in files or []:
        if not f or not os.path.isfile(str(f)):
            continue
        try:
            txt = Path(str(f)).read_text(errors="replace")
        except OSError:
            continue
        for m in sorted(set(_PATH_RE.findall(txt))):
            if m == root or m.startswith(root + os.sep) or m in seen:
                continue
            seen.add(m)
            t = tree_of(m)
            if t and os.path.realpath(t) != root:
                out.append(f"FOREIGN-TREE {f} names {m} (published tree {t}, not the candidate tree {root})")
            elif not t and m.startswith(parent):
                # a sibling of the candidate tree that does not exist here = a stale tree name (renamed / not replicated)
                top = parent + m[len(parent):].split(os.sep, 1)[0]
                if not os.path.exists(top):
                    out.append(f"FOREIGN-TREE {f} names {m} (sibling {top} of the candidate tree is missing on this host)")
    return sorted(out)


def check_bound_params(tree, bind_out):
    """-> findings (ADVISORY, BOUND-PARAM-1 11-18): every parameter the bound parts (BIND_OUT/rtl) pass to a module is declared
    by a definition of that module in TREE (KV D23g: plan key landing_ring_lite emitted .LITE(1) rings, the tree kept the ring
    RTL without LITE; bind/G0/LATCHECK passed, kit elaboration would fail).  Uses the executing checkout when available and the candidate's tool tree for the inline static gate."""
    rtl = os.path.join(str(bind_out or ""), "rtl")
    if not bind_out or not os.path.isdir(rtl):
        return []
    source_file = globals().get("__file__")
    tool_dir = (Path(source_file).resolve().parents[1] / "die_plan" if source_file
                else Path(tree) / "tools" / "die_plan")
    if not (tool_dir / "bound_param_check.py").is_file():
        return [f"BOUND-PARAM unavailable: no checker in {tool_dir}"]
    sys.path.insert(0, str(tool_dir))
    try:
        import bound_param_check as BPC
    finally:
        sys.path.pop(0)
    r = BPC.check(str(tree), rtl)
    return list(r["errors"])


def run_static(tree, plan, asbuilt=None, plan_sha256=None, work=None, g0_baseline=None, rows_proofs=None, scan=None, scan_asbuilt=None,
               bind_out=None, band_base=None):
    """-> {schema, pre_g0, hashes: {verdict, ...}}.  Uses the TREE's own tools (the ones PRE/G0/bind will run), python3 -I."""
    tree, plan = str(tree), str(plan)
    work = work or tempfile.mkdtemp(prefix="pubgate-")
    dp = os.path.join(tree, "tools", "die_plan")
    py = sys.executable
    res = {}
    if not os.path.isfile(plan):
        miss = {"verdict": "FAIL", "why": f"plan file missing: {plan}"}
        return {c: dict(miss) for c in ("schema", "pre_g0", "hashes", "contained")}
    # schema.py imports its sibling modules; python3 -I drops the script directory from sys.path, so put the tree's in
    rc, txt = _sub([py, "-I", "-c", "import sys; sys.path.insert(0, %r); import schema; sys.exit(schema.main(['schema.py', 'validate', %r]))" % (dp, plan)], tree)
    res["schema"] = {"verdict": "PASS" if rc == 0 else "FAIL", "rc": rc, "tail": txt[-1500:]}
    pre = [py, "-I", os.path.join(dp, "plan_gate_pre.py"), "check", "--tree", tree, "--plan", plan, "--quiet"]
    if asbuilt:
        pre += ["--asbuilt", str(asbuilt)]
    # QC N2B 11-17: new consumer_localization rows need their rows proof (ROWS-NO-PROOF otherwise); candidate.rows_proofs -> --rows-proof
    for rp in proof_paths(tree, rows_proofs):
        pre += ["--rows-proof", rp]
    # REMAP-BASE-1122: LANDREMAP / ISTCYC compare with the die's live plan of record (band_base), when the tree's checker knows --remap-base
    if band_base and os.path.isfile(band_base) and "--remap-base" in Path(dp, "plan_gate_pre.py").read_text(errors="replace"):
        pre += ["--remap-base", str(band_base)]
    rc1, t1 = _sub(pre, tree)
    Path(work).mkdir(parents=True, exist_ok=True)
    g0_dir = tempfile.mkdtemp(prefix="g0-", dir=work)  # never accept a stale report after a crashed checker
    g0 = [py, "-I", os.path.join(dp, "check.py"), plan, "--quiet", "--out", g0_dir]
    # LANDING-BAND-CORE (COORD 11-22): the die's live plan of record is the base: its band x core overlaps are inherited (WARN), new ones ERROR.
    # Only a check.py that knows --band-base gets it (an older tree's checker has no landing_band_core at all).
    if band_base and os.path.isfile(band_base) and "--band-base" in Path(dp, "check.py").read_text(errors="replace"):
        g0 += ["--band-base", band_base]
    rc2, t2 = _sub(g0, tree)
    try:
        g0_report = json.loads(Path(g0_dir, "g0_report.json").read_text())
    except (OSError, ValueError):
        g0_report = None
    allowance = g0_baseline_check(plan, g0_report, g0_baseline, rc2)
    res["pre_g0"] = {"verdict": "PASS" if rc1 == 0 and allowance["verdict"] == "PASS" else "FAIL",
                     "pre_rc": rc1, "g0_rc": rc2, "g0_report": str(Path(g0_dir, "g0_report.json")),
                     "baseline": allowance, "tail": ("PRE: " + t1[-900:] + "\nG0: " + t2[-900:])}
    finds, n = check_hashes(tree, plan, plan_sha256)
    res["hashes"] = {"verdict": "PASS" if not finds and n else "FAIL", "views": n, "findings": finds[:40],
                     **({"why": "no landing_evidence view found under the tree"} if not n and not finds else {})}
    cf = check_contained(tree, plan) + check_proofs_contained(tree, rows_proofs)
    res["contained"] = {"verdict": "PASS" if not cf else "FAIL", "findings": cf}
    # ADVISORY (r693/r704: the gate is a report): not in CHECKS, so it never changes the verdict; the record's advisory list names it
    ft = check_foreign_trees(tree, [plan, asbuilt] + list(scan or []), [asbuilt] + list(scan_asbuilt or []), bind_out)
    res["foreign_tree"] = {"verdict": "PASS" if not ft else "ADVISORY", "advisory": True, "n": len(ft), "findings": ft[:40]}
    bp = check_bound_params(tree, bind_out)
    res["bound_params"] = {"verdict": "PASS" if not bp else "ADVISORY", "advisory": True, "n": len(bp), "findings": bp[:40]}
    return res


# --------------------------------------------------------------------------------------------------- orchestration (hub)
def static_remote(host, work_dir, tree, plan, asbuilt, plan_sha256, runner=subprocess.run, hub_names=("localhost",), g0_baseline=None,
                  rows_proofs=None, scan=None, scan_asbuilt=None, bind_out=None, band_base=None):
    """runs the static checks ON the gen host that holds the tree: this file is shipped inline (python3 -I -c, the host has no checkout
    of the tool).  Read-only, ~20 s of one core (PRE imports the tree's tool modules), so plain ssh under nice, not an ot-run job:
    ot-run refuses a job that names a 300k-file tree outside its --dir and would SPILL-copy it."""
    q = shlex.quote
    cmd = (f"mkdir -p {q(work_dir)} && nice -n 10 python3 -I -c {q(Path(__file__).read_text())} static --tree {q(tree)} --plan {q(plan)} "
           f"--plan-sha256 {q(plan_sha256)}" + (f" --asbuilt {q(asbuilt)}" if asbuilt else "") + f" --work {q(work_dir)}"
           + (f" --g0-baseline-json {q(json.dumps(g0_baseline))}" if g0_baseline is not None else "")
           + "".join(f" --rows-proof {q(str(rp))}" for rp in rows_proofs or [])
           + "".join(f" --scan {q(str(x))}" for x in scan or []) + "".join(f" --scan-asbuilt {q(str(x))}" for x in scan_asbuilt or [])
           + (f" --bind-out {q(str(bind_out))}" if bind_out else "")
           + (f" --band-base {q(str(band_base))}" if band_base else ""))
    argv = ["bash", "-c", cmd] if host in hub_names else ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", host, "bash -c " + q(cmd)]
    p = runner(argv, capture_output=True, text=True, timeout=3 * STEP_TIMEOUT_S + 600)
    txt = (p.stdout or "") + (p.stderr or "")
    got = [ln[len("PG_STATIC "):] for ln in txt.splitlines() if ln.startswith("PG_STATIC ")]
    if not got:
        why = f"no PG_STATIC line (rc {p.returncode}): " + txt[-400:]
        return {c: {"verdict": "FAIL", "why": why} for c in ("schema", "pre_g0", "hashes", "contained")}
    return json.loads(got[-1])


def project_cfg(C, obj, expect_source, expect_event, item=None, TC=None):
    """the kit_wave config the apply WOULD write, from a scratch copy of the coord config (apply_marker itself, so no second
    implementation; the scratch has no live path).  -> (cfg_text, die, item)"""
    import apply_reviewed_tree_marker as A
    import hold_records as HR
    if TC is None:
        import tree_check as TC
    C = Path(C)
    marker = dict(obj.get("marker", obj))
    die = marker["die"]
    with tempfile.TemporaryDirectory(prefix="pubgate-cfg-") as td:
        S = Path(td)
        (S / "autopilot").mkdir()
        (S / "lanes/handoff").mkdir(parents=True)
        (S / "autopilot/kit_wave.json").write_text((C / "autopilot/kit_wave.json").read_text())
        os.symlink(C / "autopilot/tree_checks", S / "autopilot/tree_checks")
        A.apply_marker(S, dict(obj), expect_source, expect_event, no_pilot=True, TC=TC, PG=False)
        text = (S / "autopilot/kit_wave.json").read_text()
    cfg = json.loads(text)
    pick = item or HR.pilot_item_for(cfg, die, cfg["dies"][die])
    return text, die, pick


def dry_gen(cfg_text, die, item, kind, work_root, hub, gen_host, run_unit=True, want=""):
    """build the item spec from the projected cfg, run kit_wave run-item with dry_gen, -> check dict"""
    sys.path.insert(0, str(HERE))
    import kit_wave as KW
    cfg = KW.load_config(cfg_text)
    cfg["_hub"] = hub
    cfg["dies"][die]["event"] = "pg" + str(want)[:10]
    sp = KW.spec_for(dict(cfg, _otrun_status={}), die, item, hub, kind=kind)
    sp.update(dry_gen=True, gen_host=gen_host)
    jd = Path(work_root) / die / str(want)[:12] / item
    jd.mkdir(parents=True, exist_ok=True)
    (jd / "spec.json").write_text(json.dumps(sp, indent=1))
    out = {"verdict": "FAIL", "item": item, "kind": kind, "gen_host": gen_host, "dir": str(jd), "spec_src": sp.get("src")}
    if not run_unit:
        out["why"] = "unit not run"
        return out
    import published_gen_origin as PGO
    try:
        out.update(PGO.capture(cfg, die, sp, jd, KW))
    except (AssertionError, OSError, ValueError, TypeError, KeyError, AttributeError) as e:
        out["origin_capture_error"] = str(e)       # metadata refusal never changes the publish-gate verdict
    code = ("import sys,runpy;sys.path.insert(0,%r);sys.argv=['kit_wave.py','run-item',%r];"
            "runpy.run_path(%r,run_name='__main__')" % (str(HERE), str(jd / "spec.json"), str(HERE / "kit_wave.py")))
    with open(jd / "unit.log", "w") as lg:
        p = subprocess.run([sys.executable, "-I", "-c", code], stdout=lg, stderr=subprocess.STDOUT, timeout=6 * 3600)
    try:
        res = json.loads((jd / "result.json").read_text())
    except (OSError, ValueError):
        res = {}
    out.update(rc=p.returncode, stage=res.get("stage"), result=res.get("verdict"))
    out.update(PGO.seal(jd, p.returncode))
    if res.get("verdict") == "DRY-PASS" and p.returncode == 0:
        out["verdict"] = "PASS"
        out["preflight_fail_advisory"] = res.get("preflight_fail_advisory")
    else:
        out["why"] = ("stage %s: %s" % (res.get("stage"), "; ".join([res["errors"]] if isinstance(res.get("errors"), str) else (res.get("errors") or [])) or str(res.get("tail") or "")[-600:]))[:1500]
    return out


def write_record(C, rec, commit=False, runner=subprocess.run):
    p = record_path(C, rec["die"], rec["manifest_hash"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp.%d" % os.getpid())
    tmp.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, p)
    if commit:
        rel = str(p.relative_to(C))
        r = runner([str(Path(C) / "bin/coord-commit.sh"), f"PUBLISH-GATE {rec['verdict']} {rec['die']} {rec['manifest_hash'][:12]}", rel],
                   capture_output=True, text=True, timeout=900)
        rec["_commit"] = (r.stdout or "").strip().splitlines()[-1:] or r.returncode
    return p


def run_gate(C, obj, expect_source, expect_event, item=None, kind="type", work=None, hub=None, commit=False, run_unit=True, 
             static_fn=None, dry_fn=None, TC=None, gen_host=None, static_host=None):
    marker = dict(obj.get("marker", obj))
    die, tree = marker["die"], marker["tree"]
    want = marker.get("manifest_hash") or marker["src_manifest_sha"]
    plan, plan_sha = marker["plan"], marker["plan_sha256"]
    hosts = list((marker.get("config") or {}).get("gen_hosts") or marker.get("hosts") or [])
    rec = {"schema": SCHEMA_ID, "die": die, "tree": tree, "manifest_hash": want, "plan": plan, "plan_sha256": plan_sha, "hosts": hosts,
           "t": time.time(), "checks": {}, "verdict": "FAIL"}
    hub = hub or os.environ.get("OT_HUB_NAME") or socket.gethostname()
    work = work or os.path.expanduser("~/.local/state/publish-gate")
    try:
        text, die2, pick = project_cfg(C, obj, expect_source, expect_event, item, TC)
        cfgd = json.loads(text)["dies"][die]
        hosts = list(cfgd.get("gen_hosts") or hosts)
        if gen_host:                               # run the gate on this host (one of the die's gen hosts), not hosts[0]
            assert gen_host in hosts, f"--gen-host {gen_host} is not a gen host of the die {hosts}"
            hosts = [gen_host] + [h for h in hosts if h != gen_host]
        rec["hosts"] = hosts
        if not pick:
            raise AssertionError("no representative item: pass --item or set die.pilot_item")
        rec["item"] = pick
        wr = str(cfgd.get("work_root") or json.loads((Path(C) / "autopilot/kit_wave.json").read_text()).get("work_root") or "/tmp")
        baseline = load_g0_baseline(marker.get("g0_baseline") or obj.get("g0_baseline"))
        # LANDING-BAND-CORE (COORD 11-22): base plan of record = candidate.band_base, else the die's LIVE plan in the coord config (pre-apply)
        try:
            live = (json.loads((Path(C) / "autopilot/kit_wave.json").read_text()).get("dies") or {}).get(die) or {}
        except (OSError, ValueError):
            live = {}
        band_base = marker.get("band_base") or obj.get("band_base") or (live.get("plan") if live.get("plan") != plan else None)
        rec["band_base"] = band_base
        rows_proofs = list(marker.get("rows_proofs") or obj.get("rows_proofs") or [])
        rec["rows_proofs"] = rows_proofs
        # FOREIGN-TREE (advisory): what the candidate's kit RTL will read besides the plan and the marker asbuilt
        kr = (marker.get("config") or {}).get("kit_rtl") or {}
        bind_out = marker.get("bind_out") or kr.get("bind_out")
        scan_ab = [x for x in (kr.get("asbuilt"),) if x and x != marker.get("asbuilt")]
        scan = [x for x in (marker.get("sidecar"),) if x] + scan_ab
        if bind_out:
            inj = os.path.join(bind_out, "asbuilt_manifest_injected.json")
            scan += [os.path.join(bind_out, "bind.f"), inj]
            scan_ab.append(inj)
        rec["foreign_tree_scan"] = {"bind_out": bind_out, "files": scan, "asbuilts": scan_ab}
        # LATENCY-R 11-18: the static checks (PRE + G0: 13-39 min) and the dry gen (13-53 min) ran one after the other (QC M5 gate 92 min, S81 D7w 34 min).
        # They read the same published tree and write separate dirs, so they now run at the same time; the gate takes the longer of the two.  A failed
        # static check no longer skips the dry gen: both verdicts are recorded (the verdict rule is unchanged: every check must PASS).
        import concurrent.futures as CF

        def _dry():
            try:
                return (dry_fn or (lambda t, d, i, k, h, w: dry_gen(t, d, i, k, work, hub, h, run_unit, w)))(text, die, pick, kind, hosts[0], want)
            except Exception as e:                 # a dry gen that cannot run is a FAIL of that check, never a pass
                return {"verdict": "FAIL", "why": f"dry gen did not run: {type(e).__name__}: {e}"[:600]}
        with CF.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_dry)
            t0 = time.time()
            st = (static_fn or (lambda h, t, p, ab, ps: static_remote(h, wr + "/pubgate", t, p, ab, ps, hub_names=("localhost", hub), g0_baseline=baseline,
                                                                       rows_proofs=rows_proofs, scan=scan, scan_asbuilt=scan_ab,
                                                                       bind_out=bind_out, band_base=band_base)))(
                static_host or hosts[0], tree, plan, marker.get("asbuilt"), plan_sha)
            rec["checks"].update(st)
            rec["static_s"] = round(time.time() - t0, 1)
            rec["checks"]["dry_gen"] = fut.result()
            rec["gate_s"] = round(time.time() - t0, 1)
    except Exception as e:                         # a gate that cannot run is a FAIL, never a pass
        rec["checks"].setdefault("gate", {"verdict": "FAIL", "why": f"{type(e).__name__}: {e}"[:600]})
    rec["verdict"] = "PASS" if all((rec["checks"].get(c) or {}).get("verdict") == "PASS" for c in CHECKS) else "FAIL"
    # COORD 11-18 (optimistic launch): the gate is advisory for an optimistic apply; the record lists what a reader should look at
    rec["advisory"] = sorted(c for c, v in rec["checks"].items() if (v or {}).get("verdict") != "PASS")
    write_record(C, rec, commit)
    return rec


def main(argv=None):
    P = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = P.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--candidate", required=True)
    r.add_argument("--expect-source", required=True)
    r.add_argument("--expect-event", required=True)
    r.add_argument("--item")
    r.add_argument("--kind", default="type")
    r.add_argument("--coord", default=os.path.expanduser("~/coord"))
    r.add_argument("--commit", action="store_true", help="commit the record with bin/coord-commit.sh")
    r.add_argument("--work")
    r.add_argument("--hub")
    r.add_argument("--static-host", help="host for the static checks when the plan sidecars live only there (DEBUGGING only: a gate that needs it is a FAIL on `contained`; default: the gen host)")
    r.add_argument("--gen-host", help="run the static checks and the dry gen on this gen host of the die")
    s = sub.add_parser("static")
    s.add_argument("--tree", required=True)
    s.add_argument("--plan", required=True)
    s.add_argument("--asbuilt")
    s.add_argument("--plan-sha256")
    s.add_argument("--work")
    s.add_argument("--g0-baseline-json", help="pinned review record (normally shipped by run from candidate.g0_baseline)")
    s.add_argument("--rows-proof", action="append", default=[], help="rows proof file inside the tree for PRE (normally shipped by run from candidate.rows_proofs)")
    s.add_argument("--scan", action="append", default=[], help="extra input file scanned for paths in another published tree (sidecar, bind.f ...); advisory")
    s.add_argument("--scan-asbuilt", action="append", default=[], help="extra as-built manifest whose base / land_r8 must lie in the tree; advisory")
    s.add_argument("--bind-out", help="kit_rtl.bind_out of the candidate; outside the tree = advisory FOREIGN-TREE finding")
    s.add_argument("--band-base", help="base plan of record for G0 landing_band_core (inherited overlaps WARN, new ERROR)")
    c = sub.add_parser("check")
    c.add_argument("--coord", default=os.path.expanduser("~/coord"))
    c.add_argument("--die", required=True)
    c.add_argument("--tree", required=True)
    c.add_argument("--manifest", required=True)
    c.add_argument("--plan-sha256", required=True)
    a = P.parse_args(argv)
    if a.cmd == "static":
        print("PG_STATIC " + json.dumps(run_static(a.tree, a.plan, a.asbuilt, a.plan_sha256, a.work, json.loads(a.g0_baseline_json) if a.g0_baseline_json else None,
                                                   rows_proofs=a.rows_proof, scan=a.scan, scan_asbuilt=a.scan_asbuilt, bind_out=a.bind_out,
                                                   band_base=a.band_base)))
        return 0
    if a.cmd == "check":
        why = require_pass(a.coord, a.die, a.tree, a.manifest, a.plan_sha256)
        print(why or "PASS")
        return 1 if why else 0
    obj = json.loads(Path(a.candidate).read_text())
    rec = run_gate(a.coord, obj, a.expect_source, a.expect_event, a.item, a.kind, a.work, a.hub, a.commit, gen_host=a.gen_host, static_host=a.static_host)
    print(json.dumps({k: (v if k != "checks" else {c: (x or {}).get("verdict") for c, x in v.items()}) for k, v in rec.items()}))
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
