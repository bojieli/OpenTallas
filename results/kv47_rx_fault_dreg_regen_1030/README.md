# KV qkd_hr_core_rx regen with the FAULT_DREG admission variant (DIE-KV-47-HR, 2026-10-30)

Source: wrapper kv-host-regen-1/rtl/qkd_hr_core_rx/qkd_hr_core_rx.sv (instantiates only qkd_host_rx_class_admission ->
qkd_host_rx_class) + rtl/qwen_sys/host_20261013/fault_dreg/qkd_host_rx_class_admission.sv (FAULT_DREG=1 default) +
rtl/qwen_sys/host_20261013/qkd_host_rx_class.sv (main f67ec6bbb35). Chain = the RX kit of record chain (inner.sh):
yosys flatten -> hr_face_ports.py (main) face transform -> hr_face_preserve.py (Codex v2, --retime-output deferred,fault)
-> memory_map emit (keep_mapped.v = kit rtl/qkd_hr_core_rx.v, sha in sha256.txt).

Proofs (eq_rc_1030.txt, yosys 0.68 equiv_simple/induct -seq 2):
- id rc=0: old FP pre.json (kv-hr-1-1029/fp) == pre of wrapper + main ORIGINAL admission -> lineage reconstructed exactly.
- post rc=0 / mut rc=1 (face transform), keep rc=0 / keepmut rc=1 (preserve transform), v rc=0 (emitted kit RTL vs pre).
- RTL-level FAULT_DREG vs original: DIE-KV-46 results/kv_rx_fault_dreg_1030 (only host_d/ing_d/ing_cls unproven by design).
- kit LEC (kit lec.py, new RTL vs 1_2_yosys.v): EQUIVALENT 19250/19250 (kit_lec_1030.txt; baseline kit 19249, +1 = fault_q).

Kit: copy of Codex rx259 (intel1 codex-kv-hr-1030/rx259 = kit259sw + rx259_pre_detail fault site), ONLY the RTL swapped.
Pins = kit259sw/rx259 pins.json 97803f86 (plan r26q5 + the 2 HELD pin deltas), outline 259.2 = plan of record.

Placed TT STA, like-for-like (placed_sta.tcl: 3_place.odb + 3_place.sdc, TT RVT libs, placement RC, ideal clock):
- baseline rx259: WNS -185.34, TNS -72545, 1324 violating EP (1208 host_d/ing_d data-capture EP)
- fault_dreg:     WNS -175.88, TNS -519,   12 violating EP (7 data EP)
Remaining worst = fault DETECTION cones (base_fault/D, retimed fault output, queue_fault/D, deferred), which the
data-enable register does not touch (baseline routed worst was rd[446] -> base_fault/D -37.76 too).
