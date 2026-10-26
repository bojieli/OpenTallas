#!/bin/bash
# usage: dietop_run.sh <dir> <tcl> <threads> <mem_gb> [env...]; RSS sampled every 30 s into <dir>/rss.tsv
set -u
D=$(readlink -f $1); TCL=$2; T=$3; M=$4; shift 4; EV=""; for e in "$@"; do EV="$EV -e $e"; done
# Variant runs commonly share the final components (chain/grt_r22k).
# Bind the container identity to the complete canonical stage path.
RUN_KEY=$(printf '%s' "$D" | sha256sum | cut -c1-12)
N=qfd_dietop_$(basename "$D")_$RUN_KEY
date -u +%FT%TZ > $D/run.start
( while sleep 30; do s=$(docker stats --no-stream --format "{{.MemUsage}} {{.CPUPerc}}" $N 2>/dev/null) || break; [ -z "$s" ] && break; echo -e "$(date -u +%T)\t$s" >> $D/rss.tsv; done ) &
docker run --rm --name $N --cpus=$T --memory=${M}g -e OT_THREADS=$T $EV -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $T -no_init -exit /work/$TCL > /work/$(basename $TCL .tcl).log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
rc=$?
echo "$rc" > "$D/run.exit"; date -u +%FT%TZ > "$D/run.end"
exit "$rc"
