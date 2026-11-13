Production native H8 RT2 static producer reschedule: focused protocol result

Modified production outer dsdv_svc_att.sv only under H=8 and all three defines
OT_SVC_MERGE_H4, OT_ATTN_HCORE, OT_SVC_H8_REUSE_RT2. Replica calendar toggles
on every clock from reset, independent of request/ready. Q index advances at
planned phase1 launch only; registered engine Q receives phase0. Qmem address
is q_launch_count in both macro SYNC1 and ordinary registered-array forms.
KV keeps the existing rc one-per-clock plan. Run ends only after all Q launches
and all KV releases. P uses fixed phase1 pushes into the existing 2-slot skid;
no storage was added, no ready-dependent issue was introduced.

Phase-aware compiler opt-in record OT_SVC_NATIVE_RT2_CALENDAR=1 is PROSPECTIVE,
UNCALIBRATED and H8_CALIBRATED remains False. Emitted PIO/PVO constants and GO
words are unchanged. Both GO phase records are emitted, including P rounding.

Actual decoder programme: CFG, WIN T32, SEL_IDS32, ROWS32, Q128bodywords,
P8bodywords, GO PO64/PVO200. No source or memory backdoors. Consumer is explicitly
PROTOCOL ONLY, using actual calendar, actual H8 RT2 expander and the existing
2-slot P skid contract. Synthetic PV completion carries no numerical claim.

Final ot-run unit epyc7 oth-ubuntu-1553166-1794611213 exit0.
Both GO phases tested in ordinary-memory and macro SYNC1 forms:
 phase1 Q engine accepts GO+3,5,...17; P pushes+64,66,68,70.
 phase0 Q engine accepts GO+2,4,...16; P pushes+65,67,69,71.
Every case: Q8, KV8 II1, P4 II2, expanded P8, all Q/P fields exact;
zero absolute-date, cadence or phase errors; production fault_code0, actual af0.
Compiler phase record matches these dates. No numerical latency is asserted.

Malformed control removes only OT_SVC_H8_REUSE_RT2 from outer producer,
retaining native calendar consumer. Old Q everyclock plan loses half Q:
Q4,128/96 bad Q16bit fields for GOphase1/0, fc00201000 (Q/P refusals), P never
completes. It is rejected by actual producer fault bits and data checks.
The separate real expander malformed-cadence unit proves actual af1 and P loss.

Macro test warm reset emits existing SEL memory pointer-step 2->0 diagnostic;
this is reset-pointer observation, not a protocol fault (fc0, both data checks
and subsequent programme pass). No source edits made for that existing message.

Source files in existing E7 WT:
 rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv
 tools/s81_dv/layer_prog/lower_svc.py
 rtl/dsrom_sys/s81_dv/svc_rs/test/tb_svc_static_producer.sv
 tools/s81_dv/svc_rs/run_static_producer_bench.sh
Evidence: out_final/{build,run}_{nominal,nominal_macro,malformed}.log,
 compiler_phase_record.json. Original initial FAIL was bench-only P expansion
expected-index formula (32*grp used instead of16*grp); corrected before final.
No POR adoption, no claim of full combined programme calibration.
