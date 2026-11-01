#!/usr/bin/env python3
"""Prepare immutable kit-wave sources; only strict-bind-clean candidates become active.

The timer starts a preparation unit and keeps launching from its previous source.
No config file or existing source/bind tree is modified. State owns the override.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


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


def step(AP, cfg, state):
    original = copy.deepcopy(cfg)
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
        spec = {"die": die, "tip": tip, "die_config": d, "result": str(result)}
        (jd / "spec.json").write_text(json.dumps(spec))
        unit = f"kw-source-{die}-{tip[:12]}"
        if AP.launch_unit(unit, jd / "unit.log", [sys.executable, str(Path(__file__).resolve()), "worker", str(jd / "spec.json")]):
            rec["unit"] = unit
            AP.log(f"SOURCE-FOLLOW {die} preparing {tip[:12]} in {unit}; previous source remains active")


# Worker runs on the hub, preparation command itself is admitted on the generation host.
REMOTE = r'''
import json, os, pathlib, re, shutil, subprocess, sys
s=json.loads(sys.argv[1]); d=s["die_config"]; opts=d["src_follow"]; tip=s["tip"]
root=pathlib.Path(opts.get("root", "/srv/opentallas-scratch2/claude/source-follow"))/s["die"]/tip[:12]
src=root/"src"; bind=root/"bind"; root.mkdir(parents=True,exist_ok=True)
repo=pathlib.Path.home()/"OpenTallas"
def run(cmd,cwd=None):
 p=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(p.stdout,flush=True)
 if p.returncode: raise RuntimeError("command failed: "+str(cmd)+" rc="+str(p.returncode))
 return p.stdout
run(["git","-C",str(repo),"fetch","origin","main"])
if not src.exists():
 run(["git","-C",str(repo),"worktree","add","--detach","--no-checkout",str(src),tip])
 run(["git","-C",str(src),"sparse-checkout","set","physical","rtl","tools","opentools","schemas","configs","results/token_pass"])
 run(["git","-C",str(src),"checkout"])
 run(["git","-C",str(repo),"worktree","lock",str(src),"--reason","active kit-wave source snapshot"])
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
used=set()
for f in sources:
 m=re.search(r"/(rtl|physical|opentools)/(.+)$",f)
 if m: used.add(m.group(1)+"/"+m.group(2))
if changed & used:
 raise RuntimeError("cached elaboration source changed; fresh die elaboration required: "+", ".join(sorted(changed&used)))
if not bind.exists(): run(["cp","-a","--reflink=auto",oldbind,str(bind)])
# Rebase both compiled structural files and canonical repository sources.
old_struct=set()
for f in sources:
 for folder in ("/structural_full/","/structural_tops/","/parameterized_interfaces/"):
  if folder in f: old_struct.add(f.split(folder)[0])
mapping={oldsrc:str(src),oldbind:str(bind)}
for prefix in old_struct: mapping[prefix]=str(bind)
for f in sources:
 m=re.match(r"(.*/wt/[^/]+)/(rtl|physical|opentools)/",f)
 if m: mapping[m.group(1)]=str(src)
def rw(v):
 if isinstance(v,dict): return {k:rw(x) for k,x in v.items()}
 if isinstance(v,list): return [rw(x) for x in v]
 if isinstance(v,str):
  for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])): v=v.replace(a,b)
 return v
old_recipe=json.load(open(oldab)); ab=rw(old_recipe); ab["base"]=str(src)
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
print("AP_JSON "+json.dumps({"verdict":"PASS","override":override}),flush=True)
'''


def worker(spec_path):
    spec = json.loads(Path(spec_path).read_text())
    result = Path(spec["result"])
    host = spec["die_config"]["gen_host"]
    # ot-run owns the entire snapshot/bind operation and its RAM request.
    q = shlex.quote
    payload = "python3 -I - " + q(json.dumps(spec)) + " <<'SOURCE_FOLLOW_PY'\n" + REMOTE + "\nSOURCE_FOLLOW_PY\n"
    remote_dir = str(Path(spec["die_config"].get("src_follow",{}).get("root","/srv/opentallas-scratch2/claude/source-follow"))/spec["die"]/spec["tip"][:12])
    subprocess.run(["ssh", "-o", "ControlPath=none", host, "mkdir", "-p", remote_dir], check=True)
    cmd = [str(Path.home()/".local/bin/ot-run"), "--hosts", host, "--mem", str(spec["die_config"].get("bind_mem_gb", 24)),
           "--threads", "2", "--dir", str(Path(spec["die_config"].get("src_follow",{}).get("root","/srv/opentallas-scratch2/claude/source-follow"))/spec["die"]/spec["tip"][:12]),
           "--", "bash", "-lc", payload]
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
