#!/usr/bin/env python3
"""mk_kit.py OLD_KIT NEW_KIT LAYOUT(A|B) DENSITY MACROLIB PATCH: kit-copy form of d44v part 58 (macro swap + placement)."""
import hashlib, json, re, shutil, subprocess, sys
from pathlib import Path
old, new, lay, dens, ml, patch = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], Path(sys.argv[5]), sys.argv[6]
SKIP = {"run", "lec", "__pycache__", "face_shell_work"}
new.mkdir(parents=True)
for p in old.iterdir():
    if p.name in SKIP or p.name.startswith("lec_async") or p.name.endswith(".log") or p.name.startswith("hold_gate.log") or p.name in ("lec_run.log", "selrange.json", "selrange.rc", "face_guard.json", "port_bind.json", "rtl_lint.json", "sdc_lint.json"):
        continue
    if p.is_dir(): shutil.copytree(p, new / p.name)
    else: shutil.copy2(p, new / p.name)
subprocess.check_call(["python3", "-I", patch, str(new / "rtl/ot_q2nf_rest.sv")])
REP = {"ot_sram_1r1w_64x512_m1_r2c2": "ot_sram_1r1w_64x141_m1_r0c0_g141", "ot_sram_1r1w_256x256_m2_r2c2": "ot_sram_1r1w_256x256_m2_r0c0_g256"}
for f in ("config.mk", "freeze.json", "rtl_lint.ys"):
    t = (new / f).read_text()
    for a, b in REP.items(): t = t.replace(a, b)
    if f == "config.mk":
        t = t.replace("-DOT_Q2NF_TGTQ1", "-DOT_Q2NF_TGTQ1 -DOT_Q2NF_RW"); t = re.sub(r"export PLACE_DENSITY = \S+", "export PLACE_DENSITY = " + dens, t)
    if f == "rtl_lint.ys": t = t.replace("-DOT_Q2NF_TGTQ1", "-DOT_Q2NF_TGTQ1 -DOT_Q2NF_RW")
    (new / f).write_text(t)
for a, b in REP.items():
    for q in (new / "macros").glob(a + "*"): q.unlink()
    for s in (".lef", "_tt.lib", "_ss.lib", "_ff.lib"): shutil.copy2(ml / b / (b + s), new / "macros" / (b + s))
pf = "u_fcore.u_x.u_body."
L, I, T = REP["ot_sram_1r1w_64x512_m1_r2c2"], REP["ot_sram_1r1w_256x256_m2_r2c2"], "ot_sram_1rw_256x64_m4_r2c2"
sx = lambda v: round(round(v / 0.048) * 0.048, 3); sy = lambda v: round(round(v / 0.048) * 0.048 + 0.012, 3)
y0 = 220.0 if lay == "A" else 85.0
rows = []
for lk, x in ((0, 133.0), (1, 597.0)):
    for b, y in enumerate((239.0, 317.0, 406.0, 484.0)): rows.append((rf"g_link\[{lk}\].u_link.g_bank\[{b}\].u_store.u_native.u_sram", L, x, y))
y = y0
for g in range(3):
    for s in ("lo", "hi"): rows.append((rf"g_iss256.u_issuer.g_mem\[{g}\].u_bank.u_sram_{s}", I, 308.4, y)); y += 40.392
rows += [(r"g_iss256.u_issuer.g_meta\[1\].u_sram", T, 360.0, y0 - 26.0), (r"g_iss256.u_issuer.g_meta\[0\].u_sram", T, 360.0, y0 - 52.0)]
for n in (r"g_iss256.u_issuer.g_meta\[2\].u_sram", r"g_iss256.u_issuer.g_meta\[3\].u_sram", "g_q2.n_u_fj.u_fj.u.u_program.g_fsram.u_flow"):
    rows.append((n, T, 360.0, y)); y += 26.5
oldnames = set(re.findall(r"\{(u_fcore\S+)\}", (old / "macro_placement.tcl").read_text()))
assert {pf + r[0] for r in rows} == oldnames, {pf + r[0] for r in rows} ^ oldnames
(new / "macro_placement.tcl").write_text("foreach {inst master x y orient} {\n" + "".join(f"  {{{pf}{a}}} {b} {sx(c)} {sy(d)} R0\n" for a, b, c, d in rows) +
    "} {\n  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact\n}\n")
pv = json.loads((new / "PROVENANCE.json").read_text())
for k in pv["files"]:
    if (new / k).exists(): pv["files"][k] = hashlib.sha256((new / k).read_bytes()).hexdigest()
pv["q2r_note"] = "DIE-HBM-83-Q2R part 58 kit-copy form from " + str(old)
(new / "PROVENANCE.json").write_text(json.dumps(pv, indent=1) + "\n"); print("kit", new, lay, dens, len(rows))
