#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
runner="$root/sim/rtl/dsrom_sys/s81_dv/unit/test/run_mu_hwin_early_capture.sh"
case "${1:?}" in
 core) for phase in default initial wrapper matrix stress calendar_mutants boot_faults winner_and_mechanism; do bash "$runner" "$2/$phase" "$phase"; done;;
 four_state) bash "$runner" "$2" four_state;;
 sweep) bash "$runner" "$2" sweep;;
 *) exit 64;;
esac
