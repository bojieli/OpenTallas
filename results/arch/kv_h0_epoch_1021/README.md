# KV actual hop-0 epoch correction

Every forwarded KV lane's FIRST cell captures its enable on the source clock.
The existing generator and KV lane checker counted that capture only for
single-station lanes. Multi-station lanes consequently strapped K one epoch
short while the checker accepted the same incorrect calendar.

Both now use `lane_groups.hop0_en_reg`, the canonical existing rule for every
nonempty lane. The benchmark and fixtures count that same actual capture. This
changes K for multi-station lanes by one modulo eight; it does not add a data
pipeline stage or increase the correctly compiled steady-state age `E + 1`.

Base is current KV integration `f382f7eaf`: current main plus INTEG18m, AHUB
post-station padding, and PROG17's production pair work. The correction is
limited to the epoch calculation and its checker. It preserves AHUB padding,
production image settings, and all reset-source identities.

## Collected evidence

The actual RTL benchmark on that source covers NF 1/2/5/15/40, 89 real
`qkd_rlys_1` reset transport/capture edges, and changing payloads:

| Case | Existing run result |
| --- | --- |
| Correct H0 on every FIRST, G-R0 priced | PASS: 2,400 checks, zero errors/faults |
| New reset date but stale K | Expected FAIL: 2,400 errors |
| Missing capture, calendar still prices 89 | Expected FAIL: 2,397 errors |
| Historical H0 only for NF1 | Expected FAIL: 1,920 errors |

Pinned Verilator 5.050, unpinned ot-run unit
`oth-ubuntu-3376417-1792567819`, terminal exit 0. Generated bench, source hashes,
and all three committed causal witnesses accompany the receipt. The current
checker suite passes 16 tests, including explicit refusal of the historical
NF1-only epoch calculation, unit `3379056-1792567933`, terminal exit 0.
Both jobs were already running before the instruction to stop additional
validation campaigns; no further checks were launched afterward.

Historical failure evidence remains in branch `codex/kv-reset-distribution-2244`
at `a084c6fbf`, including the full-NF 1,920-error failure and the narrower PLL
NF1 proof. These are not overwritten by the corrected result.

## Remaining physical reset work

The source-typed diagnostic on the old exact d22bu netlist has 11,964 directed
reset port pairs, of which 448 exceed 405 um: 265 en, 176 rs, and seven rst_n.
The source typing removes the bogus input-as-driver relay-a pairs. Its 28,959.8
um PLL enable span remains real. These numbers describe the old diagnostic
case, not a completed current production die.

The separate full-rectangle site model found 87 transport plus two capture
stages with maximum span 360.636 um for that PLL endpoint. Its review-only
patches remain unapplied. This correction does not adopt those 89 edges or
claim their cold-boot/reset calendar is qualified.

Current reset source clocks, absolute G/R0 dates, per-source boot/first-use
profiles, retirement coverage, and the PROG17 HOLD325 versus HOLD273 issue
still require actual release integration. The H0 fix supplies the correct
FIRST epoch to that integration; it does not substitute a generic protocol
proof for the production R16 calendar or infer cold-boot dates.
