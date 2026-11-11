# KV 12:00 cut (DIE-KV-98, S3): one plan event, EQ-gated

Result plan (epyc4 /srv/opentallas-scratch2/claude/dkv98/kv1200/plan_c.json, copies on epyc7/epyc2/epyc8 same path):
md5 bfe4c242d7fb217505fde3c9d9b096ca, sha256 bd6e6b2c397fc47bcd369066432eb2f7f030b2cfa87c7478ce662f3fe8753ece.
Base: kw43/kvr2 plan_c.json md5 92370701 (kvr2 8580c2f77135) -> step0 1f387181 (overlays e2s2/kvfix1/kvrs + sreg + ringhold + phyrev ccaf9e17).

Steps: scripts/run_cut.sh. step1 pv_S (10 types, sha 179f926e), step2 hub_Wi (sha b8e26d6a) + scripts/tapfix.py, step3 hg (3d32a037) + hgi (44d6840d),
step4 hgi_v6 (3b3093b4, conditional: drop it if KV-PLAN-2 plan_swh lands for v6). pv_N interim is NOT in the event (REDESIGN).

Gates measured (epyc4, nice 19):
- EQ: eq_diff.py step0 -> step4: 469 hard_cores origin/orient/track_offset/note fields changed, 1 other (kv3_hub_Wi clock.added_taps clk_t70 xy, a clock-tap SITE; netlist untouched).
- G0 (tools/die_plan/check.py): step0 130 errors = kvr2 base (0 new, 0 gone). step1..step4: 130 errors, 2241 warnings (= base). g0_new.py reports 24 NEW + 24 GONE on kv3_pv_* only,
  because the message carries the macro instance name (pvgN_pM) that the slot swap renames; keyed by type+slot, 0 new, 0 gone (same 24 'station cells intersect physical macros' errors as base).
- hub_Wi needed scripts/tapfix.py: without it check.py aborts (ValueError kv3_hub_Wi: added tap clk_t70 violates outline/halo/tap spacing); CPL-KV-PV's 'G0 0 new' was not run on the composed plan.
- station_lint.py: 0 INVERTED; 40 NONMONOTONE (advisory; base has the same class, e.g. kv3_pv_v6n ft slots).
