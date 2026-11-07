#!/usr/bin/env python3
"""Prepare a self-contained TX-stage proof from your OWN source clone."""
import argparse
from pathlib import Path
import re
import subprocess

BASE = "93c061c396c"
ENC = "rtl/hbm_accel/cores_split/reform_1104b/ot_s81_kp4_enc_la.sv"
INPUTS = [
    "rtl/hbm_accel/cores_split/reform_1104b/ot_s81_kp4_enc_la2_mat.svh",
    "rtl/hbm_accel/cores_split/reform_1104b/ot_s81_kp4_enc_ff_mat.svh",
    "rtl/dsrom_sys/s81_link/ot_s81_gf1024.svh",
    "rtl/dsrom_sys/s81_link/ot_s81_kp4_enc_mat.svh",
    "rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv",
]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--repo", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
rtl = a.out / "rtl"
rtl.mkdir(parents=True, exist_ok=True)
for name in INPUTS:
    data = subprocess.check_output(["git", "-C", str(a.repo), "show", BASE + ":" + name])
    (rtl / Path(name).name).write_bytes(data)
ref = subprocess.check_output(["git", "-C", str(a.repo), "show", BASE + ":" + ENC]).decode()
ref = re.sub(r"\bot_s81_kp4_enc_la\b", "ot_s81_kp4_enc_la_ref", ref)
(rtl / "enc_ref.sv").write_text(ref)
(rtl / "ot_s81_kp4_enc_la.sv").write_bytes((a.repo / ENC).read_bytes())
here = Path(__file__).resolve().parent
for name in ("tb.sv", "run_sims.sh"):
    (a.out / name).write_bytes((here / name).read_bytes())
print(f"Prepared {a.out}; baseline {BASE}; candidate from {a.repo / ENC}")
