set -eu
cd /srv/opentallas-scratch2/claude/wt/die-kv-16
AS=/srv/opentallas-scratch2/claude/die-kv-16-1028/img5/asbuilt_rtl6
set -a; . $AS/kv_flags.env; set +a
export OT_KV_RETIRE_SUCCESSOR=$AS/health_successor.json OT_KV_RETIRE_LOGICAL=1
OT_KV_LINK_IMAGE=/srv/opentallas-scratch2/claude/die-kv-17-1028/boot5/img_bnd/d2d_cal_image.svh python3 physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py compile --ages /srv/opentallas-scratch2/claude/die-kv-17-1028/boot5/prep/die_ages_bound_padded.json --rs /srv/opentallas-scratch2/claude/die-kv-17-1028/boot5/prep/relay_stages_bound.json --out /srv/opentallas-scratch2/claude/die-kv-17-1028/boot5/cmp_native --mu --native-contract /srv/opentallas-scratch2/claude/die-kv-16-1028/img5/native_contract.json --capability 1
