# NE su31 FF geometry review

Picture: results/hbm_su31_geometry_2158/NE_review.png (viewed).

PASS-COND for the FF geometry fields only; full kit dispatch remains BLOCKED on clock, source, reset and parent joins. No P&R/STA was launched.

All nine actual G2 obstacles are rendered, including five reuse leaves previously missed by the siting helper. All 43,814 internal FF bodies are disjoint and outside macro bodies, on legal rows; canonical check_ft_macro_sites returns zero findings. Every normal-constructor internal hop is at most 404.73 um. The 25 die-oriented neighbor interfaces (26,013 bits) have zero pin mismatches and maximum constructor hop 399.033 um. These are plan capture constructors, not measured placed/route endpoints or STA.

The registers follow the top, center and middle streets and the right edge. Dense bands are visible; M6/M7 routing capacity still needs its prototype. No FF/cycle was added to the NE seven-stage path. The retained legacy banks have a separate conservative 4.32-um expanded-halo diagnostic; the actual required macro-body gate passes.

The current 20 soft clock ports are not qualified: clk_t9 and clk_t14 are inside two real reuse bodies, and 61,777 planned soft FFs require density/load reconciliation. Rebuild the clock/source parent event and capture placements before route/freeze. PDN and physical reset continuity, complete source/view joining, actual routed clock and timing are not qualified here.
