#!/bin/bash
set -eu
W=/srv/opentallas-scratch2/claude/wt/codex-qc-su-trials
B=/srv/opentallas-scratch2/claude/codex-qc-su-trials
cat > "$B/cts_only.sh" <<'SH'
#!/bin/bash
set -eu
[ "${2:-cts}" = cts ] || { echo 'CTS-only diagnostic runner: refused non-CTS scope' >&2; exit 2; }
exec bash "$1/run_kit.sh" "$1" cts "${3:-64}" "${4:-16}"
SH
while read -r module pid kit; do
 python3 "$W/tools/autopilot/enqueue.py" --die qwen_compute --type "$module" --kit "intel2:$kit" --src codex/qc-su-trials-1101@2969e602396e74523bd0c46837db2ffbcfdbc225 --geom PASS-COND --geom-ref "VIEWED results/geom_review/codex_qc_su_lanes_1101.json; prototype CTS only" --mem 64 --cells 260000 --lane CODEX-QC-SU --goal cts --runner "$B/cts_only.sh" --threads 16 --mode adopt
done < "$B/jobs.tsv"
