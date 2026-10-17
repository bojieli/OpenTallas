#!/usr/bin/env python3
"""Golden slots for tb_seq_static (Q-KVSYS PVJOIN 2026-10-16): seq_static_golden.py CALDIR ROOTS_JSON OUT.svh

From the link compiler's program calendar (KV receiver view, one decode layer run) and the layer programme roots
(tools/qwen_static_kv/layer_roots_from_link.py) it writes the static sequencer's pin-level slots per layer run:
  G_CMD   edge of att_rx_v (kind 1) at the static D2D end's pin = CMD rx_out + 1 (PR output stage)
  G_Q0    first Q beat (kind 2) at the pin = Q beat 0 rx_out + 1; beats follow on consecutive edges (checked)
  G_KV0   first kvn_word_valid at the pin = KVN rx_out + 1 (kvn receiver register) + 1 (PR); 4 consecutive (checked)
  G_LPRUN the layer programme's attention_run lead before the CMD pin edge (= G_CMD - root attention_run)
  G_AQ    the compiled aq start edge at the quadrant face after the CMD pin edge = last KVN pin edge (G_KV0 + 3 - G_CMD)
          + 1 store push + 3 pop margin + 4 KVN pops + 1 start + 2 core output stages + 2 fan stages - 4 (pop overlap)
          = 9 edges after the last KVN word (qkd_seq_core_static KP0 37)
"""
import json
import sys
from pathlib import Path

cal = json.loads(Path(sys.argv[1], 'calendar.json').read_text())
roots = json.loads(Path(sys.argv[2]).read_text())
m = [x for x in cal['messages'] if x.get('seg', 0) == 0 and x['src'] == 'C']
cmd = [x['rx_out'] for x in m if x['rx_port'] == 0 and x['kind'] == 1]
q = sorted(x['rx_out'] for x in m if x['rx_port'] == 0 and x['kind'] == 2)
kv = sorted(x['rx_out'] for x in m if x['rx_port'] == 3 and x['kind'] == 5)
assert len(cmd) == 1 and q == list(range(q[0], q[0] + 32)) and kv == list(range(kv[0], kv[0] + 4)), (cmd, q[:3], kv)
g_cmd, g_q0, g_kv0 = cmd[0] + 1, q[0] + 1, kv[0] + 2
run = roots['layer_relative']['attention_run']
assert 0 < g_cmd - run < 64, (g_cmd, run)
Path(sys.argv[3]).write_text(f'localparam integer G_CMD = {g_cmd};\nlocalparam integer G_Q0 = {g_q0};\n'
                             f'localparam integer G_KV0 = {g_kv0};\nlocalparam integer G_LPRUN = {g_cmd - run};\n'
                             f'localparam integer G_AQ = {g_kv0 + 3 - g_cmd + 9};\n')
print(f'SEQ_GOLD G_CMD={g_cmd} G_Q0={g_q0} G_KV0={g_kv0} G_LPRUN={g_cmd - run} G_AQ={g_kv0 + 3 - g_cmd + 9}')
