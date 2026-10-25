#!/usr/bin/env python3
"""TOK-DS/BIND 2026-10-25: as-built manifest for the integrated S81 adopt178 bind (no F2B).

Usage: bind178_manifest.py PF_R6_MANIFEST PF_ROOT WT RUN [--no-io-roles]

PF_R6_MANIFEST  CODEX PORTFIX r6 manifest (asbuilt_pf_r6.json: cap30 as-built sources + current slice/PORTFIX
                sources, all as hashed copies in PF_ROOT/source_cache_r6)
PF_ROOT         its run root (source_cache_r6, asb/asbuilt_pf*.json + asb/out*/asbuilt_sources.json name the
                original path of every cached copy: cache name = sha256(original path)[:12] + '_' + basename)
WT              this branch's worktree (main + the PORTFIX/IDXNET RTL)
RUN             run dir: RUN/asb/{die_b178.v,map_b178.json} (frame_forward_bind.py + idxnet_die_bind.py on
                PORTFIX die_pf.v, NO F2B rewrite: COORD gather ruling B), writes RUN/asb/asbuilt_b178.json and
                RUN/asb/manifest_sources.json (which source each cached copy now resolves to)

Source rule (replaces CODEX's copy-into-cache so main's newer RTL is the one bound):
  - a cached copy whose original path was a PORTFIX tree/worktree rtl/ file -> WT/rtl/<same relative path>
  - a cap30 (binder4) copy whose basename is one of WT's s81_dv/slice/**/*.sv (CODEX r6 replaced those by the
    current slice source) -> that WT file
  - every other cap30 copy -> kept, copied into RUN/src_cache (frozen as-built snapshot, as on main's asbuilt_s81_*.json)
  - plus the IDXNET sources (qfs, TP leps, l20s, idx_tree, lep, lnland), and NO f2b_src.
"""
import glob
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

pf_manifest, pf_root, wt, run = map(Path, sys.argv[1:5])
io_roles = "--no-io-roles" not in sys.argv
p = json.loads(pf_manifest.read_text())

orig = set()
for f in glob.glob(str(pf_root / "asb/asbuilt_pf*.json")) + glob.glob(str(pf_root / "asb/out*/asbuilt_sources.json")):
    j = json.loads(Path(f).read_text())
    for k in ("files", "prefer", "full", "lib"):
        orig.update(x for x in j.get(k, []) if isinstance(x, str))
by_hash = {hashlib.sha256(o.encode()).hexdigest()[:12]: o for o in orig}

slice_root = wt / "rtl/dsrom_sys/s81_dv/slice"
slice_by_name = {}
for s in slice_root.rglob("*.sv"):
    slice_by_name.setdefault(s.name, []).append(s)

cache = run / "src_cache"
cache.mkdir(parents=True, exist_ok=True)
resolved, record = {}, {}
for f in dict.fromkeys(p["files"] + p["prefer"]):
    b = os.path.basename(f)
    o = by_hash.get(b.split("_", 1)[0])
    if o is None:
        raise SystemExit(f"no original path for cached copy {f}")
    name = b.split("_", 1)[1]
    new, why = None, None
    for root in ("/codex-s81-portfix/tree/rtl/", "/wt/s81-portfix/rtl/"):
        if root in o:
            new, why = wt / "rtl" / o.split(root, 1)[1], "tree"
    if new is None and name in slice_by_name:
        if len(slice_by_name[name]) != 1:
            raise SystemExit(f"ambiguous slice source {name}: {slice_by_name[name]}")
        new, why = slice_by_name[name][0], "slice"
    if new is None:
        new, why = cache / b, "cap30"
        shutil.copy2(f, new)
    if not new.is_file():
        raise SystemExit(f"missing source {new} (for {o})")
    same = Path(f).read_bytes() == new.read_bytes()
    resolved[f] = str(new)
    record[str(new)] = dict(orig=o, kind=why, same_as_codex_r6=same)

p["files"] = list(dict.fromkeys(resolved[f] for f in p["files"]))
p["prefer"] = list(dict.fromkeys(resolved[f] for f in p["prefer"]))
idx = ["idx/dsdv_idx_tree.sv", "idx/dsdv_idx_l20s.sv", "idx/dsdv_idx_qfs.sv", "slice/ot_s81sl_slice_lep.sv",
       "slice/mu72/ot_s81_mu72_lnland.sv", "slice/mu72/ot_s81sl_slice_lepe_mab_tp_mu_72.sv",
       "slice/mu72/ot_s81sl_slice_lepw_mab_tp_mu_72.sv", "slice/mu72/ot_s81sl_slice_lepe_nh_mu_72.sv",
       "slice/mu72/ot_s81sl_slice_lepw_mab_hbc_prod_mu_72.sv"]
for f in idx:
    q = str(wt / "rtl/dsrom_sys/s81_dv" / f)
    assert Path(q).is_file(), q
    for k in ("files", "prefer"):
        if q not in p[k]:
            p[k].append(q)
for m in ("ot_s81sl_slice_lepe_mab_tp_mu_72", "ot_s81sl_slice_lepw_mab_tp_mu_72"):
    if m not in p["dissolve"]:
        p["dissolve"].append(m)
p["rtl_roots"] = [str(wt / "rtl"), str(cache)]
p["base"] = str(wt)
p["netlist"] = [str(run / "asb/die_b178.v")]
p["map_file"] = str(run / "asb/map_b178.json")
if io_roles:
    p["io_roles"] = [[r"lk_(?:WS|WN|ES|EN)[0-9]+_(pma_(?:rx|rck|tx|tck))", r"\1"]]
p["lint_split"], p["lint_jobs"] = True, 6   # whole-die lint OOM (BINDER4 r8 precedent)
p["note"] = ("TOK-DS/BIND 10-25: adopt178 (main) integrated S81 bind: CODEX PORTFIX r6 as-built (cap30 + boot/fault/dead "
             "ABI) + 24 frame forwards + six IDXNET lanes + four reserve PHYs; NO F2B (COORD gather ruling B, full-width "
             "fold); current sources from this branch (main + PORTFIX/IDXNET RTL); io_roles for the repeated SerDes PHY.")
missing = [f for f in p["files"] if not Path(f).is_file()]
assert not missing, missing
(run / "asb/asbuilt_b178.json").write_text(json.dumps(p, indent=1))
(run / "asb/manifest_sources.json").write_text(json.dumps(record, indent=1))
kinds = {}
for v in record.values():
    k = (v["kind"], v["same_as_codex_r6"])
    kinds[k] = kinds.get(k, 0) + 1
print("files", len(p["files"]), "prefer", len(p["prefer"]), {f"{a}/{'same' if b else 'CHANGED'}": n for (a, b), n in kinds.items()})
