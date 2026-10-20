# CTLM6 recovery source coupons

The opt-in landing reset forest with reset lead preserves the scalar-child reset age and uses each ring rq as the final reset stage. No data offset changes. Real CTLM source allocation: 31 crossings, 69 leaves per region, 3 branches per region, root six loads, +4 reset FFs. This covers the regional landing resets, not the child-internal reset roots.

Verilator 5.050 on ot-epyc7: reset age depths 2 through 5 PASS, including repeated mid-run assertions/releases. ASAP7 mapped maximal 1024-leaf forest coupon depths 2 and 3 both PASS max 32, zero roots over 32 (all non-clock roots, raw/reset included). Artifacts and source recipes are adjacent. The n32 writer is exactly the existing S81 helper from f56222658, connected to per-chunk vector reset leaves; 1073-bit reader-visible lockstep against the original ring PASS 9979 compares over 10000 edges with repeated resets.

These coupons do not qualify the full CTLM. Existing child resets (u_gi 4299, u_go 184), calendar and wide control fanout, clock entries, full native census, reach, physical closure and parent clock compensation remain required. No physical gate launched.

## Claude return: preserved evidence, no full qualification

STOP received; no new launches, submissions, merges or further qualification. Source branch codex/qw-ctlm6-recovery-1020 at 49c5833e9 includes the strict macro constructor, mapped MUX select cost, DFFE normalization, source-bound simulation-only closed macro parameters, and opt-in clock-entry source support. The working helper edit is uncommitted and preserved as WIP_undef_mux_receipt.patch; it has not been integration-tested or adopted for physical work and requires ROOT tool review.

Full generic construction: 60562 source cells to 61772 bounded cells, ten actual macros retained. The actual full ASAP7 native5 audit has maximum non-clock load 32 and zero fanout violations, but FAILS strict census for ten literal-X mux inputs. Adjacent native.json and trace_unknown.log preserve that failure. Source SAT proof6 proves all ten X arms unobservable across 44570 effective next-state/clock/reset/macro-input/top-output bits, cutting FF state and macro outputs into shared arbitrary symbols; positive PASS and causal known-arm negative FAIL plus VCD are preserved. This does not turn the native census into a PASS.

The full original-vs-bounded real-macro bench5 FAILS only command_stage (2901/56259 comparisons); remaining 53358 match. Physical closed h16c uses STAGE_ME=1 while the behavioral default is 0. Commit 49c5833e9 adds strict source-hashed simulation-only parameter metadata; corrected full bench was NOT launched. No corrected bounded candidate or full mapped audit was run after the WIP X refinement. No physical gate launched for CTLM6. Own-entry clocks remain source-only: real child references, hybrid gate binding, full root envelope and parent/die compensation remain unqualified.

Remote artifacts remain at ot-epyc7:/srv/opentallas-scratch/claude/codex-ctlm6-recovery-1020/{generic3,generic5,native5,proof6,bench5_obj}; local scratch /home/ubuntu/scratch/codex-ctlm6-recovery-1020. All our heavy proof/mapping/bench jobs were terminal at STOP. Existing SUVM fleet jobs and ctl5 route job are preserved.
