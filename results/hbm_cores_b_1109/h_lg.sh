set -e
D=$(realpath /srv/opentallas-scratch2/claude/kw37/src_1dea_lf); F=$D/tools/die_plan/legacy_gate.py
chmod u+w $D/tools/die_plan; T=$(mktemp /tmp/kw37_gate.XXXXXX); cp $F $T; chmod u+w $T
python3 -I - $T <<PY
import sys
from pathlib import Path
exec(open("/tmp/kw37_patch3.py").read().split('if __name__')[0])
patch_gate(Path(sys.argv[1]))
PY
python3 -I -m py_compile $T; rm -f $F; install -m 0444 $T $F; rm -f $T; chmod a-w $D/tools/die_plan
echo "$(hostname) $(sha256sum $F | cut -c1-10)"
