# DO NOT USE the 10-21 element list (owner 2026-10-24 07:45 PDT)
The 10-21 release tree element table predates the top-down (plan-first) flow and is obsolete. The open items are what
the CURRENT die plans say is unclosed:
- G0C failures on main (check.py --completeness): S81 v4.8 91 types without hard_cores (S81-CORES), QC 4 ft_budget types,
  KV kv3_hub_Wi cores without pins, HBM B2r2 (49/49 clean, 344 cores unchecked).
- G3: every partition type / hard core of the current plans (physical/die_plan/{s81,s81_head,qwen_compute,qwen_kvsys}
  and hbm_arch B2r2) that has no SIGNED closed view through the new kit gates (main 4b7b2b3e64+). Lane SIGNOFF builds
  that inventory (results/signoff_1024).
