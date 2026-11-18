#!/bin/bash
# install_docker_shim.sh (FLEET-OPS-R): /usr/local/bin/docker -> rt/current/tools/fleet/ot-docker on THIS host (run after the merge + ot-tools-sync).  Needs sudo -n.
# Undo: sudo rm /usr/local/bin/docker  (the real binary stays /usr/bin/docker).
set -eu
T=/srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-docker
[ -x "$T" ] || { echo "ot-docker missing in rt/current: sync first" >&2; exit 3; }
sudo -n ln -sfn "$T" /usr/local/bin/docker
echo "$(hostname -s): $(readlink /usr/local/bin/docker); real docker: $(/usr/bin/docker --version)"
