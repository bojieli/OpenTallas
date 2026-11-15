# KV-RAWFIX handoff (2026-11-15)
Branch claude/kv-rawfix-1115@b81e966a18 (tools/die_plan/kv_start_corridor_event.py raw_type 3-part rule + tests/test_kv_start_corridor_raw_rule.py, 8 tests pass; fail on old tool).
Proof on kvgeom7f plan: 19/19 hg/hgi types rc=0, max hop 405.0 um (v1p6), all <=405; part 3 needed on the 11 types (target moved 3.6-26.9 um). Plan: epyc7 fable-kvovf/rawfix/new/plan.json (run: rawfix/run19.sh).
Gate on that plan (tree kw45/kvrawfix_7f): G0 PASS, LATCHECK 2404/2404 PASS, bind emits raw branches (u_cland_raw_o_N relays in kv3_hgi_v3/kv3_hg_v1 part.sv). Bind RC=1 only PARAM_REGEN kv_pv_col_regen ECTL K round trips differ [18,24] (krq/krs; not raw-related, KV-102 R8/ECTL item).
Open: generate one type (gen rtl) fails i_ectl_Q_N_eN open bus on kv3_hgi_v3/kv3_hg_v1 both with and without raw plan (kvgeom7f station item, KV-102).
