# QW-G5F2 10-20 -- g5f: the die fault-OR tree emitted in the Qwen compute GEN (Q.BIND.1)

Source: claude/qw-g5f2-1020 on claude/qw-g5f-1020 (b9887fdb7 = d502ea9ae g5 + Codex 94341cb20 fault-capture proposal).
Opt-in OT_SPLIT_FAULT_EMIT=1 + OT_SPLIT_FAULT_PLAN (default GENs unchanged). physical_qualification_eligible = false.

## What the pass does (tools/qwen_split/fault_emit.py, hooked in tools/qwen_rom_fulldie_b3r2.py)
- pre (after _late_pin_grant, before _relays): one region-root node qfd_fault_or_n<N> per fault owner block
  (fault_emit_plan_g5.json: the 70 receivers of the 417 landed lanes on the actual g5 die, from its fwd_lanes.json +
  place.tcl by mkplan.py; + the hard fault blocks io_collective / d2d_rom / sys_face / mu_ctxrx / mu_dhobs), on the
  owner's clock (ck_follow = owner) and reset (d2d_rom: borrowed nearest class-reset bus, its own reset is a lane).
  Roots form a degree-8 Manhattan MST rooted at sys_face's root; field roots sit in a band row gap or the W|E seam
  and only link within their zone or to an out-of-field root (dv _poly0 corridor rule). Each edge = 1-bit spine_local
  bus relayed by _relays as a forwarded lane that LANDS on the parent's root; zero-stage cross-root edges get a
  landing station (hook beside OT_SPLIT_LAND_LIST).
- post (after _relays, before _reset_tree): every unconnected landing `fault` (all qfd_landh*, incl. the tree's own
  new landings) and every declared hard fault bit (multi-bit ports split by port_join aliases flt_<port>_<b>) goes to a
  LEAF on its own clock root within 180 um; leaves chain to the region root of the same root with hop nodes every
  <= 340 um centre (same root: no crossing). Node N fixed last (same 21.6 um box for every N). Reach audit of every new
  wire <= 405 um pin to pin, fails closed.
- gen_relay_rtl.py: qfd_fault_or_n<N> wrapper -> rtl/qwen_split/qfd_fault_or.sv #(N) (sticky OR, input pin registers,
  2-stage reset landing; mapped census N16 PASS max 18, QW-G5F).

## Owed / recorded (not fixed here)
- Root output OPEN: bound sys_face view has no obs_fault input (Q.MU.FACE.3 critical kit). No STATUS sink yet.
- io_collective: owner fix = OR its 70 bits into its own `fault` pin (RTL + re-close, COLL owner); die level now
  takes them through 5 leaves with qfd_fault_or (rs load 2 per node, no >32 reset net).
- Leaves use legacy (delayed) capture qfd_fault_or, not Codex's early-sticky qfd_fault_capture (source-only proposal).
- Calendar: fault lanes are observation only (never select or stall); their E/K come from the GEN defaults (no land plan rows).
