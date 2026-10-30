OWNER OPTION — ADOPTED 2026-10-30 per OWNER (A) 00:10 (see the ADOPTED section at the end). RTL default (no define) unchanged; the canonical child recipe sets the define.

Concrete option for the CAP_ED face failure recorded under OWNER? CODEX-LOG23:10. OT_S81_CAP_ED_FACE_DELAYED_FAULT moves the valid mask into the existing final RF flop (payload/calendar +0cycles) and adds a raw fault-input flop before sticky accumulation plus an isolated output face flop. Output fault visibility is exactly +1edge compared with the original. Extra physical flops=2. No throughput/data-latency change; the phase-end fault check must allow the extra edge if owner accepts this contract. No owner acceptance assumed. No P&R. Native childclock remainsM3.

Actual full ED lockstep for D=3/4/23/24 ×12000cycles at833ps: every66payload/output-valid bits identical, proposed fault exactly equals the original fault delayed1edge with the same reset.248resetedges perD. Wrong-fault-edge mutant caught125mismatches perD; the ORIGINAL0cyclefaultcontract itself differs125edges perD, deliberately explicit. Separate4state run injects unknown fault inputs and alsoPASS using literal oldif semantics, so unknown events hold sticky state rather than bitwiseOR poisoning.

GENPASS136pins. Pure synthesis/FACE/nativeLEC owner-option diagnostic is live on ownkit codex-s81-capchildren-2300/kits/ot_s81sl_cap_ed_owner_option1, ot-run log localhost codex-s81-capchildren-2300/ed_owner_option1.otrun.log. This is not qualification for adopting the changed fault contract. The prior qualified LD017 and pending RTeae remain on distinct branches.

## ADOPTED 2026-10-30 (S81-KITS-E) per OWNER (A) 00:10 PDT
The owner chose (A): one fault-only visibility edge; the single-gate sticky-fault pin contract is not kept. The canonical
child recipe `ot_s81sl_cap_ed` (physical/die_plan/s81/cores/legacy/recipes.json) now builds with
`-DOT_S81_CAP_ED_FACE_DELAYED_FAULT`. The RTL default (no define) is unchanged, so every other user of the module is byte-identical.

Fault-latency price (analytic, per the RTL):
- i_f captured at edge t is visible on o_f at edge t+2 (old form: t+1). Payload/valid/calendar edges: unchanged (0 cycles).
- A word captured at edge t leaves at edge t+D. All instances use D = EDLY = 23 or 24 (cap_end / capc2 / capc5cf, git grep).
  So the fault of the last word is visible D-2 >= 21 edges BEFORE that word leaves the delay line. A phase-end fault check
  that samples after the E drain sees the same fault value as before. Slack = D-2 edges, so no phase-end extension is needed.
- Parent consequence: benches that compare the cap fault edge for edge against the old gold (tb_s81sl_capc5r_gold etc.)
  must allow +1 on the E-path fault when the parent is built with the define. Like the slice leaf fault
  (tools/s81_slice/slice_flat_gen.py) and xr1f, this is a diagnostic flag, not a schedule input.

Re-checked by S81-KITS-E (intel2 /srv/opentallas-scratch2/claude/s81-kits-e/{ed_miter,ed_bench}, CHECKED):
- ed_miter.py + ed_miter_4state.py (portable now: args repo_root out_dir) on this tree: ALL_PASS for D=3/4/23/24, 12000 cycles,
  payload 0 mismatches, fault == old fault delayed 1 edge, wrong-edge mutant caught 125/D, 248 reset edges/D.
- The existing bench rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_cap_ed.sv with the define: PASS (197 checks) for D=24 and D=23.
  Mutant DM=23 vs DX=24: FAIL as required (290 errs). Log: ed_bench.log.
- Native kit synth LEC with the define (Codex kit intel1 codex-s81-capchildren-2300/kits/ot_s81sl_cap_ed_owner_option1,
  RTL md5 3e87efa9 = this commit): EQUIVALENT, 1673 compare points, FACE guard 134/134 PASS raw and post-synth.
