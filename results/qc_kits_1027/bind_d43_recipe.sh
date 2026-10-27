#!/bin/sh
# QC-KITS-1 2026-10-27: strict bind for the QC plan event (QC.BIND), run as soon as INFRA-FIRST-QC adopts plan_d43.
# Run from a repo checkout at the adoption commit, on a fleet host (bind.py --mem; not localhost).
#   PLAN     = the adopted plan (physical/die_plan/qwen_compute/die_plan.json at the adoption commit)
#   MANIFEST = the ONEQC landing bind manifest (today only on codex/qc-land-phase-1026@5ac246973; must land with the plan event), repo-relative (manifest_paths PASS required; bind.py refuses otherwise)
# plan_d43 leaves partition_types and ports byte-identical to its base candidate_oneqc0733 (CHECKED, sha1 per type),
# so the d43 delta itself needs no manifest change; only origins/channels move.
set -eu
PLAN=${PLAN:-physical/die_plan/qwen_compute/die_plan.json}
MANIFEST=${MANIFEST:-physical/die_plan/qwen_compute/bind/asbuilt_landing_probe_1026.json}
OUT=${OUT:?set OUT=/srv/opentallas-scratch2/claude/qc-bind-d43/<sha>}
python3 tools/die_plan/manifest_paths.py --kind bind "$MANIFEST"
python3 tools/die_plan/bind.py all "$PLAN" --asbuilt "$MANIFEST" --strict --mem 48 --out "$OUT"
python3 tools/die_plan/bind.py portbind "$PLAN" --asbuilt "$MANIFEST" --strict --out "$OUT"
python3 tools/die_plan/manifest_paths.py --result "$OUT"/provenance_*.json
# then per type: bind.py kit-rtl "$PLAN" --asbuilt "$MANIFEST" --out "$OUT" --type T [--variant T__vN] (S81 BLOCKER B: kits need this)
