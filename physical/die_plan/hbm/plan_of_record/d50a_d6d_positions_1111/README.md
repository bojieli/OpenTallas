# HBM next-event plan d50a_d6d_positions_1111 (HBM-COMPOSE-2 for DIE-HBM-100, 2026-11-11) DO_NOT_COUNT

Plan die_plan.json.gz (decompressed sha256 f638067aaf8320da170e8c8b05d0d6334defe4681c4c973ae9009852f625422f) = d49a e9ae418c06ca + deltas/d6d_hcol_s2_cplb1_1111.json.gz (CPL-HBM-B1 claude/cpl-hbm-b1-1111@67cfe043c5c5, positions only q_b010/q_b011 + pv1, 1498 ops; sha of the raw delta d27d8e1e). No conflict with the io types. Same delta on t19 gives b675e39ac459 as the author said.
Gates (pure main src_hbm_main_fe0002fac6, the d49a baseline tools):
- G0: d49a 554 -> 551, 2 new rows (re-keyed NW_b010 horizontal cuts 6250/7750 with new track counts), 5 lost; 0 real new.
- Strict two-pass R8 bind: BIND_OK, 92 partitions, 420 crossings, n_errors 0, stale 0, uncovered 0, pad_flops 945867 (= d49a). The r8 table is byte-equal to d49a's (fb94238a8c6a).
- stscan: no phantom; miss>405 q_b010 10 -> 0, pv1 10 -> 0, q_b011 3 -> 0, pv1 3 -> 0.
- route_supply p99 (d49a -> d50a): q_b010 1.953 -> 1.938, pv1 3.043 -> 1.910, q_b011 1.933 -> 1.686, pv1 2.446 -> 2.376. Worst: q_b011 1.403 -> 1.460, pv1 1.185 -> 2.307 (rscmp WORSE rows).
Excluded: SEAM-HOP-1 path_respace delta (see READY).
