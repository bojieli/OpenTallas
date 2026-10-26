#!/bin/bash
# TOK-DS 10-25 (dskr): rebuild of the deskew L0 NX cut vehicles from COMMITTED sources. The ec43 vehicles of 10-25 05:00-06:40
# (results/token_pass/tokds_dsk_replay_1025) lived on epyc3, retired 10-25 20:15; their ec43bbd4 XRT was never committed and
# exists in no git object or fleet host, so they cannot be re-verified (closure-order rule 3).
# Inputs, sha-pinned in results/token_pass/tokds_dskr_1025/inputs.sha256 (paths relative to <IN>):
#   fc30cuts/{cut_*,K_cut_*}               recovered fc30 cuts + kits (dv_slice_cut / dv_rtl_kit output, die lineage cap30)
#   fc31/{die.v,frame_chain_reset_v2.json} S81-P9-FC fc31 die 35ba1ef7 (= the die_sha256 of the 10-25 entry receipt)
#   cap30/{plan.json,land.json}            cap30 GEN plan / land (die tree)
# Per cut (as tools/s81_dv/tokfunc/fc31/prep_fc31.sh + reclock_cut.py): fc31 station patch -> reclock -> the kit's only XRT file
# := rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv AT THIS COMMIT (NORM-DESKEW on by default, PDSK 01234; FACE_LAND 0 default;
# module ports identical to the kit's cfc3 XRT). Then mk_tree on fc31. Records vehicle.json (every output sha256).
# Usage (from anywhere): prep_dskr.sh <IN dir> <OUT dir>; all tool paths are repo-relative to this script's checkout.
set -eu
IN=$(realpath $1); O=$(realpath -m $2)
R=$(cd "$(dirname "$0")" && git rev-parse --show-toplevel); cd $R
[ ! -e $O/cuts ] || { echo "exists $O/cuts (fresh dirs only)"; exit 3; }
(cd $IN && sha256sum -c --quiet $R/results/token_pass/tokds_dskr_1025/inputs.sha256) || { echo "INPUT SHA MISMATCH"; exit 2; }
XRT=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv
S=$O/stage; mkdir -p $S $O/cuts
for c in cut_0S cut_0N cut_7 cut_3S_ctl; do
  cp -a $IN/fc30cuts/$c $S/$c; cp -a $IN/fc30cuts/K_$c $S/K_$c
  python3 results/rtl/s81_chaincal_fc31_1023/cut_3S_ctl/patch_cut.py $IN/fc30cuts/$c/slice_top.sv $IN/fc31/die.v \
    $IN/fc31/frame_chain_reset_v2.json $S/$c/slice_top.sv > $O/cuts/$c.patch.json
  cp $S/$c/slice_top.sv $S/K_$c/src/top/slice_top.sv
  python3 tools/s81_dv/tokfunc/fc31/reclock_cut.py --cut $S/$c --kit $S/K_$c --out-cut $O/cuts/$c --out-kit $O/cuts/K_$c \
    > $O/cuts/$c.reclock.log
  K=$O/cuts/K_$c; X=$(grep '/ot_s81sl_xrt.sv$' $K/kit.f)
  [ "$(echo "$X" | wc -l)" = 1 ] || { echo "$c: kit must list exactly one XRT"; exit 4; }
  [ "$(find $K/src -name ot_s81sl_xrt.sv | wc -l)" = 1 ] || { echo "$c: more than one XRT file in kit"; exit 4; }
  cp $XRT $K/$X
  echo "$c: patch $(python3 -c "import json; d=json.load(open('$O/cuts/$c.patch.json')); print(len(d), 'frames', sum(x['stations_added'] for x in d), 'stations')") | $(tail -1 $O/cuts/$c.reclock.log | cut -c1-120) | xrt $(sha256sum $K/$X | cut -c1-8)"
done
rm -rf $S
python3 tools/s81_dv/tokfunc/mk_tree.py --die-v $IN/fc31/die.v --plan $IN/cap30/plan.json --land $IN/cap30/land.json \
  --out $O/tree_fc31 --tag fc31 > $O/mk_tree.log 2>&1 || { echo "MK_TREE FAIL"; tail -3 $O/mk_tree.log; exit 5; }
python3 - $R $O <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
R, O = map(Path, sys.argv[1:3])
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
files = {str(p.relative_to(O)): h(p) for p in sorted(O.rglob('*')) if p.is_file()}
rec = dict(schema='opentallas.tok_ds.dskr_vehicle.v1', commit=subprocess.check_output(['git', '-C', str(R), 'rev-parse', 'HEAD'], text=True).strip(),
           dirty=bool(subprocess.check_output(['git', '-C', str(R), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()),
           xrt_sha256=h(R / 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv'), n_files=len(files), files=files)
(O / 'vehicle.json').write_text(json.dumps(rec, indent=1) + '\n')
print('VEHICLE', rec['commit'][:10], 'dirty' if rec['dirty'] else 'clean', len(files), 'files')
PY
