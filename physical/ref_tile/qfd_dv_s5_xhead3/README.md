# qfd_dv_s5_xhead3

See results/arch/qw_s5_xhead_1021/README.md (successor of qfd_dv_s5_xhead; census PASS max 32, depth 365.1 ps; +1 edge priced).
Safe-design checklist: spec.json "safe_design_checklist" (pins/reach/fanout/depth/storage PASS; pin-bound util; one centre-fed root; +1 edge schedule).
Note: textbook reset_landing WARN: rst_n reaches 14 async clears (ot_rst_relay standard: 2 sync + 12 kept relay copies), release synchronous.
