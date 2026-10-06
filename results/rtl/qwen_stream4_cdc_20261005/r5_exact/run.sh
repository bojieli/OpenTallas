#!/bin/bash
# run.sh BIN NAME [ENV=..]  : run bench, keep log, record exit
B=$1; N=$2; shift 2
cd $(dirname $0)
env "$@" $B > logs/$N.log 2>&1; echo $? > logs/$N.exit
