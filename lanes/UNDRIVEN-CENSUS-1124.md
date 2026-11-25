# UNDRIVEN-CENSUS-1124: per-type undriven leaf input bits, newest full bind per die (REPORT-ONLY, r703)

Generated 2026-11-24 PST by lane UNDRIVEN-CENSUS-1124. Tool on main 44f48e35de (bind prints UNDRIVEN_OPEN_CENSUS, writes bind_open_inputs.json census).
Search: find on intel1 intel2 epyc2 epyc7 epyc8 epyc9 epyc10 epyc11 under /srv/opentallas-scratch*/claude, depth <= 11, kit-store/rt/warm/tree-cache/rtl skipped;
newest bind_open_inputs.json with bind_report.json and no BIND_PROBE_ONLY.json. These binds predate the census tool, so the numbers are recomputed from their files.

Counts: open = UNDRIVEN_OPEN bits from bind_open_inputs.json undriven[] (absent port / above connected width; summed over instances).
tied_ub = never-assigned `wire ub_N` (UNBOUND tied/top/err) in the type's emitted rtl/<module>.sv (largest variant file) = undeclared TIED bits; this is the FAM-S81-SVC-OWN 30,387 number.
total = open + tied_ub. Declared (excused) bits are not counted: shown per die as dead/bump/tied.

## s81 (s81)

bind dir: epyc9:/srv/opentallas-scratch/claude/s81-allfix-int/c8seal_tree/physical/die_plan/s81/plan_of_record/native_bind/allfix_c8_out  (bind_open_inputs.json mtime 2026-11-24 11:33 PST)  
types bound 403, types with any 24, open 127248, tied_ub 486192, total 613440; n_undriven 127248; declared dead/bump/tied 0/0/0; unjudged 0

| type | inst | groups | open (partial/absent/src_leaf) | tied_ub | total |
|---|---|---|---|---|---|
| svc_lo_dsdv_svc_rs__t1 | 1 | 53 | 7953 (7953/0/0) | 30387 | 38340 |
| svc_lo_dsdv_svc_rs__t2 | 1 | 53 | 7953 (7953/0/0) | 30387 | 38340 |
| svc_lo_dsdv_svc_rs__t3 | 1 | 53 | 7953 (7953/0/0) | 30387 | 38340 |
| svc_lo_dsdv_svc_rs__t4 | 1 | 53 | 7953 (7953/0/0) | 30387 | 38340 |
| svc_lo_dsdv_svc_rs__t5 | 1 | 53 | 7953 (7953/0/0) | 30387 | 38340 |
| svc_lo_dsdv_svc_rs__t6 | 1 | 53 | 7953 (7953/0/0) | 30387 | 38340 |
| svc_lo_dsdv_svc_rs__t7 | 1 | 53 | 7953 (7953/0/0) | 30387 | 38340 |
| svc_lo_dsdv_svc_rs_w__t1 | 1 | 53 | 7953 (7953/0/0) | 30387 | 38340 |
| svc_hi_dsdv_svc_pvso_entry__t1 | 1 | 53 | 7953 (7953/0/0) | 30386 | 38339 |
| svc_hi_dsdv_svc_pvso_entry__t2 | 1 | 53 | 7953 (7953/0/0) | 30386 | 38339 |
| svc_hi_dsdv_svc_rs__t1 | 1 | 53 | 7953 (7953/0/0) | 30386 | 38339 |
| svc_hi_dsdv_svc_rs__t2_att | 1 | 53 | 7953 (7953/0/0) | 30386 | 38339 |
| svc_hi_dsdv_svc_rs__t3 | 1 | 53 | 7953 (7953/0/0) | 30386 | 38339 |
| svc_hi_dsdv_svc_rs__t4_att | 1 | 53 | 7953 (7953/0/0) | 30386 | 38339 |
| svc_hi_dsdv_svc_rs__t5_att | 1 | 53 | 7953 (7953/0/0) | 30386 | 38339 |
| svc_hi_dsdv_svc_rs__t6 | 1 | 53 | 7953 (7953/0/0) | 30386 | 38339 |
| svc_hi_dsdv_svc_pvso_entry__t1_rs | 1 | 0 | 0 (0/0/0) | 1 | 1 |
| svc_hi_dsdv_svc_pvso_entry__t2_rs | 1 | 0 | 0 (0/0/0) | 1 | 1 |
| svc_hi_dsdv_svc_rs__t1_rs | 1 | 0 | 0 (0/0/0) | 1 | 1 |
| svc_hi_dsdv_svc_rs__t2 | 1 | 0 | 0 (0/0/0) | 1 | 1 |
| svc_hi_dsdv_svc_rs__t3_rs | 1 | 0 | 0 (0/0/0) | 1 | 1 |
| svc_hi_dsdv_svc_rs__t4 | 1 | 0 | 0 (0/0/0) | 1 | 1 |
| svc_hi_dsdv_svc_rs__t5 | 1 | 0 | 0 (0/0/0) | 1 | 1 |
| svc_hi_dsdv_svc_rs__t6_rs | 1 | 0 | 0 (0/0/0) | 1 | 1 |

## kv (qwen_kvsys)

bind dir: epyc10:/srv/opentallas-scratch2/claude/kv-allfix/a5t6e10/grow/gate_A5t6/bind  (bind_open_inputs.json mtime 2026-11-24 18:01 PST)  
types bound 93, types with any 0, open 0, tied_ub 0, total 0; n_undriven 0; declared dead/bump/tied 0/584/0; unjudged 0

no undriven input bits.

## qc (qwen_compute)

bind dir: epyc7:/srv/opentallas-scratch2/claude/QC-ALLFIX/cK/bind  (bind_open_inputs.json mtime 2026-11-24 14:22 PST)  
types bound 130, types with any 0, open 0, tied_ub 0, total 0; n_undriven 0; declared dead/bump/tied 3240/586/0; unjudged 0

no undriven input bits.

## head (s81_head)

UNMEASURED: no full bind with bind_open_inputs.json found on the live hosts (file exists only in binds since BIND-UNDRIVEN-IN 11-23).

## hbm

UNMEASURED: newest hbm binds found (hbm_arch_B2o, copied plan_of_record/event binds in intel2 flow-canary/sources/896c5200545a, mtime 11-24 18:00) predate bind_open_inputs.json; no census possible without a re-bind.

## Note

S81 c8: the 16 svc types carry 7,953 open bits (53 kreg.d groups, all partial width) + 30,386-30,387 tied_ub each (TIED, ot_s81_svc_merge_h4.iblk etc.); 8 *_rs / svc_hi t2/t4/t5 types have 1 tied_ub bit. Known root cause (Slang empty-blackbox ABI width of ot_hdc_v41x_kreg / _dly), fixed in c9s svctied asbuilt (probe-only binds, not counted). No verdict changed.
