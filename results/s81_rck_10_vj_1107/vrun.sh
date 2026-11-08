#!/bin/bash
# run a command inside the verilator 5.032 container, capped
exec timeout ${VTO:-1800} docker run --rm -m ${VMEM:-8g} --cpus ${VCPU:-4} -u 1000:1000 -e HOME=/srv/opentallas-scratch2/claude/s81-rck-10/tmp -e CCACHE_DISABLE=1 -e TMPDIR=/srv/opentallas-scratch2/claude/s81-rck-10/tmp -v /srv/opentallas-scratch2/claude/s81-rck-10:/srv/opentallas-scratch2/claude/s81-rck-10 -w /srv/opentallas-scratch2/claude/s81-rck-10 --entrypoint bash verilator/verilator:v5.032 -c "$*"
