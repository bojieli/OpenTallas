#!/bin/bash
# FLOW-11 10-30 canary retention prune (COORD 16:34 INFRA-PRUNE-SCRATCH-5 / epyc2 ask 17:2x).
# usage: prune_canary.sh <runs dir> <keep_named.txt> <manifest.tsv> [--delete]
# Deletes ONLY files >1 MB odb/def/spef/v/gds/guide/aig/rtlil + objects/* of runs idle >24 h that are not named
# in keep_named.txt (flow-tag messages + baseline refs).  logs/json/rpt stay.  Manifest is written first.
set -e
R=$1; K=$2; M=$3; now=$(date +%s)
cd "$R"
: > "$M.tmp"
for d in */; do d=${d%/}; [ "$d" = baselines ] && continue
  grep -qxF "$d" "$K" && continue
  m=$(find "$d" -printf "%T@\n" 2>/dev/null | sort -n | tail -1); m=${m%.*}
  [ -n "$m" ] && [ "$m" -lt $((now-86400)) ] || continue
  find "$d" -type f -size +1M \( -name "*.odb" -o -name "*.def" -o -name "*.spef" -o -name "*.v" -o -name "*.gds" -o -name "*.guide" -o -name "*.aig" -o -name "*.rtlil" -o -path "*/objects/*" \) -printf "$d\t%p\t%s\t%TY-%Tm-%Td %TH:%TM\n" >> "$M.tmp"
done
mv "$M.tmp" "$M"
echo "eligible files $(wc -l < "$M") bytes $(awk -F'\t' '{s+=$3} END{print s+0}' "$M")"
if [ "$4" = --delete ]; then cut -f2 "$M" | tr '\n' '\0' | xargs -0 -r rm -f; echo deleted; fi
