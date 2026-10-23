set -u; W=/srv/opentallas-scratch/claude/qw-l1k-1020; C=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f20g5/chain
python3 $W/reset_release_check.py --die-v $C/dieclk/die.v --setup $C/sta_r22k_tt/grt_tt_summary.rpt --hold $C/sta_r22k_ff/grt_ff_summary.rpt --out $W/reset_release_g5.json --diagnostic g5_terminal_fail_old_die
for r in dv2f20g5r2b dv2f20g5r2; do python3 $W/reset_release_check.py --die-v /srv/opentallas-scratch/claude/mu-die-qw/$r/p2/die.v --out $W/reset_release_${r}_static.json --diagnostic ${r}_static_pre_sta; done
