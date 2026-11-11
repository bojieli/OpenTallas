#!/bin/bash
# BIND-SUBTYPE 11-11 (DO_NOT_COUNT): fresh strict bind of plan_p11t_taps_cyc 29333b2b with asbuilt.subtype_bind (sfu).
# Recipe = die-hbm-97-taps/bind/bind_taps.sh (src kw41/src_hbmf4_m3, tools/die_plan copied + ftres_d54b96cc27.patch),
# plus claude/bind-subtype-1111 tools (subtype_tool.patch, hbm_subtype_asbuilt.py) and the staged SFU glue.
# OV = hard-link tree of SRC; tools/die_plan and every written file are fresh inodes; nothing written into SRC.
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
# L / SRC overridable for a host whose kw41 src is a symlink (epyc2: real tree on scratch3; OV needs the same device).
L=${BST_L:-/srv/opentallas-scratch2/claude/bind-subtype-1111}
SRC=${BST_SRC:-/srv/opentallas-scratch2/claude/kw41/src_hbmf4_m3}
PD=/srv/opentallas-scratch2/claude/die-hbm-97/plan_p11t_taps_cyc
PLAN=$PD/die_plan.json
PLAN_SHA=29333b2b19c992511d31720f0b80ae1c7fe4021036a59b0fd417f950b42162d1
PATCH=$L/overlay/ftres_d54b96cc27.patch
PATCH_SHA=1eeadf9c0cc5bb85ff1e3a6d9665e268ed3d177d34fd8c73c017620998de62c0
BASE_AB=/srv/opentallas-scratch2/claude/kw43-canon/hbm/asbuilt_p37su5_sm_lat_vK5d_c12.json
OV=$L/src_ov
AB=$L/asbuilt_vK5d_c12_subtype_sfu.json
BIND=$L/bind_p11t_taps_cyc_vK5d_c12_subtype
echo "KW_STAGE check $(date '+%F %T %Z')"
[ "$(sha256sum "$PLAN" | cut -d' ' -f1)" = "$PLAN_SHA" ] || { echo PLAN_SHA_FAIL; exit 7; }
[ "$(sha256sum "$PATCH" | cut -d' ' -f1)" = "$PATCH_SHA" ] || { echo PATCH_SHA_FAIL; exit 7; }
[ "$(realpath "$SRC")" = "$SRC" ] || { echo SRC_SYMLINK_FAIL; exit 7; }
[ "$(stat -c %d "$SRC")" = "$(stat -c %d "$L")" ] || { echo OV_DEV_FAIL; exit 8; }
[ -d "$OV" ] && { find "$OV" -type d ! -perm -u+w -exec chmod u+w {} + ; rm -rf "$OV"; }
case "$(realpath -m "$OV")" in "$L"/*) ;; *) echo OV_PATH_FAIL; exit 7;; esac
cp -al "$SRC" "$OV" || { echo OV_CPAL_FAIL; exit 8; }
find "$OV" -type d ! -perm -u+w -exec chmod u+w {} +
rm -rf "$OV/tools/die_plan"
cp -r "$SRC/tools/die_plan" "$OV/tools/die_plan"; chmod -R u+w "$OV/tools/die_plan"
[ "$(find "$OV/tools/die_plan" -type f -links +1 | wc -l)" = 0 ] || { echo OV_DIEPLAN_SHARED_FAIL; exit 8; }
(cd "$OV" && git apply --exclude='tools/die_plan/test_*' "$PATCH") || { echo OV_PATCH_FAIL; exit 8; }
grep -q insertion_basis "$OV/tools/die_plan/schema.py" && grep -q core_share "$OV/tools/die_plan/schema.py" || { echo OV_CHECK_FAIL; exit 8; }
cp "$L/overlay/bind_subtype.py" "$OV/tools/die_plan/bind_subtype.py" && python3 -I "$L/overlay/hook_subtype.py" "$OV/tools/die_plan/bind.py" || { echo OV_SUBTYPE_HOOK_FAIL; exit 8; }
cp "$L/overlay/tools/die_plan/hbm_subtype_asbuilt.py" "$OV/tools/die_plan/"
mkdir -p "$OV/physical/die_plan/hbm/bind/subtype"
cp "$L/overlay/physical/die_plan/hbm/bind/subtype/ot_hgi_sfu_split3_lane_core__idpin__bsub.sv" "$OV/physical/die_plan/hbm/bind/subtype/"
python3 -I "$OV/tools/die_plan/hbm_subtype_asbuilt.py" "$BASE_AB" "$AB" --repo "$OV" || { echo AB_GEN_FAIL; exit 8; }
echo "KW_STAGE bind $(date '+%F %T %Z')"
rm -rf "$BIND"; mkdir -p "$BIND"; touch "$BIND/DO_NOT_COUNT"
# taps recipe line 43 (bind_taps.sh): the bind out dir carries the as-built die asbuilt.json; real-file copy here (no symlink)
cp /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json "$BIND/asbuilt.json" || { echo ASBUILT_COPY_FAIL; exit 9; }
[ "$(md5sum < "$BIND/asbuilt.json" | cut -c1-32)" = 81959d086954ba3c0b2156221acdd02a ] || { echo ASBUILT_MD5_FAIL; exit 9; }
cd "$OV" || exit 9
python3 tools/die_plan/bind.py bind "$PLAN" --out "$BIND" --asbuilt "$AB" --mem 32 --strict > "$L/bind.log" 2>&1 || { echo "BIND_RC $?"; tail -20 "$L/bind.log"; echo BIND_NOT_OK; exit 10; }
python3 -I -c "import json,sys;r=json.load(open('$BIND/bind_report.json'));print('BIND',json.dumps({k:r.get(k) for k in ('partitions','types','crossings','errors','unbound','n_errors')}));print('SUBTYPE',len(r.get('subtype_bind',[])));sys.exit(0 if r.get('n_errors',r.get('errors'))==0 else 3)" || { echo BIND_NOT_OK; exit 10; }
touch "$BIND/.bind_ok"
cp "$AB" "$BIND/asbuilt_subtype.json"
(cd "$BIND" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS); sha256sum "$BIND/SHA256SUMS" "$BIND/bind_report.json"
echo BIND_OK
