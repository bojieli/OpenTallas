# SYS_C static count-strap sites

The current plan declared 25 static count straps (140 bits) without physical sites. Existing main helper `physical/die_plan/qwen_kvsys/g3/kv_count_strap_sites.py` assigns exact M7 sites, using the actual 6237 planned public pins and explicit macro/clock blockers. Only SYS_C count_straps layer/sites fields change. Current bound RTL, parameters, source, public signal pins, macro locations, outline, clock, reset and cycles remain identical.

140 unique sites occupy y=4.32um and x=21.600..324.064um at 2.176um pitch. Personally rendered and viewed `review.png`: clear bottom strip, no macro wall or clock entry interaction introduced. Independent GEOM review PASS-COND: public-pin minimum distance51.424um, macro minimum246.24um, explicit clock entry/sink minimum247.128um, edge-clock row separation17.28um; full actual source/placement gates remain.

Current SYS_C synthesis frontgates passed bind6377/6377, FACE5015/5015, register fanout47901 none>64. Current-cohort LEC continues on intel1 `codex-kv-1030/kit_sysc_current/gen/kv3_sys_c`; the earlier94233-point result is a distinct TXDP parameter cohort and provides no current-source credit. No P&R has been launched.

Actual G0C same current source/assets: baseline43errors/2056warnings and candidate43/2056, zero new or removed findings. Remaining43 errors are missing type cell estimates. See g0_delta.json. Independent geometry receipt is on codex/geom-1030; no P&R adoption follows until root review.
