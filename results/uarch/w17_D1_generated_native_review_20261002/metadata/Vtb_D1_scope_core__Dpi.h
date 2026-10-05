// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Prototypes for DPI import and export functions.
//
// Verilator includes this file in all generated .cpp files that use DPI functions.
// Manually include this file where DPI .c import functions are declared to ensure
// the C functions match the expectations of the DPI imports.

#ifndef VERILATED_VTB_D1_SCOPE_CORE__DPI_H_
#define VERILATED_VTB_D1_SCOPE_CORE__DPI_H_  // guard

#include "svdpi.h"

#ifdef __cplusplus
extern "C" {
#endif


    // DPI EXPORTS
    // DPI export at /tmp/opentallas-D1-parent-scope-frontend-20261002-r2/rtl/test/w17_D1_scope_corrected_probe/ot_v41_rt_die_D1_scope.sv:225:18
    extern int v41rt_vm_word(int a);

    // DPI IMPORTS
    // DPI import at /tmp/opentallas-D1-parent-scope-frontend-20261002-r2/rtl/test/w17_D1_scope_corrected_probe/ot_v41_rt_die_D1_scope.sv:223:42
    extern void v41rt_die_register(int rank);

#ifdef __cplusplus
}
#endif

#endif  // guard
