#!/bin/bash
# Minimal native AM/FSM + RELAY4 cohort proof; run through ot-run.
set -eu
R=$(cd "$(dirname "$0")/../../.." && pwd)
O=$1
[ ! -e "$O" ] || { echo "refuse existing proof output $O"; exit 2; }
mkdir -p "$O"
cp "$(dirname "$0")/tb.sv" "$O/tb.sv"
python3 -I "$(dirname "$0")/prepare.py" "$R" "$O"
cd "$O"
for kind in good short_relay short_reset;do
 args=""
 [ "$kind" != short_relay ] || args="-P tb.RN=3"
 [ "$kind" != short_reset ] || args="-P tb.RRESET=3"
 iverilog -g2012 -DOT_S81_KP4_AM_FACE3 $args -s tb -o "$kind.out" tb.sv old_literal.sv reset_literal.sv face_literal.sv good.sv > "$kind.build.log" 2>&1
 if vvp "$kind.out" > "$kind.log" 2>&1;then
  [ "$kind" = good ] || { echo "MUTANT_SURVIVED $kind";exit 1; }
 else
  [ "$kind" != good ] || { cat "$kind.log";exit 1; }
 fi
 tail -2 "$kind.log"
done
