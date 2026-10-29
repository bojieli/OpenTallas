#!/usr/bin/env python3
"""DIE-QC-36 KITS: record in PROG kit freeze.json the RTL actually signed (COORD ruling 13:14).
Keeps the old spec/repo_rev/rtl_patches values in a 'superseded' record; never deletes history.
usage: fix_freeze_provenance.py KIT"""
import hashlib, json, os, sys, datetime
kit = sys.argv[1]
fz = os.path.join(kit, "freeze.json")
d = json.load(open(fz))
if "rtl_signed" in d:
    sys.exit("freeze.json already has rtl_signed; refusing to rewrite")
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
raw = open(fz, "rb").read()
bak = fz + ".pre_provenance_fix"
if not os.path.exists(bak):
    open(bak, "wb").write(raw)
rtl = os.path.join(kit, "rtl")
files = {
    "qfd_dv_s5_vm8x.sv": "66b68bff2:rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv",
    "ot_sram_1r1w_1024x256_m2_r2c2_bb.v": "86288faea:physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v",
    "ot_sram_1r1w_128x256_m1_r2c2_bb.v": "86288faea:physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v",
    "ot_sram_1r1w_256x256_m2_r2c2_bb.v": "86288faea:physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_bb.v",
}
base = os.path.join(kit, "run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base")
now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
d["rtl_signed"] = {
    "basis": "routed LEC EQUIVALENT (lec_routed/lec.json, 7221/7221 compare points, kept 1972/1972, OT_LEC_SUPERSET_VEC=1 all_shown) of 6_final.v against these sources",
    "rtl_rev": "66b68bff2",
    "top_params": {"MIF": 1},
    "sources": [{"kit_path": "rtl/" + f, "repo": src, "sha256": sha(os.path.join(rtl, f))} for f, src in files.items()],
    "netlist": {"path": "run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base/6_final.v", "sha256": sha(os.path.join(base, "6_final.v"))},
    "lec_json_sha256": sha(os.path.join(kit, "lec_routed/lec.json")),
    "evidence": "claude/die-qc-35-kits-1029@cd2d5a05e7b results/qc_die34_1029/prog/ffh10r/lec_routed/",
    "recorded": now,
    "by": "DIE-QC-36 KITS (COORD ruling [DIE-QC-35 KITS update] 2026-10-29 13:14 (1))",
}
d.setdefault("superseded", []).append({
    "what": "RTL provenance of the signed netlist",
    "fields": {k: d[k] for k in ("spec", "spec_sha256", "repo_rev", "rtl_patches") if k in d},
    "why": "spec 86288faea / repo_rev 4151e9fe9f RTL predates MIF=1 (b91cc4b87); routed LEC vs it is NOT EQUIVALENT (gate-only g_r.u_hi_ra.* regs, lec_routed/lec_86288faea_pre_mif.json). spec/pins/outline/macros of 86288faea remain the physical spec; only the RTL source of record moves to rtl_signed.",
    "superseded_by": "rtl_signed",
    "original_file_sha256": hashlib.sha256(raw).hexdigest(),
    "original_backup": "freeze.json.pre_provenance_fix",
    "recorded": now,
})
json.dump(d, open(fz, "w"), indent=1)
open(fz, "a").write("\n")
print(json.dumps(d["rtl_signed"], indent=1)); print(json.dumps(d["superseded"], indent=1))
