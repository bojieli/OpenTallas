# KV-TAPSPLIT-HGPV handoff (split from KV-ALLFIX, 11-23 22:55 PST)
Job: census a (tap load, cap 1200) for hg/hgi/pv on A5. Hubs = KV-HUB-HOLD (do not touch).
- KV-ALLFIX already put ROWS_KV-ALLFIX-TAPSPLIT-RD.py 8f1f158a5632 (epyc10 kv-allfix/rows) into a5.list after PORTPIN-HUBWI; it re-runs tap_split on the old 14 types (11 hg resel + pv_v1n/v3n/v5n). A5try/t5.json = A4d+lost rows+RD: hg 11 SPLIT +92, pv 3 SPLIT +9 (all 0 over, planned model for hg = soft flops NOT counted).
- My census: epyc10 /srv/opentallas-scratch2/claude/kv-tapsplit-hgpv/cen.sh on t5 -> cen_t5/ (planned + soft-flop models, 54 types).
- Early core pins: core_taps="early" on all; tap_split keeps schema.core_taps as fixed separate taps.
