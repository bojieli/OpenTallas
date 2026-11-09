set -eu
# on intel2: stage P2g + macro-balancing-only form onto intel1
SRC=/srv/opentallas-scratch2/claude/codex-hbm-hard-0222/kit_opsa0_P2g
K=/srv/opentallas-scratch2/claude/hbm-hard-9/kit_opsa0_P2g_bal
ssh -n -o ControlPath=none intel1 "mkdir -p $K"
rsync -a -e 'ssh -o ControlPath=none' --exclude run/ --exclude lec/ --exclude 'lec_async.*' --exclude signoff/ --exclude physical_completion/ --exclude __pycache__/ --exclude '*.log' --exclude hold_census.txt --exclude placed.csv "$SRC/" intel1:"$K/"
rsync -a -e 'ssh -o ControlPath=none' "$SRC/lec_async.sh" intel1:"$K/"
# resume at CTS: keep results up to place, logs/objects as built
rsync -a -e 'ssh -o ControlPath=none' --exclude 'results/asap7/*/base/4_*' --exclude 'results/asap7/*/base/5_*' --exclude 'results/asap7/*/base/6_*' --exclude 'logs/asap7/*/base/4_*' --exclude 'logs/asap7/*/base/5_*' --exclude 'logs/asap7/*/base/6_*' --exclude 'reports/asap7/*/base/4_*' --exclude 'reports/asap7/*/base/5_*' --exclude 'reports/asap7/*/base/6_*' "$SRC/run/" intel1:"$K/run/"
