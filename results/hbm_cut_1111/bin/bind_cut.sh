#!/bin/bash
# DIE-HBM-99 11-11: ONE strict bind for the HBM 12:00 cut on composed plan t10. Same recipe as die-hbm-97-taps bind_taps.sh
# (asbuilt kw43-canon vK5d_c12, bind.py --strict) but the tools are the cut src por36 (m5full overlay + native_istations 57a3d8fd), private copy.
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
W=/srv/opentallas-scratch2/claude/hbm-cut-1111
SRC=/srv/opentallas-scratch2/claude/kw43/src_hbm_tc1111p_por36
PLAN=$W/compose/t10/die_plan.json
AB=/srv/opentallas-scratch2/claude/kw43-canon/hbm/asbuilt_p37su5_sm_lat_vK5d_c12.json
OV=$W/bind/src_ov; BIND=$W/bind/bind_cut1111_t10
echo "plan sha $(sha256sum $PLAN | cut -d" " -f1)"
# 11-11 13:2x: run in SRC itself (the symlink overlay made dead-input proof paths resolve outside the repo: bind.py dead_inputs repository-relative check); PYTHONDONTWRITEBYTECODE keeps the tree clean
OV=$SRC
rm -rf "$BIND"; mkdir -p "$BIND"; touch "$BIND/DO_NOT_COUNT"
ln -s /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json "$BIND/asbuilt.json"
cd "$OV" || exit 9
python3 tools/die_plan/bind.py bind "$PLAN" --out "$BIND" --asbuilt "$AB" --mem 32 --strict > "$W/bind/bind.log" 2>&1 || { echo "BIND_RC $?"; tail -20 "$W/bind/bind.log"; echo BIND_NOT_OK; exit 10; }
python3 -I -c "import json,sys;r=json.load(open(\"$BIND/bind_report.json\"));print(\"BIND\",json.dumps({k:r.get(k) for k in (\"partitions\",\"types\",\"crossings\",\"errors\",\"unbound\",\"n_errors\",\"unmapped\",\"open_outputs\")}));sys.exit(0 if r.get(\"n_errors\",r.get(\"errors\"))==0 else 3)" || { echo BIND_NOT_OK; exit 10; }
touch "$BIND/.bind_ok"
(cd "$BIND" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS); sha256sum "$BIND/SHA256SUMS" "$BIND/bind_report.json"
echo BIND_OK
