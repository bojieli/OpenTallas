# Disabled peer landing preparation

The current native peer cut has 78 combinational outputs, 485 logic input bits,
1338 multiple-load input bits and 12 constant output bits. Its old face-copy
proofs remain running and are preserved; those proofs alone cannot close this cut.

The root coordinator approved a disabled common protocol landing candidate on
11-01 11:31, with its extra mission edge explicitly priced. `landing_profile.py`
retains native state/arithmetic, lands every non-clock input, and captures each
output's exact native next-state function using the OLD landed inputs. Resets
also land. The sampled synchronous transducer therefore adds one mission edge
and one boot/reset edge. The input and output capture overlap; they do not add
two mission edges. No canonical source, plan or recipe enables this tool.

Full frozen native peer projection: 1827 input FF bits and 2016 output FF bits
added (3843 total). Its raw transformed boundary report has zero unregistered,
feedthrough, dropped, logic-input, multi-input or constant-output categories.
This is a JSON transformation screen, **not mapped CORE_PREFLIGHT or physical
signoff**. Constant output FF preservation needs the qualified keepdc flow hook.

Actual minimum protocol vehicle: the unchanged full four-user/eight-rank native
`ot_qwen_tp8_token_cohort_mu`. Compare all 83 output bits against the previous
native sampled edge, across eight complete begin/request/dispatch/terminal
transactions and reset replay: **155 complete words checked, eight dispatches,
eight terminals, zero mismatches/faults**. Inverting one output capture D fails
at cycle5. Fleet unit epyc2 `oth-ubuntu-1327840-1793562702`, rc0 including expected
mutant rc1. The initial attempt failed only its after-consumption dispatch
coverage counter; its failed log remains in the original remote directory.

Model contract before adoption:

- One added 833ps edge per traversal of this peer transducer; feedback paths add
  the sum over peer visits. Producer/consumer calendars and timeout windows must
  include it, and throughput must be measured on the composed protocol.
- One added boot/reset edge. Clock runs while reset is asserted. No power-up
  output validity is claimed before the existing reset/boot sequence.
- No extra boundary bits, clock domain, numeric change or timing waiver.
- Area includes 3843 additional FF bits plus duplicated output-decode logic;
  actual mapped area, slot fit, clocks, TT/FF timing and normal physical gates
  remain unmeasured. No current plan outline is asserted adequate.

**Canonical adoption HELD.** The component coupon establishes the sampled
retiming mechanism on the native protocol. Full current-peer protocol/feedback
and compiler composition, source identity, mapped boundary checks and normal
model/physical gates remain required. No existing full-peer proof or SIGNED
receipt is replaced by this coupon.

Reproduce by staging `tools/qwen_kv_die/mu_peer/landing1131/stage.py OUT` and
running `run.sh` in OUT through `ot-run`. Complete frozen peer artifacts remain
at epyc2 `/srv/opentallas-scratch2/claude/codex-kv-peer-land-1131/full`.
