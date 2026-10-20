#!/bin/bash
docker run --rm -u $(id -u):$(id -g) -v /srv/opentallas-scratch/claude/qw-ctlm7-1020:/work -w /work/src openroad/orfs:latest bash -lc 'bash depth7.sh'
