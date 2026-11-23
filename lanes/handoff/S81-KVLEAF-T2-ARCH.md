# S81-KVLEAF-T2-ARCH handoff (Fable; root cause + one structural fix for S81 ot_s81sl kv_leaf t2)
Brief + rules: localhost scratchpad rules.txt (session c228d9e1). Lane dir: intel2 /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch (wt = lane clone, branch s81-kvleaf-t2-hardkv; synth1 = hier synth; eq1 = HARD_RQ 0/1/2 structural compare).
## Findings (11-23 04:2x, posted hub 3af9daa6)
- t2 = ordinary leaf + D512 KV bank (ot_s81sl_kv_bank CNIK=1 HARD_RQ=0) + compressor pool. Arithmetic, not a flop store; storage is already 183 SRAM macros.
- Cause: plan row t2 has no hard_cores and the die slice top ot_s81sl_slice_sukv_raw512_w3 passes KV_HARD_RQ 0, so 64 norm engines + 16 quant + taps + trees + writers + 8 pool lanes are flattened into one soft run. The bank was designed and CLOSED (10-12/13, 833 ps) as small masters: physical/ref_tile/s81su_{kvt,kve,kvp,kvr,kvq,qnh}_ref with LEF/lib views.
- Area claim 9.1 mm2 is wrong (0.979 um2/cell includes t5 hard macros); measured 0.11-0.13 um2/cell. Masters footprint 2.28 mm2 in a 5.31 mm2 slot. No die growth, no 28-piece cut.
- Unique to t2 (t1/t3/t4/t5 have no bank; 23 hard cores each).
## Fix = hierarchy (option d)
- RTL draft in wt (NOT pushed yet): HARD_RQ >= 2 in ot_s81sl_kv_bank picks masters for kvt/kve/kvp/qnh/cn_write/ik_write/ik_reduce (new file rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_kvcn.sv: dsfd_su_t_kvtc/kvec/kvpc/cnw/ikw/ikr), pool HARD=1 -> dsfd_sl_t_cpl x8, slice top sukv_raw512_w3 sets KV_HARD_RQ(2). Soft instance names unchanged for HARD_RQ 0 kve and pool lanes.
## Jobs
- synth1 (ot-run intel2, docker s81kvt2arch_synth1): hier yosys of kv_leaf -> per-master mapped cells + soft residue. Output synth1/stat_mapped.txt.
- eq1 (docker s81kvt2arch_eq1): flatten stat for HARD_RQ 0/1/2 must be equal (wrappers are renames).
## Next
1. Read synth1/eq1; post measured composition + row/RTL plan with owner + ETA to COORD, FIX-LEDGER, FABLE-RC-S81.
2. Run tools/s81_dv/rtlgap_sukv_1021/hard_rq.py form with HARD_RQ=2 (Verilator, ot-run) if fixtures found; then push via ot-push-main with tests.
