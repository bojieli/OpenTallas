# HEAD-RTL-5 2026-10-27 (s81_head whole-die port-bind: sources from the repo-relative manifest only)

Base claude/head-rtl4-1026@ce0713f99f. Runs via ot-run on intel2 (epyc1 retiring). Numbers CHECKED (recomputed from
cand/ and canon/ port_bind_strict.json, not from the log lines).

## 1. Which ot_s81ph_mem1r1w the head die uses, and why the ref_tile copy differs
- The head die uses rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv. Its instantiations pass .WREG and .rst_n:
  ot_s81ph_link_ep_safe4 u_rb/u_fifo (.WREG(MWR)), ot_s81hd_lep_nr / portfix178 ot_s81sl_slice_lep u_m (.WREG(1)).
  Only this copy can elaborate those instances.
- physical/ref_tile/dscoll_lane_w_rt/src/... is the RTL-of-record snapshot of a different closed tile (top
  dsfd_coll_lane_w, built on the old ot_s81ph_link_ep and not safe4). The tile is not in the head die. It predates 1847d8d72e
  (ds-1010/coll-tu: opt-in WREG registered write port + rst_n port, default WREG=0). At WREG=0 the source behaves as the
  snapshot does, apart from the unused rst_n input. So this is a normal snapshot-vs-later-source gap, not an RTL
  divergence for the head. Rebinding dsfd_coll_lane_w against current rtl/ would need rst_n connected.
- Root cause (tool): ot_s81ph_mem1r1w was NOT in the manifest. die_port_bind indexed its default trees (rtl/ +
  physical/**/rtl), took the first-sorted definition, and the 'first' pick failed because the ports differed. The HEAD-RTL-3 PASS
  came from a sparse checkout without physical/ref_tile, so the verdict depended on which files the checkout held.

## 2. Fix
- tools/die_port_bind.py --manifest-only: indexes only -f / --rtl-file (+ +libdir+ / --lib-root). It does not index the
  rtl/ + physical/**/rtl trees, and it does not use the default macro dirs. A child missing from the manifest is
  unresolved (FAIL), never picked from a tree. A missing manifest entry fails (manifest_missing). Two manifest definitions
  with different ports/parameters fail (ambiguous_children) even when a prefer rank would pick one. --rtl-root,
  --ref-tile-prefer and --prefer-list are refused in this mode.
- _iface: body localparams are no longer counted as interface. A macro's behavioural model and its _bb.v abstract had
  been reported as differing only because of the model's WORDS/BITS localparams.
- tools/s81_head/head_die_portbind.py runs --manifest-only. The manifest is the generated wrappers + plan type `sources`
  + tools/s81_head/head_portbind_extra.f. The supplement lists 18 repo-relative closure files that no type's `sources`
  names (mem1r1w, fp32_f12 + prefix + fastfp, hostb_return, ot_pdie_serdes + 8 KP4 files, 4 macro models), each with
  its instantiating module. They should move into the plan type sources with the next PLAN-DELTA.
- Tests: tools/test_die_port_bind.py adds 7 ManifestOnly tests. One of them reproduces the HEAD-RTL-4 ambiguity in tree
  mode. 31 + 13 (test_die_bind_unread_manifest) OK.

## 3. Candidate (results/arch/head_rtl3_1026/candidate.json) -> cand/: PASS
HEAD_DIE_PORTBIND PASS: module_missing 0; DIE_PORT_BIND PASS, source_mode manifest_only, rtl_roots [], 100 files,
0 under physical/ref_tile; 16 masters, 326 instances; stub 0, input_unconnected 0, input_tied 0, undriven 0,
multi_driven 0, unread 0, output_open 0, unresolved_children 0, ambiguous_children 0, manifest_missing 0; closure 173
modules.
- variant_children 1: ot_sram_1r1w2c_32x64_m1. The plan sources list both the behavioural .v (hd_mesh) and the _bb.v
  (hd_ctl/host). They have the same interface, and the later entry (_bb.v) wins. This is recorded, not silent.
- model children (black-box hard macros): ot_rom_4096x274_m8, ot_sram_1r1w2c_32x64_m1, ot_sram_1r1w_128x256_m1_r0c0.
- spare_out_bits 1660 = 830 rst_o_k + 830 start_o_k on 288 instances. They are all legitimately spare. Checked on
  cand/gen/s81_head_top.sv:
  - 1131 rst_o ports in total, 301 wired to a neighbour's arst_n, 830 open.
  - start_o is open on exactly the same faces at every instance (0 mismatches).
  - Open faces by type: tile_p 792 of 1056 (4 faces, chain uses one), spn 15/25, serdes 10/12, mesh_ep 3/9,
    st_turn 4/8, st_str 4/8, st_m 2/6.
  - Per tools/die_plan/reset_tree.py (OWNER decision 13 wavefront), the pins are the per-type union of the faces any
    instance uses, with no per-instance variants. An unused face's registered relay out is unloaded.
  - No other output is open or unread, and every arst_n is driven (undriven 0).

## 4. Negative control: canonical physical/die_plan/s81_head/die_plan.json -> canon/: FAIL (kept)
module_missing 4. die_port_bind FAIL with stub_masters 3 (ot_s81hd_ctl, ot_s81hd_host_ep, ot_s81hd_mesh_ep self_instance),
spare_out 830, 0 unresolved, 0 ambiguous. The HEAD-RTL-4 epyc1 logs are kept in rtl4_runs/.
