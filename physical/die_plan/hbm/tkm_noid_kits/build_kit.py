#!/usr/bin/env python3
"""TKM no-ID tile kits (common 31x / terminal 1x) built ONLY from repo-relative inputs (closure order rule 3).

  build_kit.py import OLD_COMMON OLD_TERMINAL OLD_CLOCK   one-off: record the reviewed kits' bytes as repo sources
  build_kit.py build {common|terminal} OUT [--clock]      materialise a kit from this commit (clean tree required)
  build_kit.py receipts {common|terminal} KIT             copy the committed source_receipts into KIT, re-hash

Every kit file comes from manifest.json: kit path -> repo-relative source path + sha256.  Files that already exist in
the repo with identical bytes (tools/die_plan, physical/die_plan/hbm_arch_cores, physical/common_flow, rtl/) are
referenced there; the rest (kit data: pins/io/sdc/config/face_shell, frozen helper versions) live under this directory.
freeze.json names source_commit + repo-relative plan / pins / rtl paths; kit_hash = gen_core_kit_hbm.kit_hash rule
(tree minus run/ views/ freeze.json run_*).  No absolute path is read at build time except OUT.
"""
import argparse, gzip, hashlib, json, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
REL = HERE.relative_to(REPO).as_posix()
MAN = HERE / "manifest.json"
REF_DIRS = ("tools/die_plan/", "physical/die_plan/hbm_arch_cores/", "physical/common_flow/", "rtl/")
CLOCK_FILES = ("hbm_clock_entry.tcl", "shallow_clock.py", "shallow_clock.tcl", "pre_cts_tkm_clock.tcl",
               "post_cts_tkm_clock.tcl", "clock_candidate.json")
VIEWS = {"common": "ot_hgi_coll_tkm_tp192_tile_core__idpin__strap",
         "terminal": "ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap"}


def sha(b): return hashlib.sha256(b).hexdigest()
def git(*a): return subprocess.run(["git", "-C", str(REPO), *a], check=True, capture_output=True, text=True).stdout
def save(p, j): Path(p).write_text(json.dumps(j, indent=1, sort_keys=False) + "\n")


def kit_hash(kd):
    kd = Path(kd); h = hashlib.sha256()
    for f in sorted(p for p in kd.rglob("*") if p.is_file() and p.relative_to(kd).parts[0] not in ("run", "views")
                    and p.name != "freeze.json" and not p.name.startswith("run_")):
        h.update(str(f.relative_to(kd)).encode() + b"\0" + f.read_bytes())
    return h.hexdigest()[:16]


def repo_index():
    idx = {}
    for ln in git("ls-files", "-s").splitlines():
        meta, path = ln.split("\t", 1)
        if path.startswith(REF_DIRS) and not path.startswith(REL + "/"):
            p = REPO / path
            if p.is_file():
                idx.setdefault(sha(p.read_bytes()), path)
    return idx


def kit_files(k):
    k = Path(k)
    return sorted(p.relative_to(k).as_posix() for p in k.rglob("*") if p.is_file()
                  and p.relative_to(k).parts[0] not in ("run", "views", "source_receipts", "lec", "signoff")
                  and p.name != "freeze.json" and not p.name.startswith("run_tkm_clock") and p.name not in CLOCK_FILES
                  and not p.name.endswith(".log") and p.name != "DIAGNOSTIC_ONLY")


def do_import(a):
    idx = repo_index(); old = {"common": Path(a.common), "terminal": Path(a.terminal)}; clk = Path(a.clock)
    man = {"schema": "opentallas.tkm_noid_kit_src.v1", "kits": {}, "clock_stage": {}}
    byname = {}
    for kind, k in old.items():
        for f in kit_files(k):
            byname.setdefault(f, {})[kind] = (k / f).read_bytes()
    for kind, k in old.items():
        files = {}
        for f in kit_files(k):
            b = (k / f).read_bytes(); h = sha(b)
            if h in idx:
                src = idx[h]
            else:
                shared = len(byname[f]) == 2 and len({sha(x) for x in byname[f].values()}) == 1
                src = f"{REL}/{'shared' if shared else kind}/{f}"
                (REPO / src).parent.mkdir(parents=True, exist_ok=True); (REPO / src).write_bytes(b)
            files[f] = {"path": src, "sha256": h}
        fz = json.load(open(k / "freeze.json"))
        assert fz["module"] == VIEWS[kind], (kind, fz["module"])
        tmpl = {x: y for x, y in fz.items() if x not in ("kit_hash", "plan", "pins_file", "rtl_overrides")}
        save(HERE / kind / "freeze_base.json", tmpl)
        man["kits"][kind] = {"view": VIEWS[kind], "freeze_base": f"{REL}/{kind}/freeze_base.json",
                             "imported_kit_hash": fz["kit_hash"], "imported_tree_hash": kit_hash(k), "files": files,
                             "plan_sha256": fz["plan_sha256"], "pins_sha256": fz["pins_sha256"]}
    # clock stage = the CP1 stage files of the reviewed common clock kit (Codex codex/hbm-clock-1713@205f1ef43f)
    cfz = json.load(open(clk / "freeze.json")); files = {}
    for f in CLOCK_FILES:
        b = (clk / f).read_bytes(); h = sha(b)
        src = idx.get(h) or f"{REL}/clock/{f}"
        if src.startswith(REL):
            (REPO / src).parent.mkdir(parents=True, exist_ok=True); (REPO / src).write_bytes(b)
        files[f] = {"path": src, "sha256": h}
    base = (old["common"] / "config.mk").read_text(); full = (clk / "config.mk").read_text()
    assert full.startswith(base); (HERE / "clock").mkdir(exist_ok=True); (HERE / "clock/config_append.mk").write_text(full[len(base):])
    man["clock_stage"] = {"files": files, "config_append": f"{REL}/clock/config_append.mk",
                          "config_append_sha256": sha(full[len(base):].encode()),
                          "freeze_clock_candidate": {x: y for x, y in cfz["clock_candidate"].items()
                                                     if x not in ("source_kit", "source_kit_hash")},
                          "imported_clock_kit_hash": cfz["kit_hash"]}
    # plan: provenance only (no kit step reads it); committed gzip, sha256 of the uncompressed bytes
    pb = gzip.open(HERE / "plan/plan4_die_plan.json.gz").read()
    assert sha(pb) == man["kits"]["common"]["plan_sha256"] == man["kits"]["terminal"]["plan_sha256"]
    man["plan"] = {"path": f"{REL}/plan/plan4_die_plan.json.gz", "sha256_uncompressed": sha(pb)}
    save(MAN, man); print("manifest", MAN, {k: len(v["files"]) for k, v in man["kits"].items()})


def clean_head(paths):
    dirty = git("status", "--porcelain", "--", *paths)
    if dirty.strip():
        raise SystemExit("NOT BUILT: uncommitted changes in kit sources:\n" + dirty)
    return git("rev-parse", "HEAD").strip()


def place(entry, dst):
    src = REPO / entry["path"]
    if entry.get("source_commit"):
        b = subprocess.run(["git", "-C", str(REPO), "show", entry["source_commit"] + ":" + entry["path"]],
                           check=True, capture_output=True).stdout
    else:
        b = src.read_bytes()
    if sha(b) != entry["sha256"]:
        raise SystemExit(f"NOT BUILT: {entry['path']} sha {sha(b)[:12]} != manifest {entry['sha256'][:12]}")
    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(b)


def do_build(a):
    man = json.load(open(MAN)); m = man["kits"][a.kind]; cs = man["clock_stage"]
    paths = sorted({e["path"] for e in m["files"].values()} | {m["freeze_base"], man["plan"]["path"], REL + "/build_kit.py", REL + "/manifest.json"}
                   | ({e["path"] for e in cs["files"].values()} | {cs["config_append"]} if a.clock else set()))
    for p in paths:
        git("ls-files", "--error-unmatch", p)
    commit = clean_head(paths)
    out = Path(a.out)
    if out.exists() and any(p.name != "run" for p in out.iterdir()):
        raise SystemExit(f"NOT BUILT: {out} exists (only a run/ checkpoint may be kept)")
    out.mkdir(parents=True, exist_ok=True)
    for f, e in m["files"].items():
        place(e, out / f)
    fz = json.load(open(REPO / m["freeze_base"]))
    rtl = {f: e for f, e in m["files"].items() if f.startswith("rtl/") and f.endswith(".sv")}
    canon = rtl["rtl/ot_hgi_coll_tkm_tp192_tile_core.sv"]
    fz.update(plan=man["plan"]["path"], plan_encoding="gzip; plan_sha256 = sha256 of the uncompressed bytes",
              pins_file=m["files"]["pins.json"]["path"],
              rtl_overrides={"ot_hgi_coll_tkm_tp192_tile_core.sv": {"path": canon["path"], "sha256": canon["sha256"]}},
              rtl_sources={f: e["path"] for f, e in rtl.items()},
              source_commit=commit, source_tree=f"{REL}@{commit}", kit_builder=f"{REL}/build_kit.py",
              imported_kit_hash=m["imported_kit_hash"])
    assert fz["pins_sha256"] == m["files"]["pins.json"]["sha256"]
    if a.clock:
        for f, e in cs["files"].items():
            place(e, out / f)
        ap = (REPO / cs["config_append"]).read_bytes(); assert sha(ap) == cs["config_append_sha256"]
        (out / "config.mk").write_bytes((out / "config.mk").read_bytes() + ap)
        cc = dict(cs["freeze_clock_candidate"]); src_hash = kit_hash_of_source(m)
        cc.update(source_kit=f"{REL} build {a.kind} (no --clock) @{commit}", source_kit_tree_hash=src_hash,
                  clock_stage_files={f: e["path"] for f, e in cs["files"].items()})
        fz["clock_candidate"] = cc
        (out / "clock_candidate.json").write_text(json.dumps(cc, indent=1) + "\n")
        shutil.copyfile(REPO / REL / "run_tkm_clock_cts.sh", out / "run_tkm_clock_cts.sh"); (out / "run_tkm_clock_cts.sh").chmod(0o755)
    fz["kit_hash"] = kit_hash(out); fz["kit_hash_rule"] = "gen_core_kit_hbm.kit_hash (tree minus run/ views/ freeze.json run_*)"
    save(out / "freeze.json", fz)
    print(json.dumps(dict(kit=str(out), view=m["view"], kit_hash=fz["kit_hash"], source_commit=commit, clock=bool(a.clock))))


def kit_hash_of_source(m):
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        for f, e in m["files"].items():
            place(e, Path(t) / f)
        return kit_hash(t)


def do_receipts(a):
    m = json.load(open(MAN))["kits"][a.kind]; kit = Path(a.kit); src = HERE / "receipts" / a.kind
    clean_head([f"{REL}/receipts/{a.kind}"])
    fz = json.load(open(kit / "freeze.json"))
    (kit / "source_receipts").mkdir(exist_ok=True)
    for f in sorted(src.iterdir()):
        shutil.copyfile(f, kit / "source_receipts" / f.name)
    lec = json.load(open(kit / "source_receipts/lec.json"))
    fz["kit_hash_pre_lec"] = fz["kit_hash"]; fz["kit_hash"] = kit_hash(kit)
    fz["receipts_commit"] = git("rev-parse", "HEAD").strip(); fz["receipts"] = f"{REL}/receipts/{a.kind}"
    fz["synth_lec"] = {"verdict": lec["verdict"], "receipt": "source_receipts/lec.json",
                       "receipt_sha256": sha((kit / "source_receipts/lec.json").read_bytes())}
    save(kit / "freeze.json", fz); print(json.dumps(dict(kit=str(kit), kit_hash=fz["kit_hash"], pre=fz["kit_hash_pre_lec"])))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    i = sp.add_parser("import"); i.add_argument("common"); i.add_argument("terminal"); i.add_argument("clock")
    b = sp.add_parser("build"); b.add_argument("kind", choices=VIEWS); b.add_argument("out"); b.add_argument("--clock", action="store_true")
    r = sp.add_parser("receipts"); r.add_argument("kind", choices=VIEWS); r.add_argument("kit")
    a = ap.parse_args(); {"import": do_import, "build": do_build, "receipts": do_receipts}[a.cmd](a)
