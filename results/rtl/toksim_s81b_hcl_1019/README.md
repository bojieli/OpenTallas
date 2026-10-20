# TOKSIM-S81B/HCL (10-19): HC loads / embed / head misc / MTP draft on the S81 release RTL (GEN mu4c 19bf4121e)

Record: HCL.json (copy of scratch/toksim-s81b/elements/HCL.json). Job: ot-run ot-epyc9 oth-ubuntu-699183-1792462770, job_hcl.sh,
Verilator 5.050, src = git archive 19bf4121e (every executing file is release by construction).

- A. tb_toksim_hcl_beat.sv = rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_beat.sv@19bf4121e + timers + HLS/GS plusargs; all original golden
  checks kept (leaf_gold.py on real 1M L0/L2 chains). logs/job_hcl.otrun.log: HLOAD 21, GAIN 13, HSTORE 24, RDOUT 21; HLOAD->GAIN
  spacing floor 17 (16 FAILs: vp busy fault), GAIN->NORM 6 passes (sweep floor); go->partial 112, rstd->xb 79.
- B. run_gunit_bench.sh@19bf4121e: hc_lat 748 (stop pins), GUNIT_GATE PASS, mutants 1/4/5/6/7/8/9 detected (logs/gunit.txt).
- xfin16 247 (234 + spread 13) collected from TOKSIM-S81/SU (logs/xfin16_su.txt, ot-epyc7 out_slice/xfin16.txt).
- embed 323 collected (origin/main results/rtl/dsrom_1m_allmeasured_20261004/embed.json, blob-identical to release; no die instance, G9).
- head.argmax_merge: coll node, composed only from base xdie terms (119 measured + 453 PHY + 134 on-die leg = LEG lane). Not HCL.
- mtp.draft_blocks: draft_map.json (tools/s81_dv/toksim_hcl_draft_map.py): 0/192 draft nodes match a layer node's old cycles; release
  records apply only under a placement ruling (draft on p4l layer-class dies). Kept measured-old-RTL; no run launched (same RTL/shape).
