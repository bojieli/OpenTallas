# DIE-QC-101 handoff (QC die owner; COORD coordinates) -- started 2026-11-13 17:41 PST

## Scope
QC ONE FINAL event s29 (R-PROFILE/R-MINIMAL): strict bind + LATCHECK clean -> adopt in wave with KIT-OPS-2 -> relaunch all QC types;
pilot one type per family in parallel (OWNER: do not wait for pilots). Coordinate KIT-FIX-F (kit snapshot / srcs27 losses).

## Where
- Event tree (Codex, reused): epyc9 /srv/opentallas-scratch2/claude/wt/qc-s29-tree2 (branch claude/qc-s29-tree2-1113 @1e3b302be8; plan files untracked in POR).
- Codex scripts: epyc9 /srv/opentallas-scratch2/claude/qc-s29-reach (finish_bind_codex.sh, run_bind_isolated_codex.sh).
- My dir: epyc9 /srv/opentallas-scratch2/claude/die-qc-101 (kitwin_f547_delta.json, zz_s29_qc101_win.json copy).
- Bind outputs: epyc9 /srv/opentallas-scratch2/claude/qc-s28-hf1c/bind/bind_s29_qc101{a,w}_{pre,final}(.log).
- Local scratch: localhost scratchpad qc101/ (post.sh = queue poster, bind_*.log ot-run client logs).

## Event content
- forms f547f1a6f7a4 (POR zz_postphase_reset_ctl8inc1_geometry_codex.json) + per-port windows (kitwin delta from qc-region-1/htdme2/gate/kitwin.json,
  CTL __v1 copy parent) = POR zz_s29_qc101_win.json 1c34c43d3544. Identity sidecar qc-s29-reach/side_ctl8inc2_identities_codex.json 2dc5994fc2a0.
- Regional clock: f547 STA/K proof = qc-region-1/htdme2 (third-chain recipe; CA FAIL 0, START 763 clean).
- OPEN: extra c_* clock entries (320 ports / 11 types > 208 ps, capped at 208); advisory under R-MINIMAL.

## State
- 17:46 STATE posted (coord 3ba28f80475). Binds running: s29_qc101a (f547), s29_qc101w (windowed = adoption candidate).
