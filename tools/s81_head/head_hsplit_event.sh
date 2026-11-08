#!/usr/bin/env bash
# DIE-HEAD-84 HSPLIT (COORD 11-07 18:3x form A): hd_host -> hd_host_w + hd_host_e plan event on a HEAD plan of record.
# Reproduces the event from the plan of record + the merged HSPLIT RTL/delta (DH55/56/58, main):
#   1 head_host_split_delta.py (RAW split)          2 prep_compose: drop the old contract's pins/edge clocks, split sinks,
#     E START capture beside the die START origin   3 ca_split: count-aligned roles (host_e = sibling CA origin of host_w on
#     the same START parent; the seam is a synchronous same-region port, not a landing)   4 compose (region monitor,
#     ring_ff 2.0: on the base this reproduces every l48uo type up to the HEAD post-compose fields)   5 graft: the plan of
#     record byte-for-byte + the composed host records   6 raw START exports (die stages that read host raw relays)
#   7 count strap sites   8 head_cland_stage_delta (landing stage keys) + macro snap   9 private raw exports
#   10 start-tree uses   11 die START stages + completed die top   12 kits (gen.py phys + the wave export patches).
# usage: head_hsplit_event.sh PLAN_OF_RECORD_DIR OUT_DIR   (run from the repo root; fleet host, never localhost)
set -euo pipefail
B=$(realpath "$1"); O=$(realpath -m "$2"); [ -e "$O" ] && { echo "refusing existing $O" >&2; exit 2; }
T=tools/s81_head; PY="python3 -I"; mkdir -p "$O"
z() { if [ -f "$1.gz" ]; then zcat "$1.gz"; else cat "$1"; fi; }
mkdir -p "$O/base"; z "$B/source_plan.json" > "$O/base/source_plan.json"; z "$B/source_sidecar.json" > "$O/base/source_sidecar.json"
lnk() { for d in assets core_pins native_domains published; do ln -sfn "$B/$d" "$1/$d"; done; }
$PY $T/head_host_split_delta.py "$O/base/source_plan.json" --sidecar "$O/base/source_sidecar.json" --out "$O/split0"
lnk "$O/split0"; lnk "$O/base"
$PY $T/head_hsplit_prep_compose.py "$O/split0/source_plan.json" "$O/base/source_plan.json" "$O/split0/precomp_plan.json"
$PY $T/head_hsplit_ca_split.py "$O/split0/source_sidecar.json" "$O/split0/sidecar_ca.json"
$PY $T/head_hsplit_compose.py "$O/split0/precomp_plan.json" "$O/split0/sidecar_ca.json" "$O/comp"
mkdir -p "$O/g2"; $PY $T/head_hsplit_graft.py "$O/base/source_plan.json" "$O/base/source_sidecar.json" "$O/comp_plan.json" "$O/comp_side.json" "$O/g2"; lnk "$O/g2"
$PY $T/head_hsplit_raw_exports.py "$O/g2/source_plan.json" "$B/source/start_stages.json.gz" "$O/g3"; cp "$O/g2/source_sidecar.json" "$O/g3/"; lnk "$O/g3"
$PY $T/head_hsplit_strap_sites.py "$O/g3/source_plan.json"
mkdir -p "$O/kits3" "$O/wr3"; $PY tools/die_plan/gen.py phys "$O/g3/source_plan.json" --clock-landing "$O/g3/source_sidecar.json" --types hd_host_w,hd_host_e --rtl-root . --trial --out "$O/kits3" > "$O/kits3.log" 2>&1
$PY $T/head_hsplit_finish_kits.py alias "$O/g3/source_plan.json" "$O/kits3" "$O/wr3"
$PY $T/head_hsplit_split_rects.py "$B/macro_rects_hd_host.json" "$O/g3"
$PY $T/head_cland_stage_delta.py "$O/g3" "$O/g4" --types hd_host_w,hd_host_e --rrl-from hd_host_w="$O/wr3/ot_s81hd_host_w_ep.sv" --rrl-from hd_host_e="$O/wr3/ot_s81hd_host_e_ep.sv"
$PY $T/head_cland_stage_delta.py "$O/g4" "$O/g5" --snap-only --types hd_host_w,hd_host_e --macro-rects hd_host_w="$O/g3/macro_rects_hd_host_w.json" --macro-rects hd_host_e="$O/g3/macro_rects_hd_host_e.json"
cp -a "$O/g5" "$O/g6"; $PY $T/head_hsplit_finish_kits.py prepare "$O/g5/source_plan.json" "$O/g6/source_plan.json"
$PY $T/head_hsplit_fix_start_uses.py "$O/g6" "$O/g3/raw_exports.json"
mkdir -p "$O/g6/source"; $PY $T/head_hsplit_refresh_stages.py "$B/source/start_stages.json.gz" "$B/source/start_stages.sv.gz" "$O/g3/raw_exports.json" "$O/g6/source"
$PY tools/die_plan/gen.py rtl "$O/g6/source_plan.json" --clock-landing "$O/g6/source_sidecar.json" --rtl-root . --out "$O/rtl" > "$O/rtl.log" 2>&1
$PY $T/head_hsplit_complete_top.py "$O/g6/source_plan.json" "$O/g6/source/start_stages.json" "$O/rtl/s81_head_top.sv" "$O/g6/source/s81_head_top.sv"
$PY tools/die_plan/gen.py phys "$O/g6/source_plan.json" --clock-landing "$O/g6/source_sidecar.json" --types hd_host_w,hd_host_e --rtl-root . --trial --out "$O/kits" > "$O/kits.log" 2>&1
$PY $T/head_hsplit_finish_kits.py patch "$O/g6/source_plan.json" "$O/kits"
$PY tools/die_plan/check.py "$O/g6/source_plan.json" --out "$O/g0" --quiet || true
sha256sum "$O/g6/source_plan.json" "$O/g6/source_sidecar.json" "$O/g6/source/"* "$O/kits/_rtl/ot_s81hd_host_"[we]"_ep.sv" | tee "$O/SHA256SUMS"
