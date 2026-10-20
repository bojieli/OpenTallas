# CTLM6 recovery source coupons

The opt-in landing reset forest with reset lead preserves the scalar-child reset age and uses each ring rq as the final reset stage. No data offset changes. Real CTLM source allocation: 31 crossings, 69 leaves per region, 3 branches per region, root six loads, +4 reset FFs. This covers the regional landing resets, not the child-internal reset roots.

Verilator 5.050 on ot-epyc7: reset age depths 2 through 5 PASS, including repeated mid-run assertions/releases. ASAP7 mapped maximal 1024-leaf forest coupon depths 2 and 3 both PASS max 32, zero roots over 32 (all non-clock roots, raw/reset included). Artifacts and source recipes are adjacent. The n32 writer is exactly the existing S81 helper from f56222658, connected to per-chunk vector reset leaves; 1073-bit reader-visible lockstep against the original ring PASS 9979 compares over 10000 edges with repeated resets.

These coupons do not qualify the full CTLM. Existing child resets (u_gi 4299, u_go 184), calendar and wide control fanout, clock entries, full native census, reach, physical closure and parent clock compensation remain required. No physical gate launched.
