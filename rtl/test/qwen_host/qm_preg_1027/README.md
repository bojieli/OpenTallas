# QK-CORES-6 task 4: qkd_hr_ingest_eng pin registers (2026-10-27)

RTL: rtl/qwen_sys/host_20261013/qkd_host_native_engine_preg.sv (wrapper around the unchanged
qkd_host_native_engine) + qkd_host_native_qm_debt.sv param ENG_PREG (default 0 = unchanged).
Die binding must set ENG_PREG=1 on u_host.u_qm (partition glue kv3_hub_Wi) when the preg core is used.

Faces:
- inputs d_v/d_data, in_v/in_data, rd_v/rd_data, w_rdy, r_rdy: one pin flop each (single capture).
  rd_data (256 b) KEPT, registered (no PATH-KV deadness proof).
- d_rdy, in_rdy: registered ready via 2-entry skid (port flop + private shadow).
- w_v/w_addr/w_data, r_v/r_addr, busy, done_v/done_tag/n_sectors: output port flops.
- n_beats: passthrough (constant-class in the hr cut, open in wrapper).

Cycle delta per bus (ck cycles, vs bare engine):
- d_*, in_*, rd_*, w_rdy: +1 (pin flop). d_rdy/in_rdy: 0 extra on beats, full rate (skid).
- w_v/w_addr/w_data, r_v/r_addr, busy, done_v/done_tag/n_sectors: +1.
- w handshake: ready-latency 2 (QM-side ox credit counter); per sector write +2 input->ox.
- Fixture end-to-end: last ox write cycle equal A vs B in all 9 configs (no throughput loss seen).

Bench: rtl/test/qwen_host/qm_preg_1027/run.sh OUTDIR [DEFINE]
- clean: QM_PREG_EQUIV_SUITE PASS 9/9 (1729 ordered ox words = 1728 sectors + marker, 9 t words, 9 dones)
- mutant QKD_IE_SKID_MUT (skid beat on wrong-cycle ready): FAIL 0/9
Data: intel2:/srv/opentallas-scratch2/claude/qk-cores-6/ingest/{bench,bench_mut}

Open: no [4,2] islands for qkd_hr_ingest_eng in KV plan hm_r26q5c (pin view centre entry only;
kv_core_slice grid [2,2], [4,2] candidate pred 242.3 ps TT only) -> KV-PLAN-DELTA ask. Kit/place not run.
