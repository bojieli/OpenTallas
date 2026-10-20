#!/bin/bash
# usage: run_dump.sh CASE   (run in /srv/opentallas-scratch/claude/s81-mu5 on ep7)
set -u; C=$1; A=$(cd $(dirname $0) && pwd); O=$A/$C; mkdir -p $O
docker run --rm --name die10ana-$C-$$ --cpus=2 --memory=90g -v /srv/opentallas-scratch/claude/s81-mu5/case_$C/out:/in:ro -v $A:/a -w /a openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /a/dump_guides.py /in/grt.odb /a/$C > /a/$C/dump.log 2>&1; rc=\$?; chmod -R a+rwX /a/$C; exit \$rc"
