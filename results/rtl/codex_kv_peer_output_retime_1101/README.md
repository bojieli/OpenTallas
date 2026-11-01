# KV peer zero-cycle output retiming experiment (disabled)

Current native `qkd_hr_core_peer` has 78 combinational outputs. Fully flattening
kept helpers leaves the same count: these are real output cones. 76 bits end
exclusively at `$adff` Qs sharing clock and reset. The opt-in experiment copies
their combinational functions before a new private output FF, substitutes each
original Q with its exact D, and computes each new FF reset from the same
function of original reset values. This preserves the original output cycle.
It adds 76 FF bits and changes no canonical source or recipe.

The actual complete-core scratch transformation changes the raw report from
78 to 2 unregistered outputs. It still reports 485 logic inputs, 1338 multi
inputs and 12 constant outputs. These are transformation statistics, not
mapped CORE_PREFLIGHT results. The remaining `dispatch_valid` cone depends
on current `token_grant_ready`; `token_request_ready` depends on current request
position/token and reset. They need a concrete boundary redesign or a separately
priced protocol change. No extra cycle or gate exemption has been introduced.

The portable coupon uses the actual 76 native combinational cones and resets.
Original FF D signals are arbitrary common inputs (equal native Ds remain the
same input). It proves the retiming identity for every such input sequence,
independent of the rest of the controller. The frozen JSONs contain only those
cones, their FFs and coupon ports. No native macro or source is replaced by a
blackbox. Gold has 236 cells; gate has private output FFs and copied logic.

`coupon.log`: all 76 output equivalence points proved. `coupon_mut.log`: inverting
one new FF D makes `u_coordinator__accepted_ranks[0]` fail (75 proven, 1 unproven).
Receipt: post rc0, mutant rc1. Fleet run epyc2
`oth-ubuntu-1393817-1793549375`. Inputs and experimental complete-core output remain
at `/srv/opentallas-scratch2/claude/codex-kv-peer-flat-1101` on epyc2.

This coupon establishes the local retiming identity only. It does not close the
remaining input/output classes, replace the existing full peer proofs, establish
physical boundary legality, or claim timing/SIGNED closure. The experiment is
not enabled in any source generation path.
