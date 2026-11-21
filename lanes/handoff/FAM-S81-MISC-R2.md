# FAM-S81-MISC-R2 handoff (11-21 ~16:00 PST) - STOOD DOWN (context); successor FAM-S81-MISC-R3
Work dir epyc10 /srv/opentallas-scratch2/claude/fam-s81-misc/ (scripts there; always export OT_LANE, run via ot-run on epyc10).
## t5 (representative)
- Final layout = var_v1f.json (col A -34.56 / B -25.92, ft0 regs[3] -> [50.858,287.86], taps re-sited): G0 0 t5 ERRORs (g0_v1f). NOTE check.py needs the plan inside a tree plan dir (g0v.sh does this).
- reach1: t5_reach1_delta_v1.json (reach_rules fix --rules 1, depth 5, worst hop 289). vp_sr: vp_sr_t5_resited_v1.json (53 sites, needs OT_S81SL_VP_SRAMREG RTL: without it bind fails LF_CS_DEPTH t5 ho plan2 vs RTL1).
- Full delta t5_full_delta_v1f.json (44 ops incl vp_sr stations); no-stations delta t5_nostn_delta_v1f.json (tree candMISC3, gate misc3: check s81-j6/gates/misc3 + fam-s81-misc/gate_misc3.log).
- Define op: kv_leaf_vpsramreg_define_op.json (5 kv_leaf types +OT_S81SL_VP_SRAMREG), proof tree candMISC4 = full delta + define, gate misc4 (fam-s81-misc/gate_misc4.log; mk4.sh chain RUNNING at stand-down). If BIND_RC=0, LATCHECK 873/873 and G0 0 new -> post to S81-J6-ASSEMBLY-R4 (define op + t5 rows) BEFORE the J7 cut. Then private t5 kit (normal priority, copy kw43 wave 224567138ab t5 gen dir + row patches, diff config.mk) - not started.
- Handed to S81-J6-ASSEMBLY-R4 (posts): t5 rows, vp_sr set as Layer-A dependent; R4 asked to confirm vp_sr+RTL in J7 Layer A.
## gunit
- One-op delta GATE PASS (candGUNIT1: bind 0, LATCHECK 873/873, 0 new G0, LAT diff 0 vs C1n). Posted to R3/R4 for J7.
## t2 split (COORD ruling: split along instance boundaries, no SRAM-store conversion)
- Cut x=1684.80 posted. Part B census: census5A (74,675 generic, t5 soft) / census5B (2,031,431 generic); calibration kve 12,325 coarse -> 56,454 ASAP7 (4.58) => B ~9.3M placed; 28 pieces at <=350k (first-fit by instance: kve x6, kvq x4+kve, cmp_pool lanes+E4M3, qnh/kvt/ik_reduce/qnr). TODO: instance->piece->region map + station rows at cut faces (405 um), next event; reach at cut faces unmeasured (fallback serialization -> COORD with numbers).
## phy
- Tool fix 4ad784e4086 on main; needs a fresh J6-bound gen on current rt once J6 applies (not started).
## iqf/seqhost/eng: unchanged (see FAM-S81-MISC.md).
## Waiters: all die with this lane - re-arm: gate_misc4 (grep J6_GATE_DONE in gate_misc4.log).

## Running units handed to successor: otrun-civil-redfish-1789426 (mk4.sh -> gate misc4, log mk4.log/gate_misc4.log), otrun-civil-redfish-486470 (gate misc3, gate_misc3.log)
