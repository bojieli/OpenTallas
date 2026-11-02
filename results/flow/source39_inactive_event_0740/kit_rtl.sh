#!/bin/bash
export S81_BIND_OUT=/srv/opentallas-scratch2/claude/codex-flow-s81-source-2055/bind_final_clockset_t49
export S81_ASBUILT=/srv/opentallas-scratch2/claude/codex-flow-s81-source-2055/asbuilt.deadrefreshed.json
exec bash "$PWD/physical/die_plan/s81/kit_wave/kit_rtl.sh"
