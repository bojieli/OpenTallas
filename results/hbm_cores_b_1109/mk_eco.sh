#!/bin/bash
# on epyc4: write one ECO script per kit
set -eu
B=/srv/opentallas-scratch2/claude/kw37/eco; mkdir -p $B
for spec in "t24c slice_station__t24__cleece78ec" "t29 slice_station__t29__clc7772371"; do
set -- $spec
OV=""; [ $1 = t29 ] && OV="--owner-override"
cat > $B/eco_$1.sh <<EOS
#!/bin/bash
# KW-FIX-37: ONE late ECO on $2 (R4 census: few core-owned hold endpoints, rest parent-owned).
# t29 only: --owner-override, authority [COORD] OWNER RULING 17:5x (2) STANDING: non-port hold -32.85 vs -30 bound on 8 endpoints.
set -euo pipefail
K=/srv/opentallas-scratch3/claude/kw26-wave-1106/runs/s81/kit-wave/s81/e9eda32d41c/items/$2/attempt_14/gen/$2
O=$B/$1
S=/srv/opentallas-scratch2/claude/kw37/tools_eo/tools/die_plan
test ! -e "\$O"
python3 -I "\$S/eco_loop.py" check "\$K/signoff/signoff.json" || true
export OT_HOLD_REPAIR_SCOPE=nonport OT_FLOW_TAG=flow-20261108-eo-s81
unset OT_MARGIN_POLICY
exec python3 -I "\$S/eco_loop.py" run --kit "\$K" --signoff "\$K/signoff/signoff.json" --out "\$O" --max-iter 1 --strict-one-pass --from route --hold-margin 10 --mem 56 --cpus 16 --keep --lec $OV
EOS
chmod +x $B/eco_$1.sh
done
ls -la $B
