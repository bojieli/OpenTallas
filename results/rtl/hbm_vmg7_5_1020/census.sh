#!/bin/bash
# census.sh <gate_dir> <top> <out.json>   (runs on the data host; native_census.py beside it)
set -eu
G=$1; T=$2; O=$3; A=$(dirname "$(realpath "$0")")
SL=$(find "$G" -name 1_1_yosys_canonicalize.log | head -1); NL=$(find "$G" -name 1_2_yosys.v | head -1)
mapfile -t LIBS < <(sed -n 's/.*Executing Liberty frontend: //p' "$SL" | sort -u)
ARGS=(); for p in "${LIBS[@]}"; do ARGS+=(--liberty "$p"); done
echo "netlist $NL libs ${#LIBS[@]}"
docker run --rm -v /srv:/srv:ro ${SRCMNT:+-v $SRCMNT:/src:ro} -v "$A:/audit" openroad/orfs:asap7lock python3 /audit/native_census.py --netlist "$NL" --top "$T" "${ARGS[@]}" --out "/audit/$O"
