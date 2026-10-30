#!/usr/bin/env python3
"""KV-P7: KST (d2d_kv<->kvs_attn landed depths) for boot_v36/run.sh from a bind's bus_groups.json:
KS_RXV(srx),KS_RXP(rx_payload),KS_TXS(att_tx_slot),KS_TXK(att_tx_kind),KS_TXB(att_tx_beat),SK_TXV(att_tx_v),SK_TXP(att_tx_payload).
  kst.py BUS_GROUPS.json             -> KST
  kst.py --host-rt BUS_GROUPS.json   -> HOST record relay stages (TOK-KV-4 10-29) = landed D(d2d_kv.record_send_kind ->
     HOST) + D(HOST.record_tx_observed_v -> d2d_kv) (0 when the HOST record port is not a crossing); the pair image's
     --host-stages (d2d_link_calendar TXD K[1] = 2 + this + PR 2).  Fails when a slot / record bundle lands unequal."""
import json, sys
if sys.argv[1] == '--host-rt':
    d = json.load(open(sys.argv[2])); s = {}
    for g in d['landing']:
        for m in g['members']:
            src, port = m['source'], m['sink_port']
            if src.startswith('d2d_kv.record_') and src.split('.', 1)[1] == port:
                s.setdefault(('out', port), set()).add(m['landed_stages'])
            elif g['sink'] == 'd2d_kv' and port in ('record_tx_observed_v', 'record_tx'):
                s.setdefault(('back', port), set()).add(m['landed_stages'])
    def one(k, ks):
        v = set().union(*(s.get(x, set()) for x in ks))
        if len(v) > 1:
            sys.exit(f'HOST_RT: {k} bundle {ks} lands unequal {sorted(v)} (slot and record must share one age)')
        return v.pop() if v else 0
    out = one('out', [('out', 'record_send_kind'), ('out', 'record_witness_slot')])
    back = one('back', [('back', 'record_tx_observed_v'), ('back', 'record_tx')])
    print(out + back)
    sys.exit(0)
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
