#!/bin/bash
# PRUNE-1104N COORD 11:19 (2): finish one PARTIAL row: re-check, then delete its contents from a container with only that path mounted, no network. usage on host: ltpartial.sh list.txt
R=/srv/opentallas-scratch2/claude/
while read -r p; do
  case "$p" in $R*/items/*) ;; *) echo "REFUSE outside $p"; continue;; esac
  [ -d "$p" ] && [ ! -L "$p" ] || { echo "gone $p"; continue; }
  echo "$p" > /tmp/p1104n_one.txt
  c=$(P1104N_PARTIAL=1 python3 -I /tmp/p1104n_ltdel.py /tmp/p1104n_one.txt list | tail -1)
  case "$c" in *"ok 1 "*) ;; *) echo "REFUSE $p $c"; continue;; esac
  b=$(du -sm "$p" | cut -f1)
  docker run --rm --network none -v "$p":/x python:3.12-slim sh -c 'find /x -mindepth 1 -delete' 
  rc=$?; rmdir "$p" 2>/dev/null
  [ -e "$p" ] && echo "LEFT rc=$rc $b MB $p" || echo "DONE $b MB $p"
done < "$1"
