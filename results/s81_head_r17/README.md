# HEAD-CORE-R17 (2026-10-27)

## Task 1: per-mode post-route ECO (tools/s81_head/head_post_route_eco.sh, head_eco_post.tcl, head_eco_modes.py)
The ECO now uses the same per-mode binding that R16 gave the rebuild:
- Scene tc (mode ss) is TT setup under constraint.sdc, with vclk at 250.
- Scene BC (mode ff) is FF hold, with vclk_ff.sdc at 202.5 = OT_VCLK_FF = sdc_lint insertion_ff_ps.

What changed:
- orfs_hold_mm is now patched in the ECO container.
- The `CORNERS=tc bc` command-line override is gone.
- The global FF latency line is removed from the PRE hook (written as bind_ff_eco.tcl).
- The sign-off FF bound is taken from the kit.
- head_eco_post.tcl runs `ot_mm_sync` first, then reads the routed SPEF. It then runs the owner 10-25 structural FF hold gate, then the KV eco_route recipe, then `ot_mm_unsync`. It refuses to run in a single-mode session.
- head_eco_modes.py FAILS CLOSED (exit 2, writes nothing) if any of these disagree: config.mk OT_VCLK_FF/TT, sdc_lint.json, constraint.sdc, the hook latency, an existing vclk_ff.sdc, or the sign-off bound.
- tests/test_head_eco_modes.py: 14 PASS (CHECKED).
- Real kits under --check: elemA_eco, elemA_hold2 and R16 elemA_m2/elemB are ok. elemB_src FAILs (stale vclk_ff 170), as it should.

Probe on the signed-off elemA_eco DB (eco_mm_probe/, CHECKED). Comparing the mm session plus read_spef against the single-BC session:
- tc setup 122.363 = the signoff TT value of +122.36.
- BC hold 3.835 against single-BC 4.428, so the mm session is 0.6 ps more conservative.
- So read_spef (no -corner) reaches both scenes.

## Task 3: R16 reruns
- elemA m2 and m12 both STOPPED at GRT at 06:40. The owner 10-25 structural FF hold gate fired:
  - FF hold ws -102.82 / -102.96 ps, against the gate limit of -100;
  - 795 / 810 true failing endpoints;
  - TT setup +122.88 / +123.12 (tool numbers, UNCHECKED).
- Root cause is the input pin-register boundary contract: in_min -40 against vclk FF 202.5, with the in-band centre-entry tree about 25 ps later at FF than hold2. ASK posted in COORD-REVIEW-QUEUE.
- Chain head_r17_route_chain.sh is LIVE on intel1 for head-core-r16/elemA_{m2,m12}: GRT without GRT hold (rc 0 at 07:25) -> STA -> route -> R17 ECO -> sign-off -> LEC.
  - The ECO structural gate stays on, so the hold step stops unless COORD rules.
  - Log: KIT/r17_chain.log, R17C_ lines; ECO in KIT.eco/eco_chain.log.
- Pitfall: the kit's R14 block has `override export SKIP_INCREMENTAL_REPAIR = 0`, which beats the command line. The chain appends an override instead.
- elemB (epyc2 head-core-r16/elemB): GRT HB4 repair is live at FF -78.81, which passes the gate. The intel2 waiter (head-core-r17/elemB_waiter.sh) starts the same chain on 'R14RB done'.

## Task 2: shared-bug audit
Results are in COORD-REVIEW-QUEUE (2026-10-27 06:59).

## Tasks 4/5
Separate branches:
- claude/head-r17-tree-1027: tree fix plus pin files from the real views.
- claude/head-r17-rtl-1027: copy-B burst depth 2 from the protocol bound, with bench and mutant.
