# ROWX SRAM source and physical inventory

`dsdv_rowx_xm_sram` is the explicit native-SRAM physical top. The existing XM defaults to `USE_SRAM=0`; original RP and LC files are unchanged. The source contains no extra data/boot cycles. The static slot schedule and all FIFO-head behavior remain the same.

RP reads the next output index one edge early, including index0 at ci40. SRAM read-before-write collisions forward the actual write payload, which is essential for B[0] at ci40. LC reads rp_next on every edge and forwards empty-push and last-pop+push, preserving the combinational head on every cycle.

Native raw and p192-macro minimal lockstep (including final active-restart corner): bad0,640RP slots, LC bypass mutant105 mismatches, RP bypass mutant320 mismatches, RP fault0. Final restart miter bad0; existing default XM and explicit native physical top build lint PASS. Production16-owner packed transport using real p192 models: seed9/rate764/all15links37cycles/jitter4 PASS,2049words per receiver,err0. TRANSPORT_TIMING first_export22/span3629/hop_sum1365 exactly matches committed gold bench3b run_base_pk16_s9.log. These are RTL gates, not timing sign-off.

Seven physical macros per XM:3 existing64x512p192_mir and4 mask32/RW-preserving32x512p192_mir.94208logical bits use163840physical bits because unusedrows are padded. Pin-access-correct total macro area148883.58um² (raw dense-core minimum75393.30um² is not the physicallot). New32x512p192 generator uses the existing calibrated p192 pin-lead timing method; originalmacro views are immutable. TT/FF are the closure corners; generatedSSlib is informational only.

Standalone plan-form recipe proposes492.48x669.6um with48um channels and4.32um macrohalos; centreclockentry. `physical/ref_tile/dsdv_rowx_xm_sram/spec.json` + `recipes.json` carry all native sources, views and sites. Pins/entry/tree slice still come from the approved parent plan. No route is permitted by this proposal.

Actual existing svc5/svc11 lot census FAILED, even for a single SRAM with4.32halo: each partition is filled by64attention+8HROW cores with~17um gaps. S81 plan owner is exploring constrained repack/adjacentlot; this failure is not waived. Baseline immutable plan SHA2565b91b79891cafabe60423fbd83ed68136378e47cbf4d04e57d7e8329f4df1ede. Do not place or route these macros into the existing occupied lot.
