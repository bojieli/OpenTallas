#!/bin/bash
set -eu
R=/srv/opentallas-scratch/claude/codex-native-census-1020
V=/srv/opentallas-scratch/claude/codex-kv-hroot-safe32-1020
mapfile -t LIBS < <(sed -n 's/.*Executing Liberty frontend: //p' "$V/native_synth_hook.log" | sort -u)
ARGS=();for p in "${LIBS[@]}"; do ARGS+=(--liberty "$p"); done
docker run --rm -v /srv:/srv:ro -v "$R:/audit" openroad/orfs:asap7lock python3 /audit/completecand/tools/ref_tile/native_census.py --netlist "$V/native_orfs/results/asap7/qkd_kvs_hroot_safe32/base/1_2_yosys.v" --top qkd_kvs_hroot_safe32 "${ARGS[@]}" --out /audit/hroot_v3_census.ship.json > "$R/real_hroot.ship.log" 2>&1

sha256sum "$R/completecand/tools/ref_tile/native_census.py" "$R/completecand/tools/textbook_lint.py" > "$R/real_hroot.ship.tool.sha256"
