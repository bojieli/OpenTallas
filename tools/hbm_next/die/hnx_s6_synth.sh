#!/bin/bash
# Exact-source S6 recovery: preserve previous sources/builds, freeze this plan's wrappers,
# then synthesize into a distinct root. Never accept an old ETM log as a source receipt.
set -euo pipefail
B=/srv/opentallas-scratch/claude/hnx/die_p4
A=${A:-/home/ubuntu/artifacts/hnx/die_p4}
W=${W:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}
OTRUN=/home/ubuntu/bin/ot-run; SRC_COMMIT=${SRC_COMMIT:-42726f987}; V=$A/vplan_s6; MEMG=${MEMG:-8}
export OT_RUN_PRIO_ENV=""
# Unique run root: all source bytes remain immutable after launch, even across plan changes.
RUN=$(date +%Y%m%dT%H%M%S)_$$; R=$B/s6_$RUN
mkdir -p "$V/drive"
echo "STEP S6S exact_source $R $(date -Is) cells: $*"
ssh ot-epyc4 "mkdir -p $R; cp -al $B/src $R/src; mkdir -p $R/src/v16w; ln -s $R/src $R/src_$SRC_COMMIT"
# rsync writes a replacement inode: inherited hardlinks into older snapshots stay intact.
rsync -a "$V/wrap/" ot-epyc4:$R/src/v16w/
# The plan's generated wrappers are the exact synthesis source; no normalization or bypass.
pids=()
for c in "$@"; do
  w=$(awk -F'\t' -v c="$c" '$1==c{print $3}' "$V/jobs.tsv")
  m=$(awk -F'\t' -v c="$c" '$1==c{print $2}' "$V/jobs.tsv")
  [ -n "$w" ] || { echo "S6S_NO_JOB_ROW $c"; exit 21; }
  LC=""; case $c in hbfd_lh0_*|hbfd_land0_*) LC="LIBCELLS=1";; esac
  (
    "$OTRUN" --mem $((MEMG + 4)) --threads 4 --dir "$R/src" -- bash -c "echo HOST \$(hostname); env MEMG=$MEMG $LC HIER=1 EXTRA=v16w/$w.sv WTOP=$w bash tools/hbm_die_v15/synth_master.sh . $R/syn/$c $c $m - - && MEMG=$MEMG bash tools/hbm_die_v15/synth_etm.sh . $R/syn/$c $c" > "$V/drive/$c.$RUN.log" 2>&1
    echo "SYNTH $c DONE $(date -Is)"
  ) &
  pids+=("$!")
  # Keep the local process count bounded; computation runs only on the fleet.
  if [ "${#pids[@]}" -ge 5 ]; then
    for pid in "${pids[@]}"; do wait "$pid" || { echo S6S_BUILD_FAIL; exit 16; }; done
    pids=()
  fi
done
for pid in "${pids[@]}"; do wait "$pid" || { echo S6S_BUILD_FAIL; exit 16; }; done
python3 "$W/tools/hbm_die_v15/v16_fetch.py" --views "$V" --remote-root "$R" --commit "$SRC_COMMIT" --contract "$V/hnx_contract.json" "$@" > "$A/fetch_s6.log" 2>&1 || { tail -20 "$A/fetch_s6.log"; exit 16; }
cat "$A/fetch_s6.log"
for c in "$@"; do [ -f "$V/synth/$c/meta.json" ] || { echo "S6S_SYNTH_MISSING $c (no stubs)"; exit 16; }; done
ssh ot-epyc4 "mkdir -p $B/hnx_vplan/synth"
rsync -a "$V/synth/" ot-epyc4:$B/hnx_vplan/synth/
echo "S6S_DONE $(date -Is)"
[ -n "${NOCHAIN:-}" ] && exit 0
cd "$W/physical/hbm_next/die"
FROM=S6 bash hnx_p4_chain.sh
