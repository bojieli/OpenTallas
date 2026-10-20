#!/bin/bash
# S81-ROMOPT-C: pack the committed evidence of a fleet output dir (no ROM images; their sha256 are in each meta.json)
# usage collect.sh SRC_DIR TAR
set -u
cd $1; T=$2; rm -f $T.list
find . \( -name summary.json -o -name frame.json -o -name seq.json -o -name 'check_P*.json' -o -name 'check_P*.log' \
  -o -name 'run_P*.log' -o -name 'run_P*.log.gz' -o -name pvmeasure.json -o -name 'run_pv.log.gz' -o -name 'pvfit*.json' \
  -o -name 'sequence_gen.log' \) -not -path "*_phases/*" > $T.list
find . -path '*/mut_*/check.json' -o -path '*/mut_*/run.log' >> $T.list
find . -regextype posix-extended -regex '\./[^/]+/[^/]+/(p[0-9]+|mut_[a-z]+_p[0-9]+)/meta.json' >> $T.list
tar -czf $T -T $T.list && echo "COLLECT $(wc -l < $T.list) files $(du -h $T | cut -f1)"
