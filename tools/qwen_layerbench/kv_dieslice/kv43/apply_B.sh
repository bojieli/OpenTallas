#!/usr/bin/env bash
# usage: apply_B.sh STAGED_TREE      (e.g. epyc2:/srv/opentallas-scratch2/claude/kv-tok/kv43, a COPY of kv42)
# KV-TOK B 2026-10-24: apply KV boot fix B (controller boot window, rtl/qwen_sys/static_kv_20261014) to a staged vehicle
# source tree in place.  Every staged copy (src/*static_kv_20261014/<file>, incl. the extra__ copies) of the four changed
# files must be byte-identical to the ORIGINAL (sha256 below, = repo b1131f6fa) -> replaced by this repo's version, or
# already identical to this repo's version -> left alone (idempotent).  Anything else is an error (nothing written).
# Prints every file changed.  Staged paths / files.f are unchanged (same file names), so no list edit is needed.
set -euo pipefail
T=${1:?usage: apply_B.sh STAGED_TREE}; [[ -d $T/src ]] || { echo "apply_B: $T/src missing" >&2; exit 2; }
R=$(cd "$(dirname "$0")/../../../.." && pwd); S=$R/rtl/qwen_sys/static_kv_20261014
declare -A OLD=(
 [ot_qkd_static_kv_timing.sv]=ed202e8000388e48b7feda209c38382b5991386bf6d209b5a03ec88dd2abbce4
 [ot_qkd_static_ctrl_pc_emb.sv]=89bc7a0f33d0b2e071f3cba55e236d9d262cc6659b820319acb9767b1bd9fe5b
 [qkd_ctrl_pc_nc.sv]=14d5d335fc805eb6a39850b05d827001dbca31091c3e9e5758b4ee5db7e0d7b8
 [qkd_ctrl_pc_host_static_core.sv]=f1447f7011da1da58835db48cb2dd7323d6afd0ea58a91b5384d0d3b83a3fccb
)
echo "apply_B: repo $R @ $(git -C "$R" rev-parse --short=10 HEAD 2>/dev/null || echo '?') -> $T"
todo=(); bad=0; n=0
for f in "${!OLD[@]}"; do
  new=$(sha256sum "$S/$f" | cut -c1-64)
  [[ $new != "${OLD[$f]}" ]] || { echo "apply_B: repo $f is still the original" >&2; exit 2; }
  while IFS= read -r c; do
    n=$((n+1)); h=$(sha256sum "$c" | cut -c1-64)
    if [[ $h == "$new" ]]; then echo "  unchanged (already B) $c"
    elif [[ $h == "${OLD[$f]}" ]]; then todo+=("$f|$c")
    else echo "apply_B: UNEXPECTED content $c (sha $h)" >&2; bad=1; fi
  done < <(find "$T/src" -path '*static_kv_20261014*' -name "$f" -type f | sort)
done
[[ $n -gt 0 ]] || { echo "apply_B: no static_kv_20261014 copies found under $T/src" >&2; exit 2; }
[[ $bad == 0 ]] || { echo "apply_B: nothing written" >&2; exit 3; }
for e in "${todo[@]}"; do f=${e%%|*}; c=${e#*|}; cp "$S/$f" "$c"; echo "  CHANGED $c"; done
echo "apply_B: ${#todo[@]} file(s) changed, $((n-${#todo[@]})) already B"
