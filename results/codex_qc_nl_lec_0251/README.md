# Fresh NL gate LEC takeover

Source base d7eb2d8813 (QC-A0-KITS-11); fresh mapped parent gate from
intel1 codex-qc-nl-lec-1029/reset_newgate, built 02:00 PDT. Sources untouched.

Transferred assumptions are not accepted without proof. Diagnostic `refresh.py`
rechecks all assumptions from predecessor model, rejects 57 refuted gold KV
address-prep relations and proves remaining 12,513 jointly. Actual complete
comparison then proves 31,580 / 31,685, with 105 address-prep differences.
This is **FAIL**, not a complete equivalence claim.

`fresh.py` regenerates all correspondence from the actual fresh gold/gate AIGs,
then proves seven existing guarded-zero KV nb_t relations and the full miter.
Job intel1 unit oth-ubuntu-1934993-1793267664, run directory
/srv/opentallas-scratch2/claude/codex-qc-nl-lec-0251/fresh.

No RTL, clock, constraints or latency changes. No P&R permitted on this diagnostic.

## Fresh actual gate result

**PASS**: native comparison 31,742 / 31,742 proved, joint hypothesis outputs
12,570 / 12,570 proved. Kept registers 9,881 / 9,881 present, zero missing or
constant. Actual AIG/map/alias/keep hashes are in summary.json.

The precise repair is in reanchored57.json: every unmatched address-prep support
bit has one surviving matched register at the same bit in another group. Reanchor
to that matched register, rather than another unmatched gold copy. All 57 repaired
relations are proved together with every other relation. Examples: q_p[0][11] to
q_p[2][11], c_p[1][11] to c_p[2][11], and r_part sibling copies to the surviving
same-bit matched representative. No functional RTL changes were needed.

Negative control: invert one proposed relation. The same induction proof catches
28 differences (12,542 remain proved), proving the profile is checked rather than
assumed. See wrong_representative.log and summary.json.

Native unit oth-ubuntu-2003882-1793267946 EXIT0; kept/control unit
oth-ubuntu-2024267-1793268020 EXIT0, both intel1 under the own run directory above.
Full generic correspondence discovery remains running in fresh/ as independent
diagnostic work; its outcome does not replace the passing explicit profile.

native_profile.json contains the complete proved hypothesis profile (no constraints
were introduced; the FSM constraint set is empty). replay.py reconstructs the
normalization and checks input identities, all loaded-guard reset bases, every
inductive relation and every compare point; it avoids a dependency on pickle.
Replay script is supplied for reuse; the passing run used target.py on the exact
saved fresh-gate model and has not repeated the expensive normalization.

This closes the fresh NL **logic proof only**. Parent geometry, clock and physical
gates remain the A0 owner's responsibility. There is no P&R/STA approval here.
