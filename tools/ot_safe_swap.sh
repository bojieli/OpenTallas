#!/bin/bash
# ot_safe_swap.sh: replace a spill copy (SRC tree) by a symlink to a verified copy (DST tree).
# FLEET-2 11-12, guard v2 (after the epyc4 kw45 self-loop that deleted 7 trees, and a partial rm on root-owned files).
# REFUSES unless:
#   * SRC and DST are real dirs (no symlink), different objects (readlink -f, stat dev:inode of the trees AND of their
#     parent dirs), neither inside the other, on different filesystems (set OT_SWAP_ALLOW_SAME_FS=1 in tests only);
#   * the WHOLE SRC tree is deletable by us (no file/dir owned by another user, no non-writable directory);
#   * no live /proc cwd/fd refs under SRC;
#   * SRC is not named in any refusal file (protected.tsv, queue.json, kitwave.json of the autoclean snapshot,
#     the kit-wave keep list); at least one refusal file must be readable (fail closed). A path equal to, inside or
#     containing SRC counts. Files: --refuse-file F (repeatable) else ~/.local/state/ot-autoclean-*/snapshot/{protected.tsv,queue.json,kitwave.json}
#   * rsync -aHn --delete SRC/ DST/ is empty.
# usage: ot_safe_swap.sh [--apply] [--refuse-file F]... SRC_TREE DST_TREE      (default: dry run)
# Apply order: rename SRC -> SRC.swap-trash (complete tree kept), link SRC -> DST, verify the link resolves to DST,
# and only THEN rm the trash. A failed verify restores the complete tree; a failed rm leaves the link in place
# (DST is complete and authoritative) and reports TRASH-PARTIAL; it never restores a half-deleted tree.
set -u
apply=0; rfiles=()
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) apply=1; shift;;
    --refuse-file) rfiles+=("$2"); shift 2;;
    --) shift; break;;
    *) break;;
  esac
done
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
if [ "${OT_SWAP_ALLOW_SAME_FS:-0}" != 1 ]; then
  [ "$(stat -c %d -- "$src")" != "$(stat -c %d -- "$dst")" ] || refuse "src and dst on the same filesystem; nothing to free"
fi
# whole-tree deletability: nothing owned by another user, no non-writable directory
me=$(id -un)
bad=$(find "$src" \( ! -user "$me" -o \( -type d ! -writable \) \) -print -quit 2>/dev/null)
[ -z "$bad" ] || refuse "tree not fully deletable by $me (first: $bad)"
# refusal inputs (fail closed)
if [ ${#rfiles[@]} -eq 0 ]; then
  for f in "$HOME"/.local/state/ot-autoclean-*/snapshot/protected.tsv "$HOME"/.local/state/ot-autoclean-*/snapshot/queue.json "$HOME"/.local/state/ot-autoclean-*/snapshot/kitwave.json; do
    [ -r "$f" ] && rfiles+=("$f")
  done
fi
ok=0; for f in "${rfiles[@]}"; do [ -r "$f" ] && ok=$((ok+1)); done
[ $ok -gt 0 ] || refuse "no readable refusal file (protected.tsv/queue.json/kitwave.json); fail closed"
for f in "${rfiles[@]}"; do
  [ -r "$f" ] || refuse "refusal file unreadable: $f"
  # equal to or inside SRC
  if grep -qE -- "$(printf '%s' "$rs" | sed 's/[][\.*^$/+?(){}|]/\\&/g')([^A-Za-z0-9_.-]|$)" "$f"; then refuse "named in $f"; fi
  # a listed path that contains SRC (a parent of it is protected)
  p=$rs; while [ "$p" != "/" ] && [ -n "$p" ]; do p=$(dirname -- "$p"); [ "$p" = "/" ] && break
    if grep -qE -- "(^|[^A-Za-z0-9_./-])$(printf '%s' "$p" | sed 's/[][\.*^$/+?(){}|]/\\&/g')([\"[:space:],]|$)" "$f"; then refuse "parent $p protected in $f"; fi
  done
done
live=$(sudo -n find /proc -mindepth 2 -maxdepth 3 \( -path '/proc/[0-9]*/cwd' -o -path '/proc/[0-9]*/fd/*' \) -printf '%l\n' 2>/dev/null | grep -cF -- "$rs")
[ "$live" = 0 ] || refuse "LIVE $live process refs"
d=$(nice -n 15 rsync -aHn --itemize-changes --delete -- "$src/" "$dst/" 2>&1 | grep -v '^\.d' | head -3)
[ -z "$d" ] || refuse "copies differ: $(echo $d | cut -c1-120)"
echo "OK $src -> $dst verified (distinct objects, whole tree deletable, not protected, no live refs, rsync dry run empty)"
[ $apply = 1 ] || exit 0
trash="$src.swap-trash"
[ ! -e "$trash" ] || refuse "$trash already exists"
mv -- "$src" "$trash" || refuse "rename failed"
if ln -s -- "$rd" "$src" && [ "$(stat -c %d:%i -- "$src/")" = "$(stat -c %d:%i -- "$dst/")" ] && [ -n "$(ls -A -- "$src/" | head -1)" ]; then
  if nice -n 15 rm -rf --one-file-system -- "$trash"; then echo "swapped $src"; else echo "TRASH-PARTIAL $trash (link verified, $dst is complete; clean the trash by hand)"; exit 5; fi
else
  echo "POSTCHECK FAIL: restoring complete tree"; rm -f -- "$src"; mv -- "$trash" "$src"; exit 4
fi
