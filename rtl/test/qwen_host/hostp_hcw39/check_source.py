#!/usr/bin/env python3
"""KV-P2-RTL 10-23: bind the HOSTP minimum mechanism bench to the OBSX source cone after the raw_hc tie removal."""
from pathlib import Path
import sys
root=Path.cwd()
packet=(root/'rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obsx.sv').read_text()
for exact in ["assign hc={raw_hc[181:39],transport_hc[38:0]};",
              "qkd_host_hc_station #(.MUT(HC_MUT),.HCW(39))u_hc(",".raw_hc(raw_hc[38:0])",
              "wire[181:0]raw_hc;wire[38:0]cmd_hc;",
              "assign pr=(replay_target==0)?raw_pr:143'b0;"]:
    assert exact in packet, f'OBSX source cone changed: {exact}'
assert "143'd0,raw_hc[38:0]" not in packet, 'OBSX still ties the station raw_hc'
print('HOSTP_SOURCE_BOUND PASS obsx START-only station HCW39 + hc[181:39] bypass')
