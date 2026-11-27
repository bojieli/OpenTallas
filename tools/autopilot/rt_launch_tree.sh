#!/bin/bash
# rt_launch_tree.sh SRC RT L -- TOOLS-DECOUPLE-1118 (OWNER via COORD, FABLE-WORKFLOW-0400 do-now 1).
# Compose the launch tree L of a kit: the tools of the rt snapshot RT (rt/<sha12>, immutable, on every host) with the design data of
# the die tree SRC.  L/tools and L/physical/common_flow are hardlinks of RT's (rt files always win; tool files only the die tree has
# are hardlinked in after them and listed in L/.rt_launch_filled); every other entry of SRC and of SRC/physical is a symlink into SRC.
# A tool run from L finds its repo root at L (parents of its own file), so its tools are RT's and its design inputs are SRC's.
# Idempotent and cheap once made (L/.rt_launch_ok); made under a flock in L.tmp.<pid> and renamed, so a reader never sees half a tree.
# L is never changed after the rename: a new rt sha is a new L.  Exit 97 = cannot compose (missing tree / rt snapshot).
set -u
S=${1%/}; RT=${2%/}; L=${3%/}
PR=""; PIN_ARGS=""
if [ $# -ge 5 ] && [ -n "$5" ]; then
  PR=${4%/}; PIN_ARGS=$5
fi
stamp_matches() {
  local marker="$1/.rt_launch_ok"
  [ -f "$marker" ] && [ ! -L "$marker" ] || return 1
  python3 -I - "$marker" "$S" "$RT" "$PR" "$PIN_ARGS" <<'PY'
import json
from pathlib import Path
import sys

marker, src, rt, pin_rt, pin_args = sys.argv[1:]
try:
    stamp = json.loads(Path(marker).read_text())
    pins = dict(pair.split("=", 1) for pair in pin_args.replace(",", " ").split())
    actual = (stamp.get("src"), stamp.get("rt"), stamp.get("pin_rt", ""), stamp.get("pins", {}))
except (OSError, ValueError, AttributeError):
    sys.exit(1)
sys.exit(actual != (src, rt, pin_rt, pins))
PY
}
stamp_matches "$L" && exit 0
H=$(hostname -s)
[ -d "$S" ] || { echo "KW_RT_TOOLS FAIL: die tree $S missing on $H" >&2; exit 97; }
[ -d "$RT/tools" ] || { echo "KW_RT_TOOLS FAIL: rt snapshot $RT/tools missing on $H" >&2; exit 97; }
mkdir -p "${L%/*}" || exit 97
exec 8>"$L.lock"
flock 8
stamp_matches "$L" && exit 0
if [ -e "$L/.rt_launch_ok" ] || [ -L "$L/.rt_launch_ok" ]; then
  echo "KW_RT_TOOLS FAIL: incompatible launch stamp in $L on $H" >&2
  exit 97
fi
T="$L.tmp.$$"
# SEALED-INODE-SHARED (COORD 11-26): files of an incomplete L may be HARD LINKS of rt files; chmod on a link changes the rt inode, so only DIRECTORIES are made writable (removing
# a name needs write on its dir, never on the file).  find does not follow symlinks.
find "$T" "$L" -type d ! -perm -u+w -exec chmod u+w {} + 2>/dev/null; rm -rf "$T" "$L"   # an L without .rt_launch_ok was never complete, so nothing runs from it
mkdir -p "$T/physical" || exit 97
for e in "$S"/* "$S"/.[!.]*; do
  [ -e "$e" ] || [ -L "$e" ] || continue
  b=${e##*/}
  case $b in tools|physical|.rt_launch_ok|.rt_launch_filled) continue;; esac
  ln -s "$e" "$T/$b" || exit 97
done
if [ -d "$S/physical" ]; then
  for e in "$S"/physical/* "$S"/physical/.[!.]*; do
    [ -e "$e" ] || [ -L "$e" ] || continue
    b=${e##*/}
    [ "$b" = common_flow ] && continue
    ln -s "$e" "$T/physical/$b" || exit 97
  done
fi
link_tree() { cp -al "$1" "$2" 2>/dev/null || { find "$2" -type d ! -perm -u+w -exec chmod u+w {} + 2>/dev/null; rm -rf "$2"; cp -a "$1" "$2"; }; }   # dirs only: a chmod -R u+w here changed the rt inodes (SEALED-INODE-SHARED)   # cp -a keeps rt's a-w dir modes
link_tree "$RT/tools" "$T/tools" || exit 97
if [ -d "$RT/physical/common_flow" ]; then
  link_tree "$RT/physical/common_flow" "$T/physical/common_flow" || exit 97
elif [ -d "$S/physical/common_flow" ]; then
  ln -s "$S/physical/common_flow" "$T/physical/common_flow" || exit 97
fi
# rt dirs are read-only: the copies' dirs get u+w (python __pycache__, the fill below); the hardlinked files keep their mode
find "$T/tools" "$T/physical/common_flow" -type d ! -perm -u+w -exec chmod u+w {} + 2>/dev/null
fill() {
  [ -d "$S/$1" ] && [ -d "$T/$1" ] && [ ! -L "$T/$1" ] || return 0
  (cd "$S/$1" && find . -name __pycache__ -prune -o \( -type f -o -type l \) -print) | while IFS= read -r f; do
    { [ -e "$T/$1/$f" ] || [ -L "$T/$1/$f" ]; } && continue
    mkdir -p "$T/$1/$(dirname "$f")" && { ln "$S/$1/$f" "$T/$1/$f" 2>/dev/null || cp -a "$S/$1/$f" "$T/$1/$f"; } && echo "$1/${f#./}"
  done
}
{ fill tools; fill physical/common_flow; } > "$T/.rt_launch_filled" || exit 97
n=$(wc -l < "$T/.rt_launch_filled")
# BIND-PIN-1124: rt_launch_tree.sh SRC RT L [PINRT NAME=SHA256,...] -- the named tools/die_plan generators come from PINRT (the bind's rt), each
# checked against the sha256 the bind stamped; any mismatch or missing file = exit 97 (never a launch tree with other generators than the bind's)
PINS=""
if [ -n "$PIN_ARGS" ]; then
  for kv in ${PIN_ARGS//,/ }; do
    f=${kv%%=*}; want=${kv#*=}
    case $f in */*|..*|"") echo "KW_RT_TOOLS FAIL: bad pin $kv" >&2; exit 97;; esac
    got=$(sha256sum "$PR/tools/die_plan/$f" 2>/dev/null | cut -d' ' -f1)
    [ "$got" = "$want" ] || { echo "KW_RT_TOOLS FAIL: pin $f of $PR is ${got:-missing}, the bind stamped $want" >&2; exit 97; }
    rm -f "$T/tools/die_plan/$f" && cp -p "$PR/tools/die_plan/$f" "$T/tools/die_plan/$f" || exit 97
    PINS="$PINS${PINS:+, }\"$f\": \"$want\""
  done
fi
printf '{"rt": "%s", "src": "%s", "tree_only_tool_files": %d, "made": "%s", "host": "%s", "pin_rt": "%s", "pins": {%s}}\n' "$RT" "$S" "$n" "$(date -Is)" "$H" "$PR" "$PINS" > "$T/.rt_launch_ok" || exit 97
stamp_matches "$T" || { echo "KW_RT_TOOLS FAIL: could not verify launch stamp for $L on $H" >&2; exit 97; }
mv -T "$T" "$L" || exit 97
echo "KW_RT_TOOLS composed $L (rt $RT; $n tool files only the die tree has kept${PINS:+; pinned from $PR: $PINS})"
