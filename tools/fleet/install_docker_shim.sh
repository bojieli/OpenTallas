#!/bin/bash
# install_docker_shim.sh (FLEET-OPS-R): /usr/local/bin/docker -> rt/current/tools/fleet/ot-docker on THIS host (run after the merge + ot-tools-sync).  Needs sudo -n.
# Undo: sudo rm /usr/local/bin/docker  (the real binary stays /usr/bin/docker).
set -eu
# COORD 11-17: the six BUILD hosts only.  The hub intel2 and localhost (rtx-pro) run the owner's non-OpenTallas docker work: never installed there.
case "$(hostname -s)" in
  tolerant-swine|ubuntu|intel2|localhost|rtx-pro) echo "install_docker_shim: REFUSED on $(hostname -s): build hosts only (intel1 epyc2 epyc7 epyc8 epyc9 epyc10 epyc11 epyc12)" >&2; exit 64;;
esac
T=/srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-docker
[ -x "$T" ] || { echo "ot-docker missing in rt/current: sync first" >&2; exit 3; }
sudo -n ln -sfn "$T" /usr/local/bin/docker
echo "$(hostname -s): $(readlink /usr/local/bin/docker); real docker: $(/usr/bin/docker --version)"
