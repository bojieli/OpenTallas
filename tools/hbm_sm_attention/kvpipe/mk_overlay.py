"""KVPIPE real-token overlay: private copy of the r18h5 bundle with the KVPIPE kv_line (as __fcore inside the
face shell) + the compensated attn_front_static.  usage: mk_overlay.py SRC OUT"""
import hashlib, json, shutil, sys
from pathlib import Path

src, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
b0 = src / "physical/die_plan/hbm/bind/r18h5_bundle"
assert not out.exists(), out
shutil.copytree(b0, out, symlinks=False)          # real copy (follows links), never hard links
attn = out / "rtl/hbm_accel/sm/attn"
for f in attn.rglob("*"):
    assert not f.is_symlink()
core = (src / "rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_line.sv").read_text()
assert core.count("module ot_hbm_sm_kv_line #(") == 1
(attn / "ot_hbm_sm_kv_line.sv").unlink()
(attn / "ot_hbm_sm_kv_line__fcore.sv").write_text(core.replace("module ot_hbm_sm_kv_line #(", "module ot_hbm_sm_kv_line__fcore #("))
sh = src / "rtl/test/hbm_accel/sm_attn/kv_line_shell"
for f in ("ot_hbm_sm_kv_line__fshell.sv", "ot_hbm_face_reg.sv", "ot_hbm_face_nreg.sv"):
    shutil.copyfile(sh / f, attn / f)
shutil.copyfile(src / "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_front_static.sv", attn / "ot_hbm_sm_attn_front_static.sv")
mf = json.loads((out / "master_files.json").read_text())
L = mf["ot_hbm_accel_smh_attn"]
i = L.index("rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_line.sv")
L[i:i + 1] = ["rtl/hbm_accel/sm/attn/" + f for f in
              ("ot_hbm_face_reg.sv", "ot_hbm_face_nreg.sv", "ot_hbm_sm_kv_line__fcore.sv", "ot_hbm_sm_kv_line__fshell.sv")]
(out / "master_files.json").write_text(json.dumps(mf, indent=1))
man = {p: hashlib.sha256((out / p).read_bytes()).hexdigest() for p in L}
(out / "KVPIPE_OVERLAY.json").write_text(json.dumps({"base": str(b0), "files": man}, indent=1))
for f in out.rglob("*"):
    if f.is_file():
        f.chmod(0o444)
print("OVERLAY", out, len(L), "files")
