#!/bin/bash
cd /srv/opentallas-scratch2/claude/die-hbm-89/topk/repo
rm -rf /srv/opentallas-scratch2/claude/die-hbm-89/topk/kits/ot_hbm_idx_topk_link_static_fa4a6c51ad35-_vD
python3 physical/die_plan/hbm_arch_cores/gen_core_kit_hbm_rw.py --views /srv/opentallas-scratch2/claude/kw25-wave-1106/runs/hbm/kit-wave/hbm/d44v/core_views.347ae56f82.json --view 'ot_hbm_idx_topk_link_static@fa4a6c51ad35' --out /srv/opentallas-scratch2/claude/die-hbm-89/topk/kits --clock-pin-entry on --core-macros auto --recipe-key ot_hbm_idx_topk_link_static__ev74_pd3w --util 0.30 --sigmax M6 --macro-placement /srv/opentallas-scratch2/claude/die-hbm-89/topk/vD_macro_placement.json --macro-inst-fmt 'u_core.u_sto.gm\[{k}\].mem' --tag _vD
echo GEN_RC $?
