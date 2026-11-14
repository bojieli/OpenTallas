# DIE-PROTO-1 handoff (11-14 00:2x PST, Opus)
## Scope
Die GRT + die STA prototypes on all 4 dies, current plans, plan-shape abstracts (OWNER 11-14 00:4x / 11-11). ADVISORY, DO_NOT_COUNT.
## Running
epyc10 /srv/opentallas-scratch2/claude/die-proto-1b/{qwen_kvsys,s81,s81_head,qwen_compute}/cur1114/CHAIN.log (CHAIN_DONE at end).
Launcher: intel2 /tmp/dp1b_launch.sh, logs intel2 /tmp/dp1b_<d>.ot. Per die: $B/run_die.sh <kv|s81|head|qc> [tag] (sets W/P), $B/proto_die.sh (DIE-PROTO-2 chain, docker mounts all scratch2).
## Next
Read grt_st_{TT,FF}/combo_*.log (overflow per layer), sta/ summary json, kitwin.json; post RESULT per die; S81 re-run on B2u (die-s81-91) when bound: edit run_die.sh s81 W/P, tag b2u.
