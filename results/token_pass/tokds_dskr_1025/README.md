# TOK-DS dskr: deskew L0 NX cut replays rebuilt from committed sources (2026-10-25)

Successor of `results/token_pass/tokds_dsk_replay_1025` + `tokds_entry_vp_1025` (ec43, 05:00-06:40). Those PASS records cannot
be re-verified any more and fail closure-order rule 3: every input sat at absolute epyc3 scratch paths, epyc3 was retired at
20:15 without its scratch, and their XRT `ec43bbd4` was never committed (it is in no git object on GitHub or the epyc1 hub,
on no fleet host and not in the archive). This record re-runs the same chain on this commit only.

Vehicle (every input reproducible from this commit):
- `inputs_blobs.txt` + `inputs_data/` -> `tools/s81_dv/tokfunc/fc31/materialize_blobs.py` -> the 845 input files
  (`inputs.sha256`): recovered fc30 cuts/kits, fc31 die.v `35ba1ef7` (= the 10-25 entry receipt's die), cap30 plan/land.
  777 are git blobs already in the repo, 68 are committed data (cut tops/ports, die.v, land.json).
- `tools/s81_dv/tokfunc/fc31/prep_dskr.sh <IN> <W>/veh`: fc31 station patch, reclock, kit XRT := `ot_s81sl_xrt.sv` at
  main `c2ef1998e` (sha256 `18850f53`: cfc3 + NORM-DESKEW PDSK 01234, FACE_LAND 0 / no XR_PDC by default, same ports as the
  kits' cfc3 XRT). HEAD's XRT has FACE_LAND 1 (+1 leaf-interface cycle), wrong for these cfc3-era cuts. mk_tree on fc31.
  `veh/vehicle.json` lists every output sha256.
- `tools/s81_dv/tokfunc/fc31/mk_srcroot_dskr.py --out <W>/src`: selected source root = root30 from git blobs
  (`root30_blobs.txt`, 13,168 files; `root30_cells_used.v` is the only file no commit holds) + this checkout's tools + the
  c2ef1998e XRT. `xr_timing.XRT_MODEL` gains `18850f53` (7 edges, same justification as ec43; source model only).
- Fixtures `fix/L0`: 171 files, all match `results/rtl/s81_layer_tput_1018/fixtures/L0.sha256.json`.

Chain: `run_dskr.sh <W> fs|compile|receipt|entry|cuts`, driven by `drive_dskr.sh` (waits for the 4 cut binaries from
`tools/s81_dv/run_dv_slice.sh veh/cuts/K_<cut>`). Paths under `runs.*.path` in the receipts are run-time locations; the
committed copies here carry the same sha256.

Results (intel2 `/srv/opentallas-scratch2/claude/tok-ds-dskr`, commit noted per item):
- Entry-port mechanism gate (`tools/s81_dv/entry_vp_1025`, run from `<W>/src`): w PASS (ri_w sid 11), ev PASS (ri_e sid 5,
  vi sid 9); pin->store commit 10, HLOAD 29, GAIN 21 edges on all three ports (same values as ec43); payload mutants FAIL as
  required. Receipt `entry_mechanism_dskr.json` PASS (commit 1e7adc7151 tools).
- Strict `entry_boot.py` on the receipt: 40 native HOST jobs compiled, no source drift ("PARTIAL: real host/global route
  adoption held", same scope as before).
- L0 compile (`dv_layer_compile --entry-norm-check all`, 14:14 wall, 0.78 GB) + `norm_phase.py`: attn.entry_norm_nx 4,298
  events included / 1,923 excluded, nx_timing_delta 0 (same 4,298-event phase as codex_nx138).
- Cut binaries, native HOST entry replay (cut_3S_ctl jobs 15/16/17/20/21/22 + hf_7N bit33 control) and the cut_0S / 0N / 7
  replays (base, input-corrupt, expect-shift) under the strict check: see the PARKED section of lanes/TOK-DS.md (pending at
  writing).

Scope unchanged: component evidence on pre-adopt178 deskew cuts, L0 NX arithmetic phase, full_token false.
