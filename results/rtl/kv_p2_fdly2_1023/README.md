# KV attention F_DLY = 2 bit-exact bench (KV-P2-RTL, 2026-10-23)

Bench: tb_kvattn_rel (bench 0e597ed1c), r17 KV attention on assembly 92c2417f6, explicit-r17 binding (b0cc8cdca),
Verilator 5.050, ot-epyc9 (/srv/opentallas-scratch/claude/kv-p2-rtl-1023). Case list = tools/qwen_layerbench/kvattn_rel/run.sh.

| set | frame | FD | bit-exact cases (10) | T32768 | mutants (7) |
|---|---|---|---|---|---|
| vehicle_fd3 | vehicle (TOKe-QWM binary b7829094, all root words land 1 edge) | 3 forced (cal 3) | 10/10 PASS | REFUSED | 7/7 FAIL |
| vehicle_fd2 | same binary | 2 forced (cal says 3) | 0/10 PASS (face result fault: fin late) | REFUSED | 7/7 FAIL |
| planframe_dqk0 | kv_planframe dp PV_LAND 0 (pvst/pvfst unlanded = D(pvp) 0), D_QK 0 | cal 2 | 7/10: u1 T1024/T4096/T4096 peaky, u4 T1024/T4096 PASS; u1 T8191, u1 T8192, u4 T8192 FAIL | REFUSED | 7/7 FAIL |
| planframe_dqk1 | same + kvs_ctl D_QK 1 (+DQK tb) | cal 2 | same 7/10; same 3 FAIL | REFUSED | 7/7 FAIL |

T8191/T8192 failures are stack faults on stacks 0 and 1 (dp_fault 0x0013 = stack_fault[0], [1]); no data mismatch was reported
(result words never emitted). qkd_astk_native_er_service_w faults when an ER (exp readback) read lands on an edge where the
stack's own engine still drives its SO port, or when two reads collide. With the PV words unlanded the V/ER reads come one edge
earlier against the QK-frame stack schedule. At max context there is no slack for that. D_QK 1 moves the whole QK calendar
(lmax -> exp -> z -> pv), so the relative edge stays the same. The r17 root launches start_pv at cp_pv - (PV_LEAD + 1) with
PV_LEAD >= 0, so with this root RTL the PV frame cannot start later than the vehicle frame.
Conclusion: F_DLY 2 is bit-exact up to T4096 only. For T8192 the plan needs D(pvp) = 1 (F_DLY 3, the proven point) or a root
change (pv launch lead 0 = cp_pv - PV_LEAD, or a PV-frame ER calendar).
