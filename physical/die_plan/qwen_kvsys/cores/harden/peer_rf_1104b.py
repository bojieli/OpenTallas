#!/usr/bin/env python3
"""DIE-KV-70/PEER 11-04 qkd_hr_core_peer form r3: wrapper + core json on the r3 RTL (results/kv_peer_rf_1104b).
usage (repo root): peer_rf_1104b.py
Ports unchanged, so the wrapper is only a module-name substitution of the DIE-KV-69 form; the codec status stages stay.
Core json file list: repo-relative; source files replaced by the r3 modules are dropped so nothing else can bind them."""
import json, re
from pathlib import Path
SRC = Path("results/kv_peer_rf_1104/rtl/qkd_hr_core_peer")
OUT = Path("results/kv_peer_rf_1104b/rtl/qkd_hr_core_peer")
NAMES = [("qkd_host_peer_link #(", "qkd_host_peer_link_r3 #(", 1),
         ("qkd_host_peer_rank_codec u_peer_codec (", "qkd_host_peer_rank_codec_r3 u_peer_codec (", 1),
         ("qkd_host_peer_root_mux_pl2 u_root_mux (", "qkd_host_peer_root_mux_r3 u_root_mux (", 1),
         ("qkd_host_tp8_coordinator_mu #(", "qkd_host_tp8_coordinator_r3 #(", 1)]
t = (SRC / "qkd_hr_core_peer.sv").read_text()
for a, b, n in NAMES:
    assert t.count(a) == n, a
    t = t.replace(a, b)
(OUT / "qkd_hr_core_peer.sv").write_text(t)
cj = json.load(open(SRC / "qkd_hr_core_peer_core.json"))
DROP = re.compile(r"/(qkd_host_tp8_coordinator(_mu)?|qkd_host_peer_coordinator_codec(_mu)?|qkd_host_coordinator_services(_mu)?|"
                  r"qkd_host_post_collector(_mu)?|qkd_host_lifecycle_collected(_mu)?|ot_qwen_tp8_token_epoch_allocator(_mu)?|"
                  r"ot_qwen_tp8_token_cohort(_mu)?|qkd_host_peer_link|qkd_host_peer_rank_codec|qkd_host_peer_root_mux_pl2)\.sv$")
files = []
for f in json.load(open("/dev/stdin"))["files"]:
    if f.endswith("/qkd_hr_core_peer.sv") or DROP.search(f):
        continue
    m = re.search(r"/(rtl/|physical/|results/)(.*)$", f)
    files.append(m.group(1) + m.group(2) if m else f)
new = sorted(str(p) for p in OUT.glob("*.sv"))
cj["files"] = new + files
cj["member_modules"] = {"u_peer": "qkd_host_peer_link_r3", "u_peer_codec": "qkd_host_peer_rank_codec_r3",
                        "u_root_mux": "qkd_host_peer_root_mux_r3", "u_coordinator": "qkd_host_tp8_coordinator_r3"}
cj["rf_1104b"] = {"transform": "physical/die_plan/qwen_kvsys/cores/harden/peer_rf_1104b.py",
                  "form": "r3: DIE-KV-70/PEER cuts + status stage kept"}
(OUT / "qkd_hr_core_peer_core.json").write_text(json.dumps(cj, indent=1) + "\n")
print("files", len(cj["files"]), "new", len(new))
