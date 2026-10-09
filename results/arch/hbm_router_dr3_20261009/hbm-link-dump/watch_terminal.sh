#!/bin/bash
set -u
D=/srv/opentallas-scratch/codex/hbm-router-dr3-02b165495
mkdir -p "$D/terminal_receipt"
while test -r /proc/3720051/cmdline && tr "\000" " " < /proc/3720051/cmdline | grep -q "openroad -threads 16 -no_init -exit /rb/run_rb.tcl"; do
 date -u +%FT%TZ >> "$D/phase_watch.log"
 ps -p3720051 -o pid,etimes,rss,pcpu,args >> "$D/phase_watch.log"
 tail -n 2 "$D/rb.log" >> "$D/phase_watch.log"
 sleep 60
done
# Read-only terminal collection; no restart, derivation, state flip or requeue.
for f in rb.log exit.rc guard.rc links_tt.tsv links_ff.tsv config.sha256; do
 test ! -f "$D/$f" || cp "$D/$f" "$D/terminal_receipt/$f"
done
date -u +%FT%TZ > "$D/terminal_receipt/observed_at.txt"
sha256sum "$D"/terminal_receipt/* > "$D/terminal_hashes.txt"
