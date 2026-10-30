#!/bin/bash
# DIE-QC-50/gen47b: usage run_grt_prov.sh CORNER [N]  (epyc2; launch through ot-run --hosts epyc2)
set -u
C=$1; V=${2:-}; Q=/srv/opentallas-scratch2/claude; S=$Q/die-qc-49/g47src; R=$Q/die-qc-50/gen47b; O=$R/grt_$C$V; mkdir -p $O
SC=$Q/wt/die-qc-50-gen47b/results/qc_die50_1030/gen47b/scripts
docker run --rm --name dqc50g47b-grt-$C$V-$$ --memory=96g --memory-swap=96g --cpus=16 -v $Q:$Q -e OUT=$O -e CORNER=$C -e SRC=$S -e DB=$R/import/provider.odb -e NDR_RC=$([ "$V" = N ] && echo 1 || echo 0) openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -exit $SC/grt_prov.tcl > $O/run.log 2>&1; rc=\$?; chown -R 1000:1000 $O; exit \$rc"
rc=$?; echo "rc=$rc $(date)" > $O/status
[ $rc = 0 ] && python3 $Q/wt/die-qc-50-gen47b/results/qc_die50_1030/gen47b/scripts/mk_edges47.py $O/edges_raw.txt $O/arr_$C.txt $O/census.json
exit $rc
