# As-built BF measurement on the main ef870e65aa94 plan kits (S81-FRAME-FIX-1, 11-11)

This directory holds opt-in measurement records for the three as-built BF shapes that the strict-bind compiler
priced as `calendar_unmeasured`. The records are made by the `tools/s81_dv/bf_asbuilt_1101` flow. They are bound to
main's plan kits, which carry the BF go-align fix 477d2ed439a9: col_h9 598afa63580f, col_h10 0b0f9a60d5c6.
The records are `asbuilt_bf_measure_1111.json`, used through `OT_XS_BF_MEAS`:

| key | die frame | pv (BF column partial edge) | leaf_ret_corr |
|---|---|---|---|
| `col_h9_asb_x\|E2\|bseg1024` | u_f_0L02 | e4 324, e8 336, e13 347 | e4 -9, e8 -4 |
| `col_h9_asb_nx\|E2\|bseg1024` | u_f_0L03 | e4 324, e8 336, e13 347 | e4 -9, e8 -4 |
| `col_h10_asb_x\|E2\|bseg1024` | u_f_0L01 | e1 321, e5 330, e10 339 | e1 -9, e5 -9, e10w -4 |

Each pair's descriptor is OFF4 / PER1 / N64 with 0 mismatches. `validated_ops` is attn.wo_a and ffn.router;
attn.cmp.wk is not qualified. Default production stays OFF and no RTL cycles are added. Scope: BF-active, Q
outputs held quiescent, 833 ps, base BF column form.

## Flow (all on intel1 `/srv/opentallas-scratch2/claude/s81-bfasb-1111`, scripts in `scripts/`)
- **Source root** `root` is a `cp -al` of TOK-VERIFY-1 `b3/froot`, built by `frame_root.py` from
  `asbuilt_bs_bf1111.json` (TS5 plus the ef870e kits). The canonical
  `rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h{9,10}_l4_lp_plan_kit.sv` path is relinked to the same kit bytes as the
  manifest's `ext/` copy (`setup.sh`). Before this, that path held a stale base kit, 71fc96 / 57d57d. Schedules are
  TOK-VERIFY-1 `b3/sched`, copied byte-identical.
- **Vectors** (`gen_vec.py`) compile the whole L0 field of the as-built die frame on the bound die top
  `die_b178.v`, using the TS5 bind slice RTL. The first full attn.wo_a phase is then emitted as the BF_LEGACY
  measurement vector. Every BF phase of the field is `calendar_unmeasured` (see `bf_phases_*.json`).
- **Benches**: `prepare.py --native-bf-family --defines-manifest physical/die_plan/s81/bind/frame_asbuilt.json`, then
  walker and static Verilator 5.050 builds (`build.sh`).
- **Per shape** (`run_shape.sh`): walker run, `xs_bf.py measure`, then `replay_vectors.py` for full/tail/router
  (`phase_vector.py` for tail/router from the same field) plus the descriptor_fault and payload_fault controls. These
  run on the static binary, are checked with `xs_place.py check`, and are gathered by `collect.py`.
- **Native family** (`native.sh`): `tb_native_family.sv` on the root's `ot_s81sl_xs4_ctl` gives
  NATIVE_FAMILY_PASS, 96 samples. Its control is the same bench with the legacy one-edge family pulse
  (`tb_pulse.sv`), which fails (`pulse_family_fault_caught`). This control is a reconstruction: the 11-01 runner
  was not retained.

## Results
- **Positive cases.** All three shapes PASS full (WOA 6 rows seg 0/4, phase 106), tail (WOA 5 rows 3/4, phase 125)
  and router (1 row 4/5, phase 130). Every value and return date matches, with fault 0 and trace lockstep. These
  frames have no other row counts.
- **Controls.** descriptor+1 fails with PLAN_MISMATCH one edge late. The W/E weight swap fails with MISMATCH.
- **Old TYPE-SAFE-5 kits** (`old_kit_control/`): the same replay vectors were run on old-kit static benches.
  - H9X full and tail FAIL. There are BFP_BAD programme faults at u_e13 (edges 177..201) and wrong values at
    edges 438/441.
  - H9X router passes because it only uses pair 4.
  - H10X passes all three cases. The die-wide BF phases use pairs 1/5/10 only, so the old e15 fault is never
    exercised. This control does not discriminate on H10.
- **qualify_asbuilt_measurement** (`qualify.log`, `pin_check.log`): all three records PASS on `root`, giving
  `measured_bf_active_idle_q`. `meas_for` accepts wo_a and router and refuses cmp.wk. All are REFUSED on TOK-VERIFY-1
  `a2/froot` (TS5) and on an old root carrying the old kit at the rtl path. The rtl plan-kit pin gives 598afa vs
  71fc96 / c0207a, and 0b0f9a vs 57d57d / 635a79.

## Tool changes
- **`prepare.py`.**
  - The plan kit is taken from the schedule's own source list; an `ext/` kit must be byte-identical to the rtl path.
  - The GB split rom_q element `ot_v41_rom_elem_q_qxpq_w10_gb_split` is quiesced too.
  - `--defines-manifest` is new, because `asbuilt_kva3_g3tag2_sel.json` is absent from frame roots.
- **`collect.py`**: pins the canonical rtl plan-kit path, which is required by `qualify_asbuilt_measurement`.
- **`xs_bf.py measure`**: applies the measured `leaf_ret_corr` on as-built frames, as it already did on LP. The
  current as-built schedules give the BF leaves e4/e8 (H9) and e1/e5/e10w (H10) return paths 4-9 edges longer than the
  RTL. The RTL returns are unchanged from the 11-01 measurement (identical pv, ret_lat and ret dates). Without the
  correction the self-check fails, for example H9 composed 423..442 vs run 414..442.

## Open
- **Column form.** The bench elaborates the base `dsfd_bf_col`: MODDUP keeps `s81_die_bind/dsfd_bf_col.sv` and
  drops the schedule's `dsfd_bf_col3_kit.sv`. The records are therefore base-form (no `bf_col_form` key), and a
  compile on the default rfh3 form shifts them by bf_add.
- **Pins.** The pins match `root`, not a main checkout: 7 of the 102 pins differ there. These are the
  `ext/` kit and hard_params copies, `frame_asbuilt.json`, `die_b178.v` and `col_h9_schedule.json`. A compile must set
  `OT_S81_SELECTED_SOURCE_ROOT` to this root, or to an equivalent one.
- **Not qualified.** Row tags, Q/BF overlap, activation residency and the mission calendar remain unqualified.
