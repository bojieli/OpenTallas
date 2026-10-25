set -u; cd /srv/opentallas-scratch2/claude/wt/tok-ds-i13-1025
for c in base:: i13_554:--components\ /srv/opentallas-scratch2/claude/wt/tok-ds-i13-1025/results/token_pass/tokds_i13b_price_1025/comp i13_612:--components\ /srv/opentallas-scratch2/claude/wt/tok-ds-i13-1025/results/token_pass/tokds_i13b_price_1025/comp612; do n=${c%%:*}; a=${c#*:}; a=${a#:}
python3 tools/s81_dv/tokfunc/compose_tok_ds.py $a --out /srv/opentallas-scratch2/claude/tok-ds-price/i13b/$n > /srv/opentallas-scratch2/claude/tok-ds-price/i13b/$n.log 2>&1; echo "$n rc $?"; done
