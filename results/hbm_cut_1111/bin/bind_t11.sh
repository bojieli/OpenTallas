#!/bin/bash
# DIE-HBM-100 11-11: strict bind of the post-cut HBM plan t11 (t10 + hubdrop + cells_q_spt1 + die_layout_hbm). Asbuilt = the cut one (land_r8 -> re-derived table). Pass 1; if R8_STALE only, pass 2 follows.
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
W=/srv/opentallas-scratch2/claude/hbm-cut-1111
SRC=/srv/opentallas-scratch2/claude/kw43/src_hbm_tc1111p_por36
PLAN=$W/compose/t11/die_plan.json; AB=$W/bind/asbuilt_cut1111_t10.json; BIND=$W/bind/bind_t11
echo "plan sha $(sha256sum $PLAN | cut -d" " -f1)"
cd $SRC || exit 9
rm -rf "$BIND"; mkdir -p "$BIND"; touch "$BIND/DO_NOT_COUNT"
ln -s /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json "$BIND/asbuilt.json"
python3 tools/die_plan/bind.py bind "$PLAN" --out "$BIND" --asbuilt "$AB" --mem 32 --strict > "$W/bind/bind_t11.log" 2>&1 || { echo "BIND_RC $?"; grep -c R8_STALE "$W/bind/bind_t11.log"; grep -v R8_STALE "$W/bind/bind_t11.log" | tail -8 | cut -c1-300; echo BIND_NOT_OK; exit 10; }
python3 -I -c "import json,sys;r=json.load(open(\"$BIND/bind_report.json\"));print(\"BIND\",json.dumps({k:r.get(k) for k in (\"partitions\",\"crossings\",\"errors\",\"n_errors\")}));sys.exit(0 if r.get(\"n_errors\",0)==0 else 3)" || { echo BIND_NOT_OK; exit 10; }
touch "$BIND/.bind_ok"
(cd "$BIND" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS); sha256sum "$BIND/SHA256SUMS" "$BIND/bind_report.json"
echo BIND_OK
