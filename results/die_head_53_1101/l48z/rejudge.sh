#!/bin/bash
# re-judge an existing AUTO-GEOM dir (geom.tsv + grt.log + check.json) with the given tools dir geom_rules.py (no OpenROAD)
# usage: rejudge.sh TOOLS GEOMDIR KITDIR OUTJSON
T=$1; G=$2; K=$3; O=$4
mapfile -t RA < <(python3 -I -c "import json,sys;[print(a) for a in json.load(open(sys.argv[1])).get(\"rules_args\",[])]" "$G/check.json")
ODB=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1]))[\"odb\"])" "$G/check.json")
GMAX=$(sed -nE "s/^export MAX_ROUTING_LAYER *\??= *(\S+)/\1/p" $K/config.mk | tail -1); GMAX=${GMAX:-M5}
GA=(); [ -f "$G/grt.log" ] && GA=(--grt-log "$G/grt.log")
if [ -f "$K/ft_interface.json" ] || [ -f "$K/ft_ports.json" ]; then GA+=(--ft-interface "$K/ft_interface.json" --ft-ports "$K/ft_ports.json"); fi
if [ -f "$K/land_slots.json" ] || [ -f "$K/face_guard.json" ]; then GA+=(--land-slots "$K/land_slots.json" --face-guard "$K/face_guard.json"); fi
python3 -I "$T/geom_rules.py" "$G/geom.tsv" --odb "$ODB" --json "$O" --max-layer "$GMAX" "${GA[@]}" "${RA[@]}"
