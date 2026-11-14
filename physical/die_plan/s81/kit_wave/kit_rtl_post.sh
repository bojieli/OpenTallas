#!/bin/bash
# Script-mode entry of the S81 svc kit-RTL post step; the one copy of the recipe is
# tools/autopilot/kit_rtl_post.d/s81_svc_memory.sh (bind mode inlines it from the running kit_wave.py).
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec bash "$HERE/../../../../tools/autopilot/kit_rtl_post.d/s81_svc_memory.sh"
