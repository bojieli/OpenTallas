#!/usr/bin/env python3
"""KV-P7: KST (d2d_kv<->kvs_attn landed depths) for boot_v36/run.sh from a bind's bus_groups.json:
KS_RXV(srx),KS_RXP(rx_payload),KS_TXS(att_tx_slot),KS_TXK(att_tx_kind),KS_TXB(att_tx_beat),SK_TXV(att_tx_v),SK_TXP(att_tx_payload)."""
import json, sys
d = json.load(open(sys.argv[1])); s = {}
for g in d['landing']:
    for m in g['members']:
        k = (g['sink'], m['sink_port'])
        if k[0] in ('kvs_attn', 'd2d_kv'):
            s.setdefault(k, set()).add(m['landed_stages'])
want = [('kvs_attn', 'd2d__srx'), ('kvs_attn', 'd2d__rx_payload'), ('kvs_attn', 'd2d__att_tx_slot'),
        ('kvs_attn', 'd2d__att_tx_kind'), ('kvs_attn', 'd2d__att_tx_beat'), ('d2d_kv', 'att_tx_v'), ('d2d_kv', 'att_tx_payload')]
out = []
for k in want:
    v = s.get(k)
    if not v or len(v) != 1:
        sys.exit(f'KST: {k} landed stages {v} (need exactly one)')
    out.append(str(v.pop()))
print(','.join(out))
