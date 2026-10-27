#!/bin/bash
# ngrun.sh GLOB  : one ot-ngspice:r3 container per deck dir (memory cap 4g, 2 cpus), detached
cd /srv/opentallas-scratch2/claude/clock-kv-r7-1026/ng
for d in $1; do
  n=kvr7-$(echo $d | tr '/' '-')
  docker run -d --rm --name $n --memory 4g --cpus 2 -v $PWD:/w -w /w/$d ot-ngspice:r3 sh -c "ngspice -b deck.sp 2>&1 | grep -v 'Reference value' > sim.log; chown -R $(id -u):$(id -g) /w/$d" >/dev/null
done
