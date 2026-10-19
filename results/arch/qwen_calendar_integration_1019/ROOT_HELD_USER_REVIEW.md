ROOT selected the canonical 400 PW template for the next source MODEL. The
source-derived model now validates all 114 direct SU events, replayed under
144 diagnostic stage/user identities: 16,416 exact tuple checks. Sixteen missing,
late, duplicate, wrong-slice/PC/user/stage/generation, authentication/profile/
base, early-retirement and replacement mutants reject. These are executable
MODEL guards, not new hardware or a production schedule.

The actual GI captures `hu` at `s_me/c_seg`, alongside `st`. However, `u_thru`
ORs the live `hu` into `native_pos[17:16]`; it does not snapshot ME/XPF user
identity. The ME head captures token/pos at accepted_start, and fixed ME/XPF
starts still require base0. The current source has no shared guarantee that the
next LOCAL SEG waits until the last ME read and XPF use have retired. The model
requires separate 2-bit ME/XPF snapshots, canonical programme base0, the exact
canonical address at each declared consumer, authenticated cap1 profile and
epoch, and no replacement until both lifetimes finish. Actual publication and
retirement samples remain null. Existing calendar-copy authentication does not
prove the other physical ME/XPF copies.

Qualified canonical bases4096/16384/32768 leave user bits16..17 clear; inserting
the held user reproduces every source-certified per-user XPF address. All other
arithmetic fields remain governed by the existing namespace certificate. No
24-bit adder or new decoder is assumed. Authentication/profile/base guards in
this model need source integration; a Boolean MODEL authentication input is not
a claim that the existing production receiver enforces the new profile.

Two producer-monitor contracts are compared. Typed slice observation can reuse
the existing 16-bit width as `{valid1,user2,slice4,pidx9}` because the SU port
already identifies the unit. The full command target and user exist at GI.
This changes the ABI's meaning and is not implemented. A family-completion
alternative validates all the same required tuples internally, then reports a
completion at a fixed edge one register after the last required issue. It
cannot replace earliest payload/write calibration with the completion time and
cannot gate the producer. Neither option discards repeated slice events.

The actual 114 source issues form 13 family/PIDX groups. Each group has unique
slice identities; its within-family source edge deltas fit8 bits. Immutable
expected templates need13×134=1742 bits, exceeding the present four188-bit XPF
records (752 bits). Candidate state has a775-bit lower bound for four users,
including624 seen bits, clocks, stage, generation, active/fault and snapshots.
ROM return/capture, arbitration, physical landing and possible buffering are
additional. A finite alternative to another ROM is39 unused programme-plane PW
(three64-bit words per134-bit group), bringing400→439PW below976. The existing
ascending75-bit PW input already reaches GI. A sealed13×134-bit control block
would hold1742 bits; the775-bit dynamic state is separate. Aggregate lower-bound
storage would be2517 bits. This needs explicit atomic seal/authentication and
execution-write guards and actual mux/capture timing; it is not implemented.
No reserved footer bits are changed.

A separate native266-bit ROM would consume1,089,536 physical bits;
there is no assigned spare read port on the existing calendar ROM. Template
storage/capture and clock assignment are unselected. No indexed flop block,
ROM, new register chain, API or physical implementation is approved here.

The same-clock source component accounting is cal output publication→GI
observation publication1→monitor publication1→XPF sample1. The independently
entered head/schedule clocks and actual die landing ages remain unbound.
Source W5 offsets are used only for this finite diagnostic replay. The new
model does not alter T49/E8, the public8053632 period, current1009-entry capsule,
INIT800, production FIRST, or the loader's existing88-read contract.

Actual XS3 groups are resid1/resid2, with12 slice issues each. The candidate
consumer predecessor is gu for resid1 and next-stage qkv for resid2; the first
qkv embedding/INIT predecessor and the actual landing/read lifetimes remain
open. The corrected source review enumerates every command and preserves the
retracted intermediate hypotheses only in producer_source_audit.json.

The optional PW packet is now concrete: witness/witness_template_packet contains
the full1024-word MODEL image and manifest. All13 record round trips pass; only
PW400..438 change. Record0's unused high tail carries WTN1/revision/base/count;
no extra header word is needed. The manifest exports the changed candidate
calendar-copy digest, not an installed or authenticated production digest. It
also prices128 partial-record assembly bits and the loaded-mask/loader state
as additional to the earlier template and dynamic-state lower bounds. Current
public PW and all actual receiver images remain unchanged.

Selected held-user source now has an isolated default-off component,
qfd_dv_held_user_xbase.sv. It snapshots two2-bit users and one16-bit context
epoch, tracks two active lifetimes and sticky fault:23 declared FF/reset/clock
pins. It inserts only user bits16..17 after exact canonical/class qualification;
there is no address adder or indexed storage. A native stream→tap test passes
576 source certificate cases/23040 BF16 publications, asserting both ME and XPF
addresses and exact default-off behavior. Ten mutants reject address/user
errors, replacement during a live lifetime, early retirement, wrong epoch,
missing authentication/profile and noncanonical base.

The source inputs are diagnostic contracts: publication, profile/all-copy auth,
context epoch and final ME-read/XPF-use witnesses are not yet connected to
production. The test's ME retirement is a diagnostic assertion after provider
publication, not a real ME last-read proof. No wrapper or external API is
activated. Prior storage models reserved six held-user/valid bits; retaining
this independent component adds17 bits for held epoch and independent fault.
Adjusted candidate totals would be2202FF+SRAM or3305FF, before physical mapping.
No free sharing with the collector epoch/fault state is assumed.
