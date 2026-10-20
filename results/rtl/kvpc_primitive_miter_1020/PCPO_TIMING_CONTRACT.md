# sr8 pc__po producer and consumer timing contract (pending audit)

Gate-Rule: documentation only; no RTL/helper, gate requirement, runtime comparison, or admission change. R7 positive failures remain failures. This contract does not qualify primitive sr9 or authorize a payload mask. R8 actual state audit remains prerequisite.

Source scope is the sr8 nc producer retained on branch codex/kvpc-primitive-miter-1020 (base a88b67879), not the active PC6 interlude or its SRAM clones. qkd_static_kv_pc_path_nc.sv:100 explicitly instantiates CVL=2; controller child clocks carry the same HBM clock. Primitive input source binding must still be checked against the frozen original.v before a runtime qualifier is admitted.

Use HBM edge E as the edge after which scheduler po[28] first presents a particular column. Table values describe state immediately AFTER that edge; pre-edge sampling is explicit below. Let C be the scheduler pre-edge col_v/col_we/col_sr at E.

| Edge | Producer event for C (CVL=2) |
| --- | --- |
| E | Scheduler po captures C into column fields and dv[0] captures C. po[327:40] independently captures old p_wd. |
| E+1 | dv[1] captures C; p_col is dv[CVL-1]=dv[1]. |
| E+2 | Port-child col_v_q/col_we_q/col_sr_q captures C. |
| E+3 | Inner port samples that column. Static WR: st1_wd captures selected wq entry and wc1_st becomes 1. KV WR: wc1_kv becomes 1. |
| E+4 | Inner s2_wd captures st1_wd for static WR or zero for KV WR, using old wc1_st/wc1_kv. This is the documented two-edge data timing after the port's registered column at E+2. |
| E+5 | Scheduler po[327:40] captures that s2_wd. Thus external po write data is meaningful five edges after the external WR column for CVL=2 (generally CVL+3). |

Exact source: qkd_ctrl_pc_nc.sv:184-196 dv pipeline; 255-258 po concat; 323-338 port-child boundary; 414-452 wr_static/wr_kv, st1_wd/s2_wd, wc1 qualifiers. st1_wd and s2_wd are unreset and hold without their update enables. wq writes only on w_v and reads on wr_static; empty/full protocol errors independently set fault. A KV WR is a protocol fault and supplies zero on its data slot. Reset clears the wc1 enables but does not establish a defined idle value for s2_wd. Consequently an idle po payload may reflect arbitrary pre-reset history without being a legal write transfer.

Payload producer validity is the corresponding earlier WR column (po[28] && po[29]) at the five-edge relation, not current po[28]. A candidate future monitor must retain both designs' command equality, check the delay and reset cancellations against actual landing resets, and prove meaningful-slot coverage. It must not synthesize a blanket initial-cycle exclusion, assume cleared SRAM, or ignore control/fault differences. A source/hash/parameter binding and mapped first-use analysis remain owed.

Consumer cross-check: qkd_ctrl_pc_obs_child in qkd_ctrl_pc_host_static_core.sv:1141-1167 captures po/static/context at its registered boundary. qkd_static_kv_write_observer.sv:15-16 defines command=po[28]&&static_column, native_write=command&&context_word[346]&&po[29]. valid shifts at each edge; the comparison uses pre-edge valid[4]. Therefore a command displayed externally after E is captured by the observer boundary at E+1, enters valid[0] at E+2, reaches valid[4] after E+6, and is checked at E+7 against pre-edge observer po_q captured from external po at E+6, i.e. payload made available after E+5. This agrees with the producer's five-edge relation. It is not a same-cycle validity predicate. The observer only checks native static writes; it is not a complete external write-data admission theorem.

Unconditional comparison contract: po[39:0] in full (row_v/op/bank/row, column_v/we/bank/column), every other output/control/fault/credit bit, and er/her valid + fault/credit bits remain compared. Existing er/her[258:1] remains qualified only by their own bit0 valid. Any future WD comparison change must preserve these checks through domain resets and stopped-clock episodes.

Required causal payload negative: invert or permute actual DUT po[327:40] only during a proven meaningful WR-data slot; the positive must pass, and the negative must fail at that data slot with the same command/reset history. An idle-startup payload corruption is insufficient. Existing output-fault inversion/reset/macro mutants do not substitute for this WD-specific witness.

First-use obligations still open: actual R8 phase0 architectural relation; earliest retained state divergence; all 80 independent new-copy states and architectural SRAM array/read-register relation; each copied control's reset/first-use admission dominator; source-to-frozen-netlist/parameter binding; meaningful WR-data coverage and WD-specific mutant. No proof/admission claim is made here.

Source hashes:

- rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_nc.sv: `14d5d335fc805eb6a39850b05d827001dbca31091c3e9e5758b4ee5db7e0d7b8`
- rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv: `16ac2306ab9b5e707c276042080c03225ab04773f43169d376905c05b0508f0f`
- rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static_core.sv: `f1447f7011da1da58835db48cb2dd7323d6afd0ea58a91b5384d0d3b83a3fccb`
- rtl/qwen_sys/static_kv_20261014/qkd_static_kv_write_observer.sv: `b86f14f5e7e007e5e07b3d80ebd3787f5cbae669e94b984f887d4bef29cd06ca`
