// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: main() simulation loop, created with --main

#include "verilated.h"
#include "Vtb_dsfd_sp_vm_static.h"
#include "Vtb_dsfd_sp_vm_static___024root.h"

//======================

int main(int argc, char** argv, char**) {
    // Setup context, defaults, and parse command line
    Verilated::debug(0);
    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};
    contextp->threads(1);
    contextp->commandArgs(argc, argv);

    // Construct the Verilated model, from Vtop.h generated from Verilating
    const std::unique_ptr<Vtb_dsfd_sp_vm_static> topp{new Vtb_dsfd_sp_vm_static{contextp.get(), ""}};

    // Simulate until $finish
    while (VL_LIKELY(!contextp->gotFinish())) {
        // Evaluate model
        topp->eval();
if(contextp->time()>12000 && contextp->time()<22000) printf("STATE time=%llu t=%u rss=%u mark=%u en_b=%u tp=%u mk_q=%u u_c__bpar=%u tp=%u te=%u warm=%u mk=%u tp=%u tp=%u\n",(unsigned long long)contextp->time(),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__t_ck),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__rss),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__mark),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__u_t__DOT__captured__DOT__en_b),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__u_t__DOT__captured__DOT__tp),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__u_t__DOT__captured__DOT__mk_q),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__u_t__DOT____Vcellinp__captured__DOT__u_c__bpar),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__u_t__DOT__captured__DOT__u_c__DOT__tp),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__u_t__DOT__captured__DOT__u_c__DOT__te),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__u_t__DOT__captured__DOT__u_c__DOT__warm),unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__u_t__DOT__captured__DOT__u_c__DOT__mk),unsigned(topp->rootp->__Vdly__tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__u_t__DOT__captured__DOT__tp),unsigned(topp->rootp->__Vdly__tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__lane__BRA__0__KET____DOT__u_x__DOT__u_t__DOT__captured__DOT__u_c__DOT__tp));
        // Advance time
        if (!topp->eventsPending()) break;
        contextp->time(topp->nextTimeSlot());
    }

    if (VL_LIKELY(!contextp->gotFinish())) {
        VL_DEBUG_IF(VL_PRINTF("+ Exiting without $finish; no events left\n"););
    }

    // Execute 'final' processes
    topp->final();

    printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__s_flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT__s_flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__0__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__0__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__0__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__0__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__1__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__1__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__1__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__1__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__2__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__2__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__2__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__2__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__3__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__3__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__3__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__3__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__4__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__4__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__4__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__4__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__5__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__5__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__5__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__5__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__6__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__6__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__6__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__6__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__7__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__7__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__7__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__7__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__8__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__8__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__8__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__8__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__9__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__9__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__9__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__9__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__10__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__10__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__10__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__10__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__11__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__11__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__11__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__11__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__12__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__12__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__12__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__12__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__13__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__13__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__13__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__13__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__14__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__14__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__14__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__14__KET____DOT__u_x__fault));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__15__KET____DOT__u_l__flt=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__15__KET____DOT__u_l__flt));
printf("DIAG tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__15__KET____DOT__u_x__fault=%u\n",unsigned(topp->rootp->tb_dsfd_sp_vm_static__DOT__dut__DOT__u_cap__DOT____Vcellout__lane__BRA__15__KET____DOT__u_x__fault));
// Print statistical summary report
    contextp->statsPrintSummary();

    return 0;
}
