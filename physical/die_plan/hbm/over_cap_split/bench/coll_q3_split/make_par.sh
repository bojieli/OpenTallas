#!/bin/bash
# make_par.sh TAG J : compile verilator objects TAG with J parallel single-target makes (the fleet make runs capped at -j4)
cd /srv/opentallas-scratch2/claude/path-hbm/q3split/obj_$1
rm -f Vtb__pch.h.fast.gch Vtb__pch.h.slow.gch; make -s -f Vtb.mk VM_USER_CFLAGS="-O0 -w" OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0 Vtb__pch.h.fast.gch Vtb__pch.h.slow.gch > ../make_pch_$1.log 2>&1
ls Vtb_vm_classes_*.cpp | sed 's/\.cpp$/.o/' | xargs -P $2 -I{} make -s -f Vtb.mk VM_USER_CFLAGS="-O0 -w" OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0 {} > ../make_par_$1.log 2>&1
make -f Vtb.mk VM_USER_CFLAGS="-O0 -w" OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0 >> ../make_par_$1.log 2>&1; echo "make_par $1 rc=$?"; ls -la sim
