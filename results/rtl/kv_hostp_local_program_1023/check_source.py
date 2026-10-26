#!/usr/bin/env python3
"""Bind the minimum mechanism bench to the selected obsx source cone."""
from pathlib import Path
import hashlib,json
root=Path.cwd()
packet=(root/'rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obsx.sv').read_text()
for exact in ["assign hc={raw_hc[181:39],transport_hc[38:0]};", ".raw_hc({143'd0,raw_hc[38:0]})", "assign pr=(replay_target==0)?raw_pr:143'b0;"]:
    assert exact in packet, f'Frozen source cone changed: {exact}'
manifest=json.loads((root/'results/rtl/kv_hostp_local_program_1023/source_manifest.json').read_text())
for name,expected in manifest.items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected, f'Source changed: {name}'
print('HOSTP_SOURCE_BOUND PASS exact selected obsx source and actual leaf hashes')
