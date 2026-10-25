#!/usr/bin/env python3
"""KV-TOK 10-24 (COORD ruling A): the kvpc PC paths reset on the HBM reset, not on the HOST die reset.

Bound kv41/kv42: every pc partition resets its 4 kvpc instances (qkd_kvs_pc_*: PC controller, HBM calendar, embedding
endpoint and the slice boot-window face qkd_static_kv_pc_es_merge_b) from the reset spine ri_kvpc0_rst_n = HOST
die_rst_n (x_hub_Wi_rs_host_die_rst_n_*).  The HOST (ot_qwen_sys_rst_seq) releases die_rst_n only after every slice's
HBM cold-boot check reports done & ok, and that check's controller word passes through es_merge_b, held in reset by
die_rst_n => deadlock by construction (flat pc_part sub-bench, tools/qwen_layerbench/kv_dieslice/pcpart).

Fix (bind-level, deterministic): each u_kvpc<k> .rst_n takes the partition's delivered HBM reset i_host_hbm_rst_n_q[0]
-- the same signal its .hrst_n and the 4 HOST slices' .hbm_rst_n already use: the HOST hbm_rst_n carried as a pipelined
synchronous lane (ot_dp_st per crossing; the die reset rule's synchronous delivery, no local asynchronous synchroniser).
The slice-group leaf (u_slg) keeps ri_kvpc0_rst_n (die reset).  Nothing else changes; ports are unchanged.

A re-run of bind.py is not possible (the KV as-built bound_netlist.json was lost with the 10-23 hosts); this is the edit
bind.py's asbuilt.reset_spines would make with the kvpc rst_n pins bound to host.hbm_rst_n.

  kv_kvpc_hbm_reset.py IN_RTL_DIR OUT_DIR   -> OUT_DIR/<changed pc part files> + kvpc_hbm_reset.json
"""
import json, re, sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
rep = {}
for f in sorted(src.glob('kv3_pc*_part*.sv')):
    t = f.read_text()
    if 'ri_kvpc0_rst_n' not in t:
        continue
    n = 0

    def fix(m):
        global n
        blk = m.group(0)
        b2, k = re.subn(r'\.rst_n\(ri_kvpc0_rst_n_q\[0\]\)', '.rst_n(i_host_hbm_rst_n_q[0])', blk)
        assert k == 1, (f.name, m.group(1), k)
        n += k
        return b2
    t2 = re.sub(r'^\s*qkd_kvs_pc\w*\s+(?:#\(.*?\)\s*)?(u_kvpc\d+)\s*\(.*?\n\s*\);', fix, t, flags=re.M | re.S)
    assert n == 4, (f.name, n)
    assert 'i_host_hbm_rst_n_q' in t
    (out / f.name).write_text(t2)
    rep[f.name] = n
json.dump({'rule': 'COORD A: u_kvpc<k>.rst_n = i_host_hbm_rst_n_q[0] (was ri_kvpc0_rst_n_q[0] = HOST die_rst_n spine)',
           'files': rep, 'kvpc_instances': sum(rep.values())}, open(out / 'kvpc_hbm_reset.json', 'w'), indent=1)
print(f'{len(rep)} pc part files, {sum(rep.values())} kvpc instances rebound to i_host_hbm_rst_n_q[0]')
