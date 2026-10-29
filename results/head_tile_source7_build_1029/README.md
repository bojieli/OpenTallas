Canonical HEAD tile SOURCE7 candidate build.

Input is the portable source7 packet from codex/head-start-0251@bb309fa0e, preserving the qualified native FWD_COPY1 and per-type registered reset aliases. The new own branch merges current main while retaining both native START and leaf-origin options (39focusedtestsPASS), then applies qualified data-corridor helpers and the OFFdefaultcontrol-copy source/generator. The build driver explicitly enables landing_control_status_copy only on hd_tile, adds8FF/0cycles, and carries the existing native physical clock budget525TT/425.25FF. Gen2 validates all21types, patches raw reset aliases only after generated landing RTL, and installs source-based data placement.

Gen1 FAIL: strict schema lacked21start_capture_um+19reset_start_raw_exports+1landing_control_status_copy field registrations. Exact typed registrations74f55ed48 resolve these without dropping metadata or bypassing validation;20schema/status-copy focusedtestsPASS. Failed gen1 log retained. Actual GEN2 source receipt: FWD_COPY1 retained,15hd_tile raw-reset exports,+8FF/0cycles,2440data placement targets. No physical timing or signoff claim.

Reproduce from a clean checkout:

    mkdir -p run/head_tile_source7_1029
    tar xzf results/head_tile_source7_build_1029/source7_portable.tar.gz -C run/head_tile_source7_1029
    python3 tools/s81_head/head_tile_source7_kit.py run/head_tile_source7_1029/head_start_source7 --out run/head_tile_source7_1029/gen

Trial-place review: results/geom_review/head_tile_source7_prebuild_1029.md. Start with canonical run_kit.sh goal synth; require source/face/LEC PASS before PLACE. Fresh actual new-FF clock model/assignment is mandatory before CTS. Route remains held. All measured prior raw clock/ring failures and the corrected435FIRMbaseline belong to earlier source versions, not this new candidate.
