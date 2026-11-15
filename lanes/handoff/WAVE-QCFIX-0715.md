# WAVE-QCFIX-0715 handoff (07:4x PST 11-15)

Lane goal: stop the pre-P&R kit-wave failures (count frame, pruned HDL, VIEW-MISSING, prov_view not staged, GEN_LINT).

## Root causes
- Count frame (62 qwen_compute; KV never asks for the s29 frame): plan zz_s29_qc103_s4p.json lives in die-qc-103/treeA/.../plan_of_record; count_frame._resolve looks next to the plan, so feed_s29.json / regions_s29.json had to be in the same dir on each gen host. They are now on epyc10/8/7/2/intel1 (+epyc9). Fails stopped 07:03. KV fails are other classes: schema.full_area_hard_ip (stopped ~06:44), strap_r8pad ValueError (kv3_pc_v3), STALE-CORE-VIEW (kv3_hub_C): not in this lane.
- Pruned HDL / "leaf modules without a source": die-qc-103/treeA/rtl was a 54-file sparse tree on every gen host except epyc9 (10950 files). Add-only rsync from epyc9 to epyc10/8/7/2/intel1 (no delete): all 10950. gsafe.sv itself had been restored ~06:27 by someone else (treeA/rtl/hdc,lib,rom mtimes 06:27-06:30).
- prov_view not staged: treeA/physical sparse (181 vs 6454 files). rsync --max-size=30M from epyc9 to the 5 hosts done (plan jsons >30M not copied; the plan itself is already there).
- VIEW-MISSING: rk2/sle_cland_w517_n_s10_1/kits/..._synth0/views had only libs; the LEF existed under run/results/asap7/.../base. Copied into views/ on epyc10 (no deletion).
- GEN_LINT ot_rst_relay: module exists in qc-s29-tree2/rtl/lib; likely same sparse-source cause; re-prove on a released item.
- kit_rtl of record is still S4PQ (KIT-OPS-5 owns the S4q2 swap, DIE-QC-103 R8/LATCHECK pending); not changed here.

## kit_wave.json
- Hold: 28 items (dies.*.hold_items, text starts "WAVE-QCFIX-0715 hold") pushed 8e8910207d0e.
- Batch 1 release: 8 items (2 per class) pushed 6e68b066bc7e. 20 still held.
- Release rest (python /tmp/wq_rel.py b2 on intel2; sel list /tmp/wq_sel.json) after batch-1 items pass their step.
- Replicating bind-chain inputs (tree7, wt_r8pin, qc-s29-reach, die-qc-103 top-level scripts, r8 seeds, bind_s29q101P) epyc9 -> epyc10: log epyc9:/tmp/wq_repl_epyc10.log, script /tmp/wq_repl.sh <host>.
