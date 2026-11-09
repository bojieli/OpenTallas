# args: src_link  name
set -e
SRC=$(realpath "$1"); N="$2"; L=/srv/opentallas-scratch2/claude/kw37/$N
D=$(dirname "$(dirname "$SRC")")/kw37_src/$N
case "$D" in */kw37_src/*) ;; *) exit 9;; esac
if [ -e "$L" ] && [ ! -L "$L" ]; then exit 7; fi
[ -L "$L" ] && exit 0
mkdir -p "$(dirname "$D")" "$(dirname "$L")"
cp -al "$SRC" "$D" 2>/tmp/kw37_lg.err
F=$D/tools/die_plan/legacy_gate.py
chmod u+w "$D/tools/die_plan"
T=$(mktemp /tmp/kw37_gate.XXXXXX)
cp "$F" "$T"; chmod u+w "$T"
python3 -I - "$T" <<PY
import sys,importlib.util
from pathlib import Path
exec(open("/tmp/kw37_patch3.py").read().split('if __name__')[0])
patch_gate(Path(sys.argv[1]))
PY
python3 -I -m py_compile "$T" ; rm -f "$F"; install -m 0444 "$T" "$F"; rm -f "$T" "${T%/*}/__pycache__"/$(basename "$T").* 2>/dev/null || true
chmod a-w "$D/tools/die_plan"
ln -s "$D" "$L"
echo "built $(hostname) $N $(sha256sum "$F" | cut -c1-10)"
