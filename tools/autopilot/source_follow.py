#!/usr/bin/env python3
"""Prepare immutable kit-wave sources; only strict-bind-clean candidates become active.

The timer starts a preparation unit and keeps launching from its previous source.
No config file or existing source/bind tree is modified. State owns the override.
"""
import argparse
import copy
import json
import inspect
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys



def materialize_clock_mesh(src, plan, read_archive):
    """Close the plan's exact mesh input; recover only the known hash-pinned archive."""
    import gzip
    import hashlib
    import json
    from pathlib import Path
    src = Path(src).resolve()
    plan = Path(plan)
    mesh = json.loads(plan.read_text()).get("clock", {}).get("mesh", {})
    if not mesh.get("sites_file"):
        return
    target = (plan.parent / mesh["sites_file"]).resolve()
    expected = mesh.get("sites_sha256")
    recovery = {
        "d25f60c6f22e6921a36d73a850b3bc8a3822f0e5545879ff05e84bd1755513db":
        "98711b8be0:results/clock_kv_r25/plan/clock_mesh_sites_r25.json.gz"
    }
    # This recovery adds no contract to other existing mesh declarations.
    if expected not in recovery:
        return
    if not target.is_relative_to(src):
        raise ValueError("clock mesh sites path escapes source snapshot")
    if target.exists():
        body = target.read_bytes()
    else:
        if expected not in recovery:
            raise ValueError("missing declared clock mesh sites: " + str(target))
        body = gzip.decompress(read_archive(recovery[expected]))
    if not expected or hashlib.sha256(body).hexdigest() != expected:
        raise ValueError("declared clock mesh sites hash mismatch")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(body)


def copy_untracked_inputs(old_source, new_source):
    """Copy the base source's untracked plan/bind inputs into a fresh snapshot (never over a tracked file).

    KV event sources carry untracked inputs read by the plan and the strict bind (kv36/kv37/kv40 pad tables,
    the composed_rtl receipt); a snapshot of a newer main tip without them FAILs the strict bind
    (KIT-WAVE-15 11-01: kv37/pv_col_pads_28b.json missing on b1a2125433d0)."""
    import shutil
    import subprocess
    from pathlib import Path
    old_source, new_source = Path(old_source), Path(new_source)
    out = subprocess.run(["git", "-C", str(old_source), "ls-files", "--others", "--exclude-standard", "-z"],
                         text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
    copied = []
    for rel in sorted(x for x in out.split("\0") if x):
        if rel.endswith(".pyc") or "/__pycache__/" in "/" + rel:
            continue
        f, nf = old_source / rel, new_source / rel
        if f.is_file() and not f.is_symlink() and not nf.exists():
            nf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, nf)
            copied.append(rel)
    return copied


def link_previous_snapshot(repo, src, tip, dirs, die_root):
    """Delta snapshot: hard-link every file tracked at tip (inside the sparse dirs) whose content is unchanged
    since the newest complete sibling snapshot, before the checkout; returns (previous src, linked count).

    KIT-WAVE-15 11-01: one full ~32 GB checkout per main sha (15 KV snapshots, 377 GB) filled intel1.  Linked
    files are immutable source inputs and made read-only (a-w) on the shared inode; git writes every changed or
    new file as a fresh inode (finish_linked_checkout never rewrites a linked path), so the previous snapshot's
    bytes are never changed through a link."""
    import os
    import subprocess
    from pathlib import Path
    src, die_root = Path(src), Path(die_root)
    prev = []
    for d in die_root.iterdir() if die_root.is_dir() else []:
        ready = d / "source_checkout.ready"
        if d.resolve() != src.parent.resolve() and ready.is_file() and (d / "src" / ".git").exists():
            prev.append((ready.stat().st_mtime, d / "src"))
    if not prev:
        return None, 0
    prev_src = max(prev)[1]
    g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], text=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, check=True).stdout
    prev_sha = subprocess.run(["git", "-C", str(prev_src), "rev-parse", "HEAD"], text=True,
                              stdout=subprocess.PIPE, check=True).stdout.strip()
    changed = set(g("diff", "--no-renames", "--name-only", "-z", prev_sha, tip).split("\0"))
    n = 0
    for rel in g("ls-tree", "-r", "-z", "--name-only", tip, "--", *dirs).split("\0"):
        if not rel or rel in changed:
            continue
        a, b = prev_src / rel, src / rel
        if a.is_symlink() or not a.is_file() or b.exists() or b.is_symlink():
            continue
        b.parent.mkdir(parents=True, exist_ok=True)
        os.link(a, b)
        # Shared inode: read-only in BOTH snapshots, so an in-place write (shell '>', open('w'), a patch tool)
        # fails instead of corrupting every sibling.  git, copy_untracked_inputs and materialize_clock_mesh
        # never write an existing path: git unlinks and writes a fresh inode, the helpers only create new files.
        os.chmod(b, os.stat(b).st_mode & ~0o222)
        n += 1
    return prev_src, n


def finish_linked_checkout(src):
    """Complete a --no-checkout sparse worktree whose unchanged files are already linked in: index = HEAD with the
    sparse bits, then write only the missing in-cone files (never an existing path); the tree must be clean."""
    import subprocess
    from pathlib import Path
    def git(*a, check=True):
        return subprocess.run(["git", "-C", str(src), *a], text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=check).stdout
    git("reset", "-q")
    git("sparse-checkout", "reapply")
    git("update-index", "-q", "--refresh", check=False)
    missing = []
    for row in git("ls-files", "-t", "-z").split("\0"):
        tag, _, rel = row.partition(" ")
        if rel and tag != "S" and not (Path(src) / rel).exists() and not (Path(src) / rel).is_symlink():
            missing.append(rel)
    for i in range(0, len(missing), 500):
        git("checkout-index", "-q", "--", *missing[i:i + 500])
    dirty = git("status", "--porcelain", "--untracked-files=no")
    if dirty.strip():
        raise RuntimeError("delta snapshot checkout not clean: " + dirty[:500])
    return len(missing)


def live_snapshot_refs(ap_dir, cfg, state):
    """Every string that can pin a source snapshot: kit_wave.json, the source-follow state (active override) and
    the spec of each live wave record (RUNNING/WAITING/LAUNCHING, or ENQUEUED unless its queue run FAILED: a
    FAILED queue kit relaunches as a new attempt on the current source), plus PROTECTED-DBS.txt."""
    from pathlib import Path
    # cfg carries runtime-only sets (kit_wave cfg["_near_count"]); serialize them instead of crashing the wave
    # (KW-FIX-1 11-02: "Object of type set is not JSON serializable" on every new main tip since 11-01 21:11)
    dump = lambda o: json.dumps(o, sort_keys=True, default=lambda x: sorted(map(str, x)) if isinstance(x, (set, frozenset)) else str(x))
    refs = [dump(cfg), dump(state.get("source_follow", {}))]
    ap_dir = Path(ap_dir)
    try:
        items = json.loads((ap_dir / "kit_wave_state.json").read_text()).get("items", {})
    except (OSError, ValueError):
        items = None
    if items is None:
        return None                                      # unknown live set: retention must not run
    for v in items.values():
        live = v.get("status") in ("RUNNING", "WAITING", "LAUNCHING") or v.get("enqueue_pending") or (
            v.get("status") == "ENQUEUED" and v.get("q_status") != "FAIL")
        if not live:
            continue
        refs.append(dump(v))
        try:
            refs.append((Path(v["dir"]) / "spec.json").read_text())
        except (OSError, KeyError, TypeError):
            refs.append(str(v.get("dir")))
    for p in (ap_dir.parent / "PROTECTED-DBS.txt",):
        if p.is_file():
            refs.append(p.read_text())
    return refs


def referenced_snapshots(refs, die_root):
    """The <die_root>/<12-hex> snapshot dirs named anywhere in refs (small list for the remote payload);
    None stays None (live set unknown)."""
    if refs is None:
        return None
    pat = re.compile(re.escape(str(die_root).rstrip("/")) + r"/([0-9a-f]{12})(?![\w.-])")
    return sorted({str(die_root).rstrip("/") + "/" + m.group(1) for r in refs for m in pat.finditer(r)})


def prune_snapshots(repo, die_root, refs, current, newest=2, log=print):
    """Retention after a PASSed preparation: keep the newest `newest` complete snapshots, the current one and every
    snapshot whose path any live reference names; remove the rest (worktree remove, then the snapshot dir).
    Only <die_root>/<12-hex> snapshot dirs are candidates.  refs=None (live set unknown) removes nothing."""
    import re
    import shutil
    import subprocess
    from pathlib import Path
    die_root, current = Path(die_root), Path(current)
    if refs is None or not die_root.is_dir():
        return []
    snaps = [d for d in die_root.iterdir() if d.is_dir() and not d.is_symlink() and re.fullmatch(r"[0-9a-f]{12}", d.name)]
    def age(d):
        r = d / "source_checkout.ready"
        return (r if r.is_file() else d).stat().st_mtime
    snaps.sort(key=age, reverse=True)
    keep = set(snaps[:newest]) | {current}
    text = "\n".join(refs)
    removed = []
    for d in snaps:
        if d in keep or d.resolve() == current.resolve() or re.search(re.escape(str(d)) + r"(?![\w.-])", text):
            continue
        src = d / "src"
        if (src / ".git").exists():
            subprocess.run(["git", "-C", str(repo), "worktree", "unlock", str(src)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", "--force", str(src)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(d, ignore_errors=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "prune"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("SOURCE-FOLLOW retention removed unreferenced snapshot " + str(d))
        removed.append(str(d))
    return removed


def same_library_interface(parser, old_source, new_source, scratch):
    """Compare the exact interface stubs used by bind_elab for opaque library files."""
    from pathlib import Path
    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    signatures = []
    for name, text in (("old", old_source), ("new", new_source)):
        source = scratch / (name + ".sv")
        source.write_text(text)
        stub = scratch / (name + ".interface.sv")
        parser.lib_stubs([str(source)], stub)
        signatures.append(parser._strip(stub.read_text()).strip())
    return bool(signatures[0]) and signatures[0] == signatures[1]


def used_hdl_paths(sources, recipe, metadata):
    """Exact elaborator readset plus explicit recipe files; search roots are not inputs."""
    import re
    used = set()
    def walk(value):
        if isinstance(value, dict):
            for item in value.values(): walk(item)
        elif isinstance(value, list):
            for item in value: walk(item)
        elif isinstance(value, str) and value.endswith((".sv", ".v")):
            match = re.search(r"(?:^|/)(rtl|physical|opentools)/(.+)$", value)
            if match: used.add(match.group(1) + "/" + match.group(2))
    walk(sources)
    walk(recipe)
    # These files were actually parsed, including opaque modules whose bodies
    # were replaced by interface stubs. Never drop their interface checks.
    walk(metadata.get("full", []))
    walk(metadata.get("lib", []))
    return used


def rewrite(value, mapping):
    if isinstance(value, dict):
        return {k: rewrite(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [rewrite(v, mapping) for v in value]
    if isinstance(value, str):
        for old, new in sorted(mapping.items(), key=lambda x: -len(x[0])):
            value = value.replace(old, new)
    return value


def apply_ready(cfg, state):
    """Discard an override when the operator changes the configured source."""
    for die, rec in state.get("source_follow", {}).items():
        d = cfg.get("dies", {}).get(die)
        if d and rec.get("base") == d.get("src_sha") and rec.get("ready"):
            d.update(copy.deepcopy(rec["ready"]))


def collect_prepared(AP, cfg, state):
    """Collect the recorded preparation before looking at a potentially newer main tip."""
    for die, rec in state.get("source_follow", {}).items():
        base = cfg.get("dies", {}).get(die) or {}
        if rec.get("base") != base.get("src_sha"):
            continue
        result = rec.get("result")
        if not result and rec.get("unit"):
            # Recover preparations started by versions that recorded only the unit.
            short_tip = rec["unit"].rsplit("-", 1)[-1]
            root = Path(AP.AP_DIR) / "source_follow" / die
            choices = [root / str(rec["base"])[:12] / short_tip / "result.json",
                       root / short_tip / "result.json"]
            result = next((str(p) for p in choices if p.is_file()), None)
        if not result or rec.get("collected") == result or not Path(result).is_file():
            continue
        got = json.loads(Path(result).read_text())
        if got.get("verdict") == "PASS":
            rec["ready"] = got["override"]
            AP.log(f"SOURCE-FOLLOW {die} activated prepared {got['override']['src_sha'][:12]}")
        else:
            AP.log(f"SOURCE-FOLLOW {die} held: {got.get('reason')}")
        rec["collected"] = result


def step(AP, cfg, state):
    original = copy.deepcopy(cfg)
    collect_prepared(AP, cfg, state)
    apply_ready(cfg, state)
    rc, tip, _ = AP.sh(["git", "-C", str(AP.REPO), "rev-parse", "origin/main"])
    if rc:
        return
    tip = tip.strip()
    for die, base in original.get("dies", {}).items():
        opts = base.get("src_follow") or {}
        if not opts.get("enabled"):
            continue
        d = cfg["dies"][die]
        if d.get("src_sha") == tip:
            continue
        rc, changed, _ = AP.sh(["git", "-C", str(AP.REPO), "diff", "--name-only", d.get("src_sha", ""), tip])
        watch = opts.get("watch") or ["tools/die_plan/", "tools/orfs", "physical/common_flow/",
                                       "physical/die_plan/" + die + "/", "physical/asap7", "rtl/"]
        if rc or not any(p.startswith(tuple(watch)) for p in changed.splitlines()):
            continue
        rec = state.setdefault("source_follow", {}).setdefault(die, {})
        if rec.get("base") != base.get("src_sha"):
            rec.clear()
            rec["base"] = base.get("src_sha")
        jd = Path(AP.AP_DIR) / "source_follow" / die / str(base.get("src_sha", "unknown"))[:12] / tip[:12]
        result = jd / "result.json"
        if result.is_file():
            got = json.loads(result.read_text())
            if got.get("verdict") == "PASS":
                rec["ready"] = got["override"]
                d.update(copy.deepcopy(rec["ready"]))
            elif rec.get("reported") != tip:
                AP.log(f"SOURCE-FOLLOW {die} held: {got.get('reason')}")
                rec["reported"] = tip
            continue
        if rec.get("unit") and AP.unit_active(rec["unit"]):
            continue
        if AP.DRY:
            AP.log(f"SOURCE-FOLLOW would prepare {die} {tip[:12]}")
            continue
        jd.mkdir(parents=True, exist_ok=True)
        spec = {"die": die, "tip": tip, "die_config": d, "result": str(result),
                "keep_refs": referenced_snapshots(live_snapshot_refs(AP.AP_DIR, [original, cfg], state),
                                                  Path(opts.get("root", "/srv/opentallas-scratch2/claude/source-follow")) / die)}
        (jd / "spec.json").write_text(json.dumps(spec))
        unit = f"kw-source-{die}-{tip[:12]}"
        if AP.launch_unit(unit, jd / "unit.log", [sys.executable, str(Path(__file__).resolve()), "worker", str(jd / "spec.json")]):
            rec.update(unit=unit, tip=tip, result=str(result))
            AP.log(f"SOURCE-FOLLOW {die} preparing {tip[:12]} in {unit}; previous source remains active")


# Worker runs on the hub, preparation command itself is admitted on the generation host.
REMOTE = r'''
import json, os, pathlib, re, shutil, subprocess, sys
s=json.loads(sys.argv[1]); d=s["die_config"]; opts=d["src_follow"]; tip=s["tip"]
root=pathlib.Path(opts.get("root", "/srv/opentallas-scratch2/claude/source-follow"))/s["die"]/tip[:12]
src=root/"src"; bind=root/"bind"; root.mkdir(parents=True,exist_ok=True)
(root/".keep").write_text("KIT-WAVE source/bind snapshot; preserve while configured or referenced by a live kit\n")
repo=pathlib.Path.home()/"OpenTallas"
def run(cmd,cwd=None):
 p=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(p.stdout,flush=True)
 if p.returncode: raise RuntimeError("command failed: "+str(cmd)+" rc="+str(p.returncode))
 return p.stdout
run(["git","-C",str(repo),"fetch","origin","main"])
created=not src.exists()
if created:
 run(["git","-C",str(repo),"worktree","add","--detach","--no-checkout",str(src),tip])
checkout_ready=root/"source_checkout.ready"
if not checkout_ready.exists():
 # Explicit initialization is required on the fleet Git 2.34; retry incomplete own snapshots.
 run(["git","-C",str(src),"sparse-checkout","init","--cone"])
 cone=["physical","rtl","tools","opentools","schemas","configs","results/token_pass"]
 run(["git","-C",str(src),"sparse-checkout","set",*cone])
 # Delta snapshot (default-on): unchanged files are hard links into the newest previous snapshot.
 prev,linked=link_previous_snapshot(repo,src,tip,cone,root.parent) if opts.get("delta_snapshot",True) else (None,0)
 if linked:
  print("SOURCE_FOLLOW delta snapshot: linked",linked,"unchanged files from",prev,"; wrote",finish_linked_checkout(src),"changed/new",flush=True)
 else:
  run(["git","-C",str(src),"checkout"])
 checkout_ready.write_text(tip+"\n")
 if created: run(["git","-C",str(repo),"worktree","lock",str(src),"--reason","active kit-wave source snapshot"])
else:
 actual=run(["git","-C",str(src),"rev-parse","HEAD"]).strip()
 if actual != tip: raise RuntimeError("immutable source snapshot sha mismatch")
if s.get("history_pack"):
 with open(s["history_pack"],"rb") as stream:
  history_import=subprocess.run(["git","-C",str(src),"index-pack","--stdin"],stdin=stream,
                                text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print("SOURCE_FOLLOW historical input import rc",history_import.returncode,history_import.stdout,flush=True)
oldsrc=d["src"]; mode=(d.get("kit_rtl") or {}).get("mode")
if mode == "script" and s["die"] == "s81":
 script=pathlib.Path(d["kit_rtl"]["script"]).read_text()
 oldbind=re.search(r"^export S81_BIND_OUT=(.+)$",script,re.M).group(1)
 oldab=re.search(r"^export S81_ASBUILT=(.+)$",script,re.M).group(1)
elif mode == "bind" or opts.get("snapshot_kind") == "bind":
 mode="bind"
 oldbind=opts.get("snapshot_bind") or str(pathlib.Path(opts.get("work_root", "/srv/opentallas-scratch2/claude/kit-wave"))/s["die"]/d["event"]/"bind")
 oldab=opts.get("snapshot_asbuilt") or d["kit_rtl"]["asbuilt"]
else:
 raise RuntimeError("source-follow adapter not configured: "+s["die"]+"/"+str(mode))
# A cached elaboration may only be reused if every HDL source is unchanged.
sources=pathlib.Path(oldbind,"bind.f").read_text().splitlines()
changed=set(run(["git","-C",str(repo),"diff","--name-only",d["src_sha"],tip]).splitlines())
old_recipe=json.load(open(oldab))
metadata=json.load(open(pathlib.Path(oldbind)/"asbuilt_sources.json"))
used=used_hdl_paths(sources,old_recipe,metadata)
blocked=changed & used
# Library bodies were never elaborated; compare the actual parser-generated interfaces instead.
def relative_source(f):
 m=re.search(r"(?:^|/)(rtl|physical|opentools)/(.+)$",f)
 return m.group(1)+"/"+m.group(2) if m else f
libraries={relative_source(f) for f in metadata.get("lib", [])}
full={relative_source(f) for f in metadata.get("full", [])}
if blocked & (libraries-full):
 sys.path.insert(0,str(src/"tools/die_plan"))
 import bind_elab as interface_parser
 for rel in sorted(blocked & (libraries-full)):
  old_text=subprocess.check_output(["git","-C",str(repo),"show",d["src_sha"]+":"+rel],text=True)
  new_text=(src/rel).read_text()
  scratch=root/"interface_checks"/str(len(list((root/"interface_checks").glob("*"))) if (root/"interface_checks").exists() else 0)
  if same_library_interface(interface_parser,old_text,new_text,scratch):
   blocked.remove(rel)
   print("SOURCE-FOLLOW opaque library interface unchanged: "+rel,flush=True)
# A changed elaborated source needs a fresh die elaboration (bind.py elab) in this snapshot instead of the cached
# graph (KW-FIX-1 11-02, default-on; src_follow.fresh_elab false restores the hold).
fresh_elab=bool(blocked) and opts.get("fresh_elab",True) is not False
if blocked and not fresh_elab:
 raise RuntimeError("cached elaboration source changed; fresh die elaboration required: "+", ".join(sorted(blocked)))
if fresh_elab:
 print("SOURCE-FOLLOW fresh die elaboration: changed elaborated sources "+", ".join(sorted(blocked)),flush=True)
 if bind.exists() and not (bind/"asbuilt.json").exists(): shutil.rmtree(bind)
 bind.mkdir(parents=True,exist_ok=True)
elif not bind.exists(): run(["cp","-a","--reflink=auto",oldbind,str(bind)])
# Rebase both compiled structural files and canonical repository sources.
old_struct=set()
for f in sources:
 for folder in ("/structural_full/","/structural_tops/","/parameterized_interfaces/"):
  if folder in f: old_struct.add(f.split(folder)[0])
mapping={oldsrc:str(src),oldbind:str(bind)}
for prefix in old_struct: mapping[prefix]=str(bind)
# S81 bind12 is a hard-linked copy, but bind.f still names the original out/rtl tree.
for f in sources:
 if "/out/" in f:
  prefix, rel=f.rsplit("/out/",1)
  candidate=pathlib.Path(oldbind)/rel
  original=pathlib.Path(f)
  if candidate.is_file() and original.is_file() and (os.path.samefile(candidate,original) or candidate.read_bytes()==original.read_bytes()):
   mapping[prefix+"/out"]=str(bind)
for f in sources:
 m=re.match(r"(.*/wt/[^/]+)/(rtl|physical|opentools)/",f)
 if m: mapping[m.group(1)]=str(src)
def rw(v):
 if isinstance(v,dict): return {k:rw(x) for k,x in v.items()}
 if isinstance(v,list): return [rw(x) for x in v]
 if isinstance(v,str):
  for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])): v=v.replace(a,b)
 return v
ab=rw(old_recipe); ab["base"]=str(src)
# Cached source helper files absent from Git belong to the snapshot too.
for f in sources:
 nf=rw(f)
 if nf.startswith(str(src)+"/") and not pathlib.Path(nf).exists() and pathlib.Path(f).is_file():
  pathlib.Path(nf).parent.mkdir(parents=True,exist_ok=True); shutil.copy2(f,nf)
# Sparse source snapshots include recipe data such as token proof and cell semantics.
extra=set()
def paths(v):
 if isinstance(v,dict):
  for x in v.values(): paths(x)
 elif isinstance(v,list):
  for x in v: paths(x)
 elif isinstance(v,str):
  rel=v[len(str(src))+1:] if v.startswith(str(src)+"/") else v
  if rel.startswith(("results/", "docs/")): extra.add(str(pathlib.Path(rel).parent))
paths(ab)
if extra: run(["git","-C",str(src),"sparse-checkout","add",*sorted(extra)])
recipe=root/"asbuilt.json"; recipe.write_text(json.dumps(ab,indent=1))
# The copied generated assemblies preserve their bytes; only source-path receipts are rebased.
for name in ("bind.f","asbuilt_sources.json","provenance_elab.json"):
 p=bind/name
 if p.exists():
  t=p.read_text()
  for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])): t=t.replace(a,b)
  p.write_text(t)
plan=pathlib.Path(str(d["plan"]).replace(oldsrc,str(src)))
print("SOURCE_FOLLOW untracked inputs copied:",copy_untracked_inputs(oldsrc,src),flush=True)
materialize_clock_mesh(src,plan,lambda obj: subprocess.check_output(["git","-C",str(repo),"show",obj]))
if fresh_elab and not (bind/"asbuilt.json").exists():
 run([sys.executable,"tools/die_plan/bind.py","elab",str(plan),"--out",str(bind),"--asbuilt",str(recipe),"--mem",str(int(opts.get("elab_mem_gb",12)))],cwd=src)
run([sys.executable,"tools/die_plan/bind.py","bind",str(plan),"--out",str(bind),"--asbuilt",str(recipe),"--strict"],cwd=src)
r=json.load(open(bind/"bind_report.json")); errors=r.get("errors")
if errors: raise RuntimeError("strict bind errors: "+str(errors)[:500])
# bind.py can rewrite source receipts; normalize those once more to the immutable source.
p=bind/"bind.f"; text=p.read_text()
for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])): text=text.replace(a,b)
p.write_text(text)
missing=[f for f in text.splitlines() if f.strip() and not pathlib.Path(f).is_file()]
if missing: raise RuntimeError("source closure missing: "+str(missing[:5]))
kit=root/"kit_rtl.sh"
if mode == "script":
 kit.write_text("#!/bin/bash\nexport S81_BIND_OUT="+str(bind)+"\nexport S81_ASBUILT="+str(recipe)+"\nexec bash \"$PWD/physical/die_plan/s81/kit_wave/kit_rtl.sh\"\n")
else:
 import shlex
 kit.write_text("#!/bin/bash\nset -euo pipefail\npython3 -I tools/die_plan/bind.py kit-rtl \"$PLAN\" --out "+shlex.quote(str(bind))+" --asbuilt "+shlex.quote(str(recipe))+" --type \"$TYPE\" --kit \"$OUT\"\n")
override={"src":str(src),"src_sha":tip,"plan":str(plan),"event":tip if s["die"]=="s81" else d["event"],"kit_rtl":dict(d["kit_rtl"],mode="script",script=str(kit))}
override["src_follow"]=dict(opts,snapshot_kind=mode,snapshot_bind=str(bind),snapshot_asbuilt=str(recipe))
if fresh_elab: override["src_follow"]["fresh_elaboration"]=tip
# Retention (default-on): newest 2 + this one + every snapshot a live record or the config names.
if opts.get("retention",True):
 try: prune_snapshots(repo,root.parent,s.get("keep_refs"),root,int(opts.get("keep_newest",2)),log=lambda m: print(m,flush=True))
 except Exception as e: print("SOURCE-FOLLOW retention skipped: "+repr(e)[:300],flush=True)
print("AP_JSON "+json.dumps({"verdict":"PASS","override":override}),flush=True)
'''


def stage_history_inputs(repo, tip, output, host, remote_dir):
    """Carry declared historical inputs with a source snapshot; availability stays advisory.

    Build on the hub, whose object store holds historical non-main source pins.
    Sparse/main-only fleet clones need not fetch entire unrelated histories.
    """
    import importlib.util
    helper = Path(__file__).with_name("source_history.py")
    loader = importlib.util.spec_from_file_location("source_history", helper)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    report = module.pack_history(repo, repo, output, revision=tip)
    if report["pack"]:
        target = str(Path(remote_dir) / Path(report["pack"]).name)
        temporary = target + ".%d.tmp" % os.getpid()
        # Never overwrite a pack another preparation may already be importing.
        command = "cat > {t} && (ln {t} {d} 2>/dev/null || test -f {d}) && rm {t}".format(
            t=shlex.quote(temporary), d=shlex.quote(target))
        with Path(report["pack"]).open("rb") as stream:
            subprocess.run(["ssh", "-o", "ControlPath=none", host, command], stdin=stream, check=True)
        report["remote_pack"] = target
    return report


def worker(spec_path):
    spec = json.loads(Path(spec_path).read_text())
    result = Path(spec["result"])
    host = spec["die_config"]["gen_host"]
    # ot-run owns the entire snapshot/bind operation and its RAM request.
    q = shlex.quote
    remote_dir = str(Path(spec["die_config"].get("src_follow",{}).get("root","/srv/opentallas-scratch2/claude/source-follow"))/spec["die"]/spec["tip"][:12])
    subprocess.run(["ssh", "-o", "ControlPath=none", host, "mkdir", "-p", remote_dir], check=True)
    try:
        history = stage_history_inputs(Path(__file__).resolve().parents[2], spec["tip"],
                                       result.parent / "source_history", host, remote_dir)
        spec["history_pack"] = history.get("remote_pack")
        print("SOURCE-FOLLOW historical inputs " + json.dumps(history), flush=True)
    except Exception as error:
        # No new release gate: the existing strict bind and the requested kit's real inputs still decide.
        print("SOURCE-FOLLOW historical input preparation unavailable: " + str(error), flush=True)
    payload = "python3 -I - " + q(json.dumps(spec)) + " <<'SOURCE_FOLLOW_PY'\n" + inspect.getsource(materialize_clock_mesh) + "\n" + inspect.getsource(copy_untracked_inputs) + "\n" + inspect.getsource(link_previous_snapshot) + "\n" + inspect.getsource(finish_linked_checkout) + "\n" + inspect.getsource(prune_snapshots) + "\n" + inspect.getsource(same_library_interface) + "\n" + inspect.getsource(used_hdl_paths) + "\n" + REMOTE + "\nSOURCE_FOLLOW_PY\n"
    cmd = [str(Path.home()/".local/bin/ot-run"), "--hosts", host, "--mem", str(spec["die_config"].get("bind_mem_gb", 24)),
           "--threads", "2", "--dir", str(Path(spec["die_config"].get("src_follow",{}).get("root","/srv/opentallas-scratch2/claude/source-follow"))/spec["die"]/spec["tip"][:12]),
           "--", "bash", "-lc", payload]
    if spec["die_config"].get("src_follow", {}).get("critical"):
        cmd.insert(1, "--crit")
    p = subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(p.stdout,flush=True)
    got = {"verdict":"FAIL","reason":f"source preparation rc {p.returncode}: {p.stdout[-1200:]}"}
    for line in reversed(p.stdout.splitlines()):
        if line.startswith("AP_JSON "):
            got=json.loads(line[8:]); break
    tmp=result.with_suffix(".tmp")
    tmp.write_text(json.dumps(got,indent=1)); os.replace(tmp,result)


if __name__ == "__main__":
    if sys.argv[1:2] == ["worker"]: worker(sys.argv[2])
