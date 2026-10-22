#!/bin/bash
set -eu
U=/home/ubuntu/scratch/qk-die
L=/home/ubuntu/scratch/qw2-nextgen/stage_gold1d.log
until grep -q '^HASH_MATCH$' "$L"; do sleep 10; done
R=/srv/opentallas-scratch/claude/mu-die-qw
K=$R/qcodex-kit
for recipe in 'dv2f21g5r6af 1 dv2f21g5r4a 0 129.6' 'dv2f21g5r6b 0 - 0 172.8' 'dv2f21g5r6bf 1 dv2f21g5r6b 0 172.8'; do
  read -r tag fault base cls sg <<< "$recipe"
  systemd-run --user --unit=codex-qdie-$tag -p StandardOutput=file:$U/$tag.otrun.log -p StandardError=file:$U/$tag.otrun.err /home/ubuntu/bin/ot-run --no-spill --mem 128 --disk 120 --priority die --dir "$K" -- env CSRC=/srv/opentallas-scratch/claude/codex-qw-classgeom0030g bash "$K/drive_ng.sh" "$tag" 0125 "$fault" "$base" "$cls" "$sg"
done
echo LAUNCHED
