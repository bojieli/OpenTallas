#!/bin/bash
# FTLOCK-S81 (DIE-S81-85 11-10): kit RTL of the named items from the ft_hop_lockup event plan (item_inputs plan) and its
# strict bind /srv/opentallas-scratch2/claude/die-s81-85/ftlock/bind_ftlk (u_fl_<o>_k hop latches in the bound station chains), asbuilt /srv/opentallas-scratch2/claude/type-safe-4/s81p3/asbuilt_f.json.
set -euo pipefail
export S81_ASBUILT=/srv/opentallas-scratch2/claude/type-safe-4/s81p3/asbuilt_f.json
export S81_BIND_OUT=/srv/opentallas-scratch2/claude/die-s81-85/ftlock/bind_ftlk
exec bash physical/die_plan/s81/kit_wave/kit_rtl.sh
