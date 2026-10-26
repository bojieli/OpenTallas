#!/bin/bash
# SQ-QBIND2 10-21: GEN post-step of the Qwen compute die -- strict bind, then the netlist-proven open-output role
# contract (q_open_roles.py v2) written beside the netlist as DIE_V.pads.json (read by tools/die_port_bind.py and carried
# into the chain case by rsync), then the strict bind again.  Exit = the final strict bind's exit (0 only on PASS).
# Undeclared (functional) opens keep failing.  usage: q_open_roles_step.sh DIE_V OUTDIR   (env as port_bind_compute.sh)
set -u
D=$(readlink -f "$1"); O=$(mkdir -p "$2" && readlink -f "$2"); H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../.." && pwd)
[ -e "$D.pads.json" ] && { echo "q_open_roles_step: $D.pads.json exists (GEN-emitted); refusing to overwrite"; exit 2; }
bash $H/port_bind_compute.sh "$D" "$O/pre" > "$O/pre.line" 2>&1; pre=$?
grep -q 'output_open_ports=[1-9]' "$O/pre.line" || { cat "$O/pre.line"; exit $pre; }
python3 $H/q_open_roles.py "$D" --port-bind "$O/pre/port_bind.json" --src "$R" --out "$D.pads.json" > "$O/roles.line" 2>&1 || { cat "$O/roles.line"; exit 3; }
head -c 600 "$O/roles.line"; echo
bash $H/port_bind_compute.sh "$D" "$O" > "$O/final.line" 2>&1; rc=$?
cat "$O/final.line"; exit $rc
