#!/usr/bin/env bash
# el1011-hbm-hcvm/vm: superseded by run_vm_tunit_full_lock.sh (lockstep vs the current ot_hgi_vm_unit); this runs its reduced
# configuration (NC 8, no lane groups, no aperture).  usage: run_vm_tunit_lock.sh <outdir> [MUTS] [SEED]
exec bash "$(dirname "$0")/run_vm_tunit_full_lock.sh" "$1" "${2:-0}" "${3:-11}" small
