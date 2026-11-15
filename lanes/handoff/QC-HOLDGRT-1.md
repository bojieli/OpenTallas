# QC-HOLDGRT-1 handoff (11-15)
Root cause (MEASURED): tools/die_plan/pregrt_ff_hold.py accept test discarded the pre-GRT hold repair on any >1 ps placement-estimate TT WNS loss (fw_v1 -305.49->-306.61, stm_v1 -8.12->-9.62, hc3 +106->-2.7) or <1 ps hold gain.
Fix: pg_verdict proc, setup rejects only if s1 < -42 (OT_PREGRT_SETUP_GATE) AND s1 < min(s0,0)-5 (OT_PREGRT_SETUP_TOL). Branch claude/qc-holdgrt-1-1114 @f515b601b5ea (worktree intel2 /srv/opentallas-scratch2/claude/qc-holdgrt-1), 30 tests pass. READY posted for MERGE-QUEUE-1.
Installed 11-15 (sha256 969b75b49484) in wt/qc-s29-tree2/tools/die_plan on intel1 epyc2 epyc7 epyc8 epyc9 epyc10; backup pregrt_ff_hold.py.bak-holdgrt1-1115 on each (revert = cp -p bak over file via copy+mv). Only kits generated after install carry it.
Proofs (from 4_cts.odb, ot-run): fw_v1 FF -109.60->+4.04 (0 endpoints), TT -305.49->-306.61. stm_v1 FF -113.74->-98.27, endpoints 15238->3260 (all port_in, advisory r30), TT -8.12->-9.62. hc3: pass 2 reached +5.0 ps; final result pending (intel1 container qchg-hc3, log intel1:/srv/opentallas-scratch2/claude/qc-holdgrt-1-proof/hc3/kit/pregrt_ff_hold.log).
Retry keys: KIT-OPS-5 autokey waiter (intel2 ~/kitops5-autokey.log) keys the 8 types with fresh gen as attempts end.
Next owner: read hc3 result; if hc3 FALLBACKs or regresses TT below -42, revert from .bak and tell COORD.
