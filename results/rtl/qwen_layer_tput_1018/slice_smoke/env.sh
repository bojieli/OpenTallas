F=/srv/opentallas-scratch/claude/layerbench-qwen-1018
CS=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f14bn
CDIE=$CS/chain/case_r22k/die.v; CBIND=$CS/chain/port_bind/port_bind.json; CSRC=$CS/src
KP=/srv/opentallas-scratch/claude/qwen-kvsys/kvs14c-place
KDIE=$KP/port_bind_v2/die_bound.v; KBIND=$KP/port_bind_v2/port_bind_v2.json; KSRC=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14-f05f9338f
CUT="python3 $F/tools/qwen_layerbench/slice_cut.py"
