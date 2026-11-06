# CODEX HBM bounded parent trial

Updated 2026-11-06. Owner: hbm_parent; canonical plan owner: hbm. This is a diagnostic two-child q_spb2 parent, not parent/die/token closure.

## Current result

PLACE shell PASS, async LEC exit0: epyc6 unit `oth-ubuntu-1429122-1793955200`, intel2 log `~/codex-hbm-parent-1106/place_rstport2.otrun.log`. Actual two signed xcal macros retained. SYNTH:69,585 stdcells+2macros; macro108690um2, standard11657um2. PORT_BIND12505/12505, FACE_GUARD failures0, REG_FANOUT33627regs/over64=0. Final placement rendered/viewed; no stdcell centers inside macros. No route launched.

Important actual PLACE subfailure: OT_RESET_TREE FAIL missing `u_rst_root`; native has synchronous relayed `u_rst_in`. Isolated gen_phys incorrectly treated the partition as die root. Shell exit0 does not clear this failure.

Artifact root (ROOT): `/srv/opentallas-scratch2/claude/codex-hbm-parent-1106` on intel2/epyc2/epyc6. Final DB epyc6 `ROOT/xcal_gen_rstport/q_spb2/run/results/asap7/dp_q_spb2/base/3_place.odb`; image `ROOT/xcal_actual_placement.png` on epyc6, local `coord/tmp/codex-hbm-parent-1106`. Own tools intel2+epyc2 `.../wt/codex-hbm-parent-1106`; never merge these private exploratory copies to main blindly.

## Failures diagnosed and owners

- q_su21 native composition lacks the16 signed p17 lane1 MLAT5 paths; old plain4 uses MLAT4 and different address/data ABI. Attaching real views yielded ZERO lane1 macros and1.37M flattened logic. Never route false join. kit_assembly+hbm now own focused semantic proof/composition, including possible unused VI word4; no fabricated outputs.
- q_spb2 missing internal stations: original native has0pads. Original kit_istations loops duplicate bus rows and fails L83 generated3>laterplanned2. Native L83 width28 versus plan99; stale cfg_data256 rows on L83/L87 are wrong. A diagnostic-only normalized plan coalesced each bus once at max depth/native width and PASSed insertion23stages. No geometry or cycle adoption claim.
- Full-plan reset context is epyc2 `hbm-bind-9/m79fp/die_plan.json` (native provenance). `g_t11m79f/bind_reset.json` requires relayed entry, depth8, release9, rst_o_0, hard reset taps21/22/internal_depth1. Fleet prep owns admitted canonical kit_rsync on this full context, then mandatory bounded stations, then gen honoring canonical sidecars. Preserve kept kit_cells; do not skip reset conventions or regenerate isolated-root geometry. Direct full-context probes stopped (exact own PIDs); no live probe remains.
- Shared kit_assembly helper handles exact source-byte-sealed parameter tuple DD256/PAW11/PREL1/XSLOT1. Its successful contract is intel2 own worktree `results/kit_assembly_1106/hbm_q_spb2/contracts.json`; fleet has it. Shared hard-child classification fix READY `d91819ffd37`, resolving bogus soft guides for real xcal macros.
- Same-face support uses explicit tested turnaround annotations; bounded plan drops only unused L117x2/L138x2 with owner approval. Canonical repair belongs hbm.
- HBM-40 conditional signed-shell latency input+1/output+1 (+2 command/response), reset+2, negative lockup0. Native raw child does not yet consume shell. HBM-42 conditional internal stage debt; original fullplan fixed0/pad0 on all6cohorts, L75/L76 only2boundarycycles versus internal8/5. Token owner reconciling; no adoption claim.

## Concrete geometry repair ready

HBM owner has exact native field map plus all646 actual soft first-capture endpoints. Every used input bit has a legal final bank outside macro+4.32halo within403um, worst385.32um before row allocation. File intel2 `codex-hbm-parent-fieldmap/input_lastbank_legal.json`. Physical cells must use actual .054um site/.270um row grid; conservative footprint1.404x.270um; coordinates are lower-left, not centers.

My `ROOT/output_banks_DRAFT.json` provides all L75/L76 banks at existing8/5 depths,173payload+epoch slots each: row/site legal, no mutual overlap/halo intrusion, actual payload max hops266.706/351.702um. Image `ROOT/output_banks_DRAFT.png` rendered/viewed. Draft still needs input/existing-FIRM occupancy merge and canonical epoch/reset source check. Reproducer `allocate_output_banks.py`.

Source-preserving reduction options, not applied: all1064 L40 launch->face FF hops <=199.962um, so stale internal2 may be unnecessary. L87 soft60bits <=352.35um; hard8statusbits486..603um require relay, coherent1stage may suffice versus stale2. HBM/token owners decide coherent depths. Exact traces `ROOT/output_launch_points.tsv`, `hard_status_output_reach.json`, `command_output_escape_paths.json`.

`ROOT/soft_all_interfaces_relay_sites_DRAFT.json` freezes1770 existing soft FFs (646 input capture+1124 output launch) at actual legal lower-left sites with0cycles, preserving measured endpoint assumptions. Nearest-free placer can displace them: remeasure after fresh PLACE. Do not trust precomputed reach if GPL moves endpoints.

## Next

Combine legal input/output banks, existing soft guides and corrected hard-child classification; reconcile cycle calendar; run fresh admitted prep with full-context reset. Render/review combined geometry, SYNTH/PLACE, inspect parsed reset/station PASS and actual reach, then bounded CTS/GRT/STA. Every prior failed kit/log remains preserved. No blocking owner question.
