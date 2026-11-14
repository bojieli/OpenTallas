# TYPE-SVCMEM handoff (2026-11-14 08:04 PST)
Problem: S81 svc_hi rs t5, rs t6, pvso_entry t2 FAIL GEN_LINT memory_bits since 11-13 01:xx, no lane.
Findings (checked):
- Over-cap memories (all 3 types identical): 4x ot_hdc_v41x_attn_staging g_lane[0..3].mem 160x265 = 42400 b each; ot_bind_native_193c9bdc... 512x512 = 262144 b; ot_bind_native_4c805a55... 640x256 = 163840 b; ot_bind_native_9c28130c... 8x2120 = 16960 b. Cap 16384.
- Same RTL in ALL 16 S81 svc types (hi t1-t6, pvso t1/t2, lo t1-t7, rs_w): the same failure hit hi t1,t3,t4 on 11-13 01:15/01:25.
- Structural fix already exists and is deployed: kit_rtl_post.d/s81_svc_memory.sh maps attn_staging to 8x ot_sram_1r1w_160x265_m1_r0c0 (train K b4c5665391d, SVC-BAND-3 2845e7a35b); KIT-OPS-3 00:34 11-14 raised lint bound to 65536 (lintmem) + post-gen watcher exports SYNTH_MEMORY_MAX_BITS 65536 for svc kits. FAIL-S81-1 raised lint bound too. Siblings hi t2/t3/t4 relaunched 11-14 06:xx on B3v src and are past/in gen_lint (a4 gen_lint admitted 07:31, a5 in gen).
- Why t5/t6/pvso t2 still fail: only the stale 11-13 attempts. Kit_wave.json dies.s81.hold_items keys svc_hi_dsdv_svc_rs__t5, _t5__*, _t6, _t6__*, svc_hi_dsdv_svc_pvso_entry__t2, _t2__* (SVC-MACRO-1113) still hold them; no attempt since.
Action: ASK KIT-OPS-3 to delete those 6 hold keys and add retry keys. No plan change; nothing for DIE-S81-92.
Next: when they launch, watch gen_lint/place/route; add AUTO-RESIGN row on pass (R-MINIMAL). Poll every >=10 min.

## 08:05
COORD approved release. Owning hi t1-t4/pvso t1. t1 a7 memory_bits PASS (place). Deadline for KIT-OPS-3 launch of t5/t6/pvso t2: 30 min, else self-launch.

## 08:37
t5/t6/pvso t2 launched 08:23 by KIT-OPS-3. Following hi t1-t6 + pvso t1/t2 through route; check 09:10. On pass: AUTO-RESIGN row + RESULT. Size fail -> evidence + split proposal.

## 09:10
reg_fanout (old 11-05 attempts) and BIND_STALE (old bind) do not reproduce on live attempts. Live: pvso t1 a12 place, t4 a4 place, t1 a7 place + a8 B3x2b; t2 gen_lint, t3 gen, t5/t6/pvso t2 kit_rtl. Next check 09:40.
