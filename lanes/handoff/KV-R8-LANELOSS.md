# KV-R8-LANELOSS handoff (COORD split from KV-ALLFIX, 11-23 20:0x PST)
Job: bind drops lanes on R8 clones (A2g 3857747ea992 pc_EN_7 L495 native_istations refusal).
ROOT CAUSE: tools/die_plan/bind_plancells.py PlanCells aliased plan_cells.json rows only via landing_base_type;
R8/param clones (param_base_type) of plain types got NO plan cells -> their plan-cell out buses unreserved -> lanes empty.
A2g affected: kv3_pc_v3 x4 clones, kv3_hg_v1 x3, kv3_hg_v1p3 x3 (13 partitions). __cl__r8 clones OK.
FIX: commit 70be023f9e2 in epyc10 /srv/opentallas-scratch2/claude/kv-r8-laneloss/wt (plan_cell_types + tests).
Repro: epyc8 /srv/opentallas-scratch2/claude/kv-r8-laneloss/repro/{base,fix} (repro.sh, wrap.py dumps lanes_unused).
Next: confirm fix bind passes native_istations; ot-push-main; tell FLOW-OPS + KV-ALLFIX.
