Bank data seam/edge algebra diagnostic, no timing exceptions

Exact physical endpoint plan provides216bank-data seams /111120bits and108written-flag bindings /4752bits. Each seam lists physical W/Rhardchild/parentclock-domain identities and slot-to-face mapping. Written flags are explicitly ordinary timing. Select/status/reset/epoch/control paths are not granted a data window.

D4K2 enumerates writer edge n-K, selected receiver edge n+phi, next same-slot overwrite n-K+D. Diagnostic phi in[-0.4,+0.4]T gives1.6T minimum setup age and overwrite gap. Premature D2 overwrite mutant fails with-0.4T minimum hold gap. This does not certify actual native phases.

At actual registered data endpoints, max data-path delay must satisfy K*T+delta_clock_RminusW_TT-CQmax-setup-Usetup-150ps. Min data-path delay must satisfy (K-D)*T+delta_clock_RminusW_FF+hold+Uhold+100ps-CQmin. The paired register-clock delta must include actual compensated root delivery/phase and child insertion, at the appropriate corner. Terms cannot be substituted by unqualified whole-bank extrema. With hard macros the tool/schema owner must qualify equivalent bank-pin arc/seam bounds, since internal flop pins are not directly visible in the parent.

No numerical exception budget or Tcl/schema dispatch is emitted, and exception_authorized=false on every seam. Actual W/R corner arcs, native parent phase envelope/root spreads,150/100reserves, reset/written/absolute-age proof, physical405routes and owner/root constraint approval remain required. Local reset-order and logical MODELv7 witnesses are references only. Physical half MODELv8 is still running and not used here as a qualification claim.
