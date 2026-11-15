# S81-LEAF-T14 handoff (2026-11-15 08:02 PST)
Task: FABLE-PD-S81T-0710 sec 4 / FABLE-TRIAGE-S81 sec 8 / FABLE-CLOSURE-STRATEGY lever 4 (COORD r88): t14 row + station re-site class on B6gslcf.
## Done
- TL-LEAFT14 r2 cancelled (epyc10, ot-heavy-stop --match).
- t14 row: ve_m +34.56 east (slot 8.64 -> 43.2), 5 stages out of u_vsw/vn_b re-banded (1,503 sites -> 0, u <= 0.935).
- Class rows: epyc7 /srv/opentallas-scratch2/claude/s81-leaf-t14/rows_E2_all.json (48 types, sha d5c940579dac), composed plan_gslcf_E2.json (103f56b7f861). Ledgers led_class.json (ve slot + ft in core: t14 t16 t24cl2456157b t32 t38 t58 t65 t68), led_ist.json (44 types, 977 rows, 1,442 regs, 82,170 bits).
- 2 refused rows (bus:leafup_i2 in dsdv_slice_c1x_C__t7 and dsdv_slice_lepw_mus_C__t1): +1 station rows in rows_refused_plus1.json (t7 4->5 regs, max hop 318.8; lepw_mus 3->4, 327.6); adds 1 cycle on that bus, price with LATCHECK. A hop-405 re-site is not viable: all hops are already 382-388 on the column pitch, so moving the in-core reg out needs a longer neighbour hop.
- Tools on branch claude/s81-leaf-t14-1115 (off claude/s81-leaf-plan-1114, since they import ft_throat_fix which is not on main yet): leaf_slot_clear.py, istation_clear.py (--grow), tests.
## Pending
- t14 place + GRT: kit epyc7 /srv/opentallas-scratch2/claude/s81-leaf-t14/kit/p1/kit/gen/ot_s81sl_leaf__t14 (run_kit.sh grt). Pass = overflow 0 inside 30 iterations; then route.
- Post full READY (rows + per-type list + GRT) to DIE-S81-92, S81-LEAF-PLAN, COORD.
## Kit notes
- B6gslcf has no bound RTL (bind EMIT bk_sel__t2); kit uses B6gsl bind out + src_rel2 + plan_gsl_t14.json (B6gsl + the t14 row).
- gen_phys in the kit src is patched privately (OT_PROOF_STALE_RESET) for the collector_tree after the ve_m move; kit_rtl.f repointed from B6gsl/src to the kit own src (stale ot_dp_clk_landing.sv without LOCAL).
