#!/bin/bash
# Corrected receive-anchor image; preserve original complete bindWc build.
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-kvtok-2249
S=/srv/opentallas-scratch2/claude/tok-kv-7-1029/bWc
B=$D/bWc_o2
I=$D/vimg_Wc_ofs-2_pinned
test -x $S/obj/Vtb_kvslice
test -f $I/frames.hex
test -f $D/dcal_Wc_ofs-2_pinned/kv_dcal_r0_c0.viamap.hex
[ -d "$B" ] || cp -a --reflink=auto "$S" "$B"
[ -d "$D/vehWc_snapshot" ] || cp -a --reflink=auto /srv/opentallas-scratch2/claude/tok-kv-7-1029/vehWc "$D/vehWc_snapshot"
export D S B I
python3 - <<'PY'
from pathlib import Path
import os
s,b,i=map(Path,(os.environ['S'],os.environ['B'],os.environ['I']))
a=Path('obj/Vtb_kvslice__hierMkArgs.f')
t=(s/a).read_text().replace(str(s)+'/',str(b)+'/').replace('/srv/opentallas-scratch2/claude/tok-kv-7-1029/vimg_Wc',str(i))
# Pin peer models/includes to this exported source cohort; do not depend on a
# paused worktree surviving after the inherited build completes.
d=Path(os.environ['D'])
t=t.replace('/srv/opentallas-scratch2/claude/wt/tok-kv-7/',str(d/'compiler_root2')+'/')
t=t.replace('/srv/opentallas-scratch2/claude/tok-kv-7-1029/vehWc/',str(d/'vehWc_snapshot')+'/')
assert t.count('+incdir+'+str(i)+'"')==1
assert '/tok-kv-7-1029/vimg_Wc"' not in t
(b/a).write_text(t)
PY
cd "$B"
[ ! -f obj/Vtb_kvslice ] || mv obj/Vtb_kvslice obj/Vtb_kvslice.offset0
/usr/bin/time -v make -f obj/Vtb_kvslice_hier.mk hier_launch_verilator VM_HIER_LAUNCH_VERILATOR_ARGSFILE=obj/Vtb_kvslice__hierMkArgs.f >$D/top_verilate_o2.log 2>&1
/usr/bin/time -v make -C obj -f Vtb_kvslice.mk -j 24 >$D/top_make_o2.log 2>&1
test -x obj/Vtb_kvslice
printf 'BUILD_DONE rc=0 %s\n' "$(date)" >$D/build_o2.status
