# SVGR owner RF1 conservative form

Collected predecessor HBM-GAPS-5-LEC proof on epyc5 /srv/opentallas-scratch2/claude/hbm-gaps-5-lec/bench, res_rf1.txt. Existing ordinary and landing-stall smoke: old0/old1/rf0/rf1 PASS20/20ops,29/29go,81results,0fault;7/7owner mutants fail. Default-off source resolves byte-identical to main.

OT_SVGR_OWN_RF1 registers descriptor dispatch before K issue, K response head, and response-take count; kept per-lane one-hot arbiter cuts wide select fanout. PIN CYCLES: first K request per descriptor +1hbm_clk; each K response +1hbm_pc_clk; bank next-descriptor availability +1hbm_clk. No arithmetic changes. A refused response remains at skid head and faults stop the die. Physical closure and production throughput are pending; do not count this source form as signed off.
