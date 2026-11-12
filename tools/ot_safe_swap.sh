#!/bin/bash
# ot_safe_swap.sh: replace a spill copy (SRC tree) by a symlink to a verified copy (DST tree).
# Root-relief swap guard (FLEET-2, 11-12 after the epyc4 kw45 self-loop that deleted 7 trees):
# REFUSES unless SRC and DST are different filesystem objects, DST is a real dir (not a symlink),
# and no component of either path resolves into the other.
# usage: ot_safe_swap.sh [--apply] SRC_TREE DST_TREE      (default: dry run, prints decisions only)
set -u
apply=0; [ "${1:-}" = "--apply" ] && { apply=1; shift; }
src=${1:?src}; dst=${2:?dst}
refuse() { echo "REFUSE $src: $*"; exit 3; }
[ -d "$src" ] && [ ! -L "$src" ] || refuse "src is not a real directory (symlink/missing)"
[ -d "$dst" ] && [ ! -L "$dst" ] || refuse "dst is not a real directory (symlink/missing)"
rs=$(readlink -f -- "$src"); rd=$(readlink -f -- "$dst")
[ "$rs" != "$rd" ] || refuse "readlink -f equal ($rs)"
[ "$(stat -c %d:%i -- "$src")" != "$(stat -c %d:%i -- "$dst")" ] || refuse "same device:inode"
[ "$(stat -c %d:%i -- "$(dirname -- "$src")")" != "$(stat -c %d:%i -- "$(dirname -- "$dst")")" ] || refuse "parent directories are the same object (a parent is a symlink to the other)"
case "$rd/" in "$rs"/*) refuse "dst inside src";; esac
case "$rs/" in "$rd"/*) refuse "src inside dst";; esac
# must be on a different filesystem to free anything
[ "$(stat -c %d -- "$src")" != "$(stat -c %d -- "$dst")" ] || refuse "src and dst on the same filesystem; nothing to free"
live=$(sudo -n find /proc -mindepth 2 -maxdepth 3 \( -path '/proc/[0-9]*/cwd' -o -path '/proc/[0-9]*/fd/*' \) -printf '%l\n' 2>/dev/null | grep -cF -- "$rs")
[ "$live" = 0 ] || refuse "LIVE $live process refs"
d=$(nice -n 15 rsync -aHn --itemize-changes --delete -- "$src/" "$dst/" 2>&1 | grep -v '^\.d' | head -3)
[ -z "$d" ] || refuse "copies differ: $(echo $d | cut -c1-120)"
echo "OK $src -> $dst verified (distinct objects, no live refs, rsync dry run empty)"
[ $apply = 1 ] || exit 0
mv -- "$src" "$src.old-swap" && ln -s -- "$rd" "$src" || refuse "swap failed"
# post-check: the link must resolve to the real data before anything is deleted
[ "$(stat -c %d:%i -- "$src/")" = "$(stat -c %d:%i -- "$dst/")" ] && [ -n "$(ls -A -- "$src/" | head -1)" ] \
  && nice -n 15 rm -rf --one-file-system -- "$src.old-swap" && echo "swapped $src" \
  || { echo "POSTCHECK FAIL: restoring"; rm -f -- "$src"; mv -- "$src.old-swap" "$src"; exit 4; }
