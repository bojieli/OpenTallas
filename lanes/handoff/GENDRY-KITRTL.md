# GENDRY-KITRTL handoff (lane split from KV-ALLFIX by COORD 11-23 ~20:40 PST)
Job: PRE GENDRY false FAILs on KV kit-RTL types (kv3_hg*/hgi*/hroot, "bus o_ectl_Q_N_eN not bound to any leaf port").
Fix (lane clones epyc10+epyc11 /srv/opentallas-scratch2/claude/gendry-kitrtl/wt, tools/die_plan/plan_gate_pre.py + test_pre_gendry_1123.py):
- kit-RTL type = buses but no bus.leaf and no contents[].bind. With --elab-dir = error-free bind OUT: bind.py kit-rtl -> gen phys --kit-rtl (real path).
  Without: WARN GENDRY-KITRTL (classified, not FAIL). Normal types unchanged.
- A3e PRE with fix: FAIL GENDRY 24 -> 0, PLAN-GATE-PRE PASS (tmp/pre_a3e/pre.log on epyc10).
- In flight 20:5x: old-vs-new GENDRY on S81 plan_fill (s81-allfix-svc tapinv_f5) + QC v4e; bound-path demo on KV D28 bind.
Next: push via ot-push-main from epyc10 clone (pytest there), sha -> FLOW-OPS-R3.
