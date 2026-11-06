#!/usr/bin/env python3
"""AUTOBUILD-PIPE-2 10-31 (COORD 02:2x): KV hard cores in the kit wave (tools/autopilot/kit_wave.py core_kit mode).

    views: python3 kv_core_wave.py views --plan PLAN --out VIEWS [--core-root DIR ...]
    gen:   python3 kv_core_wave.py gen --views VIEWS --view MODULE@SHA12 --out OUT [--kit-rtl auto|DIR] [--fp-root DIR ...]
                                  [gen_core_kit_kv.py args ...]

views lists every planned hard core of the KV plan of record (partition_types[*].hard_cores with a pins_file and no
lef/lib view) as one view per (module, plan pin table): view = '<module>@<sha256(pins_file)[:12]>', the same key the
kit_wave plan probe (core_views) uses, so the core_kit picker selects exactly one view per wave item.  A module whose
core RTL json (<root>/<module>/<module>_core.json, kv_core_rtl.py output; default root results/kv_host_regen_1/rtl)
is not found has no view (picker: CORE_VIEW FAIL ... 0 views = PLAN, core RTL owner) and is listed in no_recipe.

gen = the KV-HOST-KITS-2 recipe (results/kv_host_regen_1/gen_kit.sh) without hand steps:
  * core json source paths that point into removed lane worktrees (/.../wt/<name>/<repo path>) are re-pointed to the
    same repo path in this checkout (fail closed if absent); the re-pointed json is written next to the kit;
  * qkd_hr_* cores need their PASS face proof (hr_face_ports.sh: post rc=0 / mut rc=1 / emitted_v rc=0) from one of
    --fp-root; none -> 'NO_RECIPE <module>: no PASS hr face proof' (PLAN class: the proof run is the core owner's);
  * --kit-rtl auto (default): the gen reads only kit_rtl.json hard_macros; they are derived from the core json memory
    black boxes (<dir>/<m>_bb.v -> <dir>/<m>.lef + <m>_*.lib in this checkout), so no lane kit_rtl dir is needed;
  * gen_core_kit_kv.py --core-json J --plan PLAN --out OUT --kit-rtl DIR --util 0.6 --sigmax M5
    [--hr-face-ports FP --plan-inst INST] + extra args (last wins); kit = OUT/<module>__<w>x<h>/freeze.json.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hr_dead_inputs  # noqa: E402
REPO = HERE.parents[4]
CORE_ROOT_DEFAULT = "results/kv_host_regen_1/rtl"
CORE_ROOT_NATIVE_EX = "results/kv_hg_ex_1101"
FP_PASS = ["post", "rc=0", "mut", "rc=1", "emitted_v", "rc=0"]


def sha12(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def plan_views(plan_path, roots):
    plan = json.load(open(plan_path))
    pdir = Path(plan_path).resolve().parent
    by = {}
    for t, v in sorted((plan.get("partition_types") or {}).items()):
        for c in (v.get("hard_cores") or []) if isinstance(v, dict) else []:
            if not isinstance(c, dict) or not c.get("module") or not c.get("pins_file") or c.get("lef") or c.get("lib"):
                continue
            pf = pdir / c["pins_file"]
            key = (c["module"], sha12(pf) if pf.is_file() else "missing")
            e = by.setdefault(key, dict(module=c["module"], view=f"{key[0]}@{key[1]}", type=t, pins_file=str(pf),
                                        insts=[]))
            e["insts"].append(c["inst"])
    views, none = [], []
    for (m, s), e in sorted(by.items()):
        cj = next((Path(r) / m / f"{m}_core.json" for r in roots if (Path(r) / m / f"{m}_core.json").is_file()), None)
        if cj is None or s == "missing":
            none.append(dict(module=m, why="pins file missing" if s == "missing" else "no core json under " + ",".join(roots)))
            continue
        views.append(dict(e, core_json=str(cj.resolve()), hr=m.startswith("qkd_hr_")))
    return dict(schema="opentallas.kv.core_views.v1", plan=str(Path(plan_path).resolve()), plan_sha256=hashlib.sha256(
        Path(plan_path).read_bytes()).hexdigest(), core_roots=list(roots), view_list=views, no_recipe=none)


def repoint(f, repo, cj_dir):
    """core json source -> an existing path: as is, the core json's own dir (wrapper), or the repo path of a removed
    lane worktree (/.../wt/<name>/<repo path>)"""
    p = Path(f)
    if not p.is_absolute():
        p = repo / p
    if p.is_file():
        return str(p)
    if (cj_dir / p.name).is_file():
        return str(cj_dir / p.name)
    m = re.match(r"^/.*?/wt/[^/]+/(.+)$", f)
    if m and (repo / m.group(1)).is_file():
        return str(repo / m.group(1))
    # The host-core extraction records two generated inputs outside a worktree.  Their
    # committed recovery paths are explicit, so unrelated basename matches stay rejected.
    recovered = {
        "/kv-kits-7-1027/b3/rtl/bind_cells.sv":
            "results/kv_host_regen_1/rtl/qkd_kvs_ctl/bind_cells.sv",
        "/kv-host-regen-1/kit_rtl_b3/kv3_hub_Wi/inline/qkd_embgw_boot_s.sv":
            "results/kv_host_regen_1/recovered/inline/qkd_embgw_boot_s.sv",
    }
    for suffix, relative in recovered.items():
        candidate = repo / relative
        if str(f).endswith(suffix) and candidate.is_file():
            return str(candidate)
    return None


def macro_views(files):
    """memory macro black boxes (<dir>/<m>_bb.v) of the core sources -> kit_rtl.json hard_macros {m: {dir, lef, libs,
    bb, model}} from the repo macro view next to each (the gen copies lef + libs of the macros the core reaches)"""
    hm, miss = {}, []
    for f in files:
        p = Path(f)
        if not p.name.endswith("_bb.v"):
            continue
        m, d = p.name[:-5], p.parent
        libs = sorted(str(x) for x in d.glob(f"{m}_*.lib"))
        if not (d / f"{m}.lef").is_file() or not libs:
            miss.append(f)
            continue
        hm[m] = dict(dir=str(d), lef=str(d / f"{m}.lef"), libs=libs, bb=str(p), model=str(d / f"{m}.v"))
    return hm, miss


def module_recipe(module):
    """Planned masters use their established face/clock and hardened-child recipes."""
    if module == "qkd_astk_ex_s":
        # Exact native F policy: synthesis EQ; route/final-netlist EQ remain separate release gates.
        return ["--recipes", str(HERE / "qkd_astk_ex_s_recipe.json"),
                "--cts-setup-only", "--two-mode-grt", "--hold-ff-margin", "10"]
    if module in ("ot_qwen_tp8_pv_join_t", "kv3_pv_pair"):
        # Native TT setup / FF hold sessions, including guarded normal GRT.
        return ["--cts-setup-only", "--two-mode-grt", "--hold-ff-margin", "10"]
    if module == "kv3_astk":
        # DIE-KV-61 11-02: native strap master face recut (CORE_PREFLIGHT dropped 60 / shared 17 / unregistered 1
        # without it) + the native TT setup / FF hold sessions.
        return ["--astk-native-faces", "--cts-setup-only", "--two-mode-grt", "--hold-ff-margin", "10"]
    if module in ("qkd_kvs_pc", "qkd_kvs_pc_h_head_p"):
        return ["--kvspc-face-ports", "--kvspc-private-ports", "--kvspc-core-clock"]
    if module == "qkd_ahub":
        return ["--am-g-drop", "--hard-children", str(HERE / "qkd_ahub_hard_children.json"),
                "--cts-setup-only", "--two-mode-grt", "--hold-ff-margin", "10"]
    return []


def memory_blackbox_sources(files):
    """Use a complete compiled SRAM package for synthesis, retaining its model for simulation."""
    sources, substitutions = [], []
    for name in files:
        p = Path(name)
        bb = p.with_name(p.stem + "_bb.v")
        memory_dir = any(x in ("asap7_memory_macros", "asap7_memory_macros_v2") for x in p.parts)
        if memory_dir and p.suffix == ".v" and not p.name.endswith("_bb.v") and bb.is_file() \
                and (p.parent / (p.stem + ".lef")).is_file() \
                and (p.parent / (p.stem + "_tt.lib")).is_file() \
                and (p.parent / (p.stem + "_ff.lib")).is_file():
            sources.append(str(bb))
            substitutions.append(dict(model=str(p), bb=str(bb)))
        else:
            sources.append(name)
    return sources, substitutions


def plan_slot_for_view(cj, view, plan_path):
    """(type, inst) of this pin table: the core's own type first (a repeated instance name in another type is not an
    alias); when that type has no slot with this pin table, the type the view itself was found in (views: plan_views
    'type'), e.g. a pin variant planned only in a sibling partition type (KV pv_join R0 table only in kv3_pv_v*n)."""
    plan_path = Path(plan_path)
    plan = json.loads(plan_path.read_text())
    wanted = view["view"].rsplit("@", 1)[-1]
    types = [cj["type"]] + ([view["type"]] if view.get("type") and view["type"] != cj["type"] else [])
    for t in types:
        matches = []
        for c in plan.get("partition_types", {}).get(t, {}).get("hard_cores", []):
            if c.get("module") != cj["module"] or not c.get("pins_file"):
                continue
            pins = plan_path.parent / c["pins_file"]
            if pins.is_file() and sha12(pins) == wanted:
                matches.append(c["inst"])
        if matches:
            return t, (cj.get("inst") if cj.get("inst") in matches else matches[0])
    sys.exit(f"NO_RECIPE {cj['module']}: requested pin view {wanted} has no slot in core type {' or '.join(types)}")


def plan_inst_for_view(cj, view, plan_path):
    """Select this pin table in the core's actual type, not an alias in another type."""
    return plan_slot_for_view(cj, view, plan_path)[1]


def gen(a, extra):
    v = json.load(open(a.views))
    e = next((x for x in v.get("view_list") or [] if x["view"] == a.view), None)
    if e is None:
        sys.exit(f"CORE_VIEW FAIL {a.view}: not in {a.views}")
    m = e["module"]
    cjp = Path(e["core_json"])
    cj = json.load(open(cjp))
    if cj.get("module") != m:
        sys.exit(f"NO_RECIPE {m}: core json {cjp} is module {cj.get('module')}")
    slot_type, inst = plan_slot_for_view(cj, e, a.plan or v["plan"])
    if slot_type != cj["type"]:
        cj = dict(cj, type=slot_type, inst=inst)
    repo = Path(a.repo).resolve()
    files, bad = [], []
    for f in cj["files"]:
        r = repoint(f, repo, cjp.parent)
        (files.append(r) if r else bad.append(f))
    if bad:
        sys.exit(f"NO_RECIPE {m}: {len(bad)} core json sources not found (first {bad[0]})")
    files, memory_substitutions = memory_blackbox_sources(files)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cj2 = dict(cj, files=files, kv_core_wave=dict(src_core_json=str(cjp), view=a.view, repointed=sum(
        f != g for f, g in zip(cj["files"], files)), memory_substitutions=memory_substitutions))
    cjw = out / f"_{m}_core.json"
    if m == "qkd_ahub":
        import ahub_clock7
        cj2 = ahub_clock7.prepare(cj2, out / "_ahub_clock7")
        files = cj2["files"]
    cjw.write_text(json.dumps(cj2, indent=1) + "\n")
    kit_rtl = a.kit_rtl
    if kit_rtl == "auto":
        hm, miss = macro_views(files)
        if miss:
            sys.exit(f"NO_RECIPE {m}: memory macro view (lef/lib) missing next to {miss[0]}")
        kit_rtl = str(out / "_kit_rtl")
        (out / "_kit_rtl" / cj["type"]).mkdir(parents=True, exist_ok=True)
        (out / "_kit_rtl" / cj["type"] / "kit_rtl.json").write_text(json.dumps(dict(
            schema="opentallas.kv.core_wave_kit_rtl.v1", note="hard_macros from the core json black boxes (repo views)",
            hard_macros=hm), indent=1) + "\n")
    cmd = [sys.executable, str(HERE / "gen_core_kit_kv.py"), "--core-json", str(cjw), "--plan", a.plan or v["plan"],
           "--out", str(out), "--kit-rtl", kit_rtl, "--tool", str(repo / "tools/die_plan")]
    # Leave physical defaults to the recipe/generator. Only the caller's extra flags
    # below are explicit overrides; injecting .6/M5 here would now override the recipe.
    fp = None
    if e.get("hr"):
        for r in a.fp_root:
            d = Path(r) / m
            if (d / "eq_rc.txt").is_file() and (a.face_proof_pending or hr_dead_inputs.proof_state(d, m) in ("pass", "named")) \
                    and (d / f"{m}.v").is_file() and (d / "hr_face_ports.json").is_file():
                fp = d
                break
        if fp is None:
            sys.exit(f"NO_RECIPE {m}: no PASS hr face proof under {','.join(a.fp_root) or '(no --fp-root)'} "
                     f"(hr_face_ports.sh; results/kv_host_regen_1/fp_core.sh {m})")
        cmd += ["--hr-face-ports", str(fp)] + (["--hr-face-proof-pending"] if a.face_proof_pending else [])
    cmd += module_recipe(m) + ["--plan-inst", inst] + list(extra)
    (out / "kv_core_wave.json").write_text(json.dumps(dict(view=a.view, module=m, core_json=str(cjw), face_proof=str(
        fp) if fp else None, face_proof_sha=hashlib.sha256((fp / "hr_face_ports.json").read_bytes()).hexdigest()[:16]
        if fp else None, cmd=cmd), indent=1) + "\n")
    print("KV_CORE_WAVE", " ".join(cmd), flush=True)
    return subprocess.run(cmd).returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("views")
    pv.add_argument("--plan", required=True)
    pv.add_argument("--out", required=True)
    pv.add_argument("--core-root", action="append", default=[])
    pg = sub.add_parser("gen")
    pg.add_argument("--views", required=True)
    pg.add_argument("--view", required=True)
    pg.add_argument("--out", required=True)
    pg.add_argument("--plan")
    pg.add_argument("--kit-rtl", default="auto", help="kit_rtl dir (<type>/kit_rtl.json) or auto: hard_macros "
                    "from the core json memory black boxes (repo macro views)")
    pg.add_argument("--fp-root", action="append", default=[])
    pg.add_argument("--face-proof-pending", action="store_true",
                    help="opt-in: accept a face proof dir whose proof has not returned (kit records face_proof pending)")
    pg.add_argument("--repo", default=str(REPO))
    a, extra = ap.parse_known_args(argv)
    if a.cmd == "views":
        if extra:
            ap.error(f"unknown args {extra}")
        roots = a.core_root or [str(REPO / CORE_ROOT_DEFAULT), str(REPO / CORE_ROOT_NATIVE_EX)]
        v = plan_views(a.plan, roots)
        Path(a.out).write_text(json.dumps(v, indent=1) + "\n")
        print(f"KV_CORE_VIEWS {len(v['view_list'])} views, {len(v['no_recipe'])} no_recipe: "
              + " ".join(x["module"] for x in v["no_recipe"]))
        return 0
    return gen(a, extra)


if __name__ == "__main__":
    sys.exit(main())
