# S81 native PG terminal binding: cause, PG-bind-only ECO, receipts (LEAD2-S81/NATIVE 10-19)

Tree S81.STA.PG. Follows `results/rtl/s81_capc_pg_terminal_audit_1019` and `results/rtl/s81_selected_pg_terminal_audit_1019`
(CAPC 3732 / cap_rt 1186 / cap_tr 658 / HSLOT 332 / MU land 304 unbound VDD/VSS terminals, all PG_HOLD).

## Cause (measured, not inferred from names)

OpenROAD `global_connect` skips every instance with dont_touch set (`src/odb/src/db/dbGlobalConnect.cpp:163`, OpenROAD
6cb3f2b704, the fleet image). CTS buffers (clkbuf_sp_*), wire and place repair buffers are inserted after the PDN-time
global_connect, and then the flow protects them (`clk_net_protect.tcl`, `clock_spine.tcl`, `out_pin_driver.tcl`, `icg_dont_touch.tcl`
in default mode set dont_touch without binding first). The final ORFS global_connect therefore skips them. This ECO counts,
per view, how many unbound instances carried dont_touch: **all of them** (1866/1866, 593/593, 329/329, 166/166, 152/152, s81sl_vn 2999/2999).

## ECO (pg_bind_eco.tcl, this directory)

On a copy of each CLOSED final ODB (input mounted read-only): for each instance whose master PG MTerm has no net, look up the expected
net from the block's own stored global-connect rules (`ot_pg_prepare`, physical/common_flow/native_pg_binding.tcl from main),
clear the instance's dont_touch, `connect` the ITerm, restore the flag. Nothing else changes. Proofs in each `run.log`:

- pre/post signal fingerprint (every non-PG net: ITerm list + routed wire length; every instance: master, location, orient,
  placement status, dont_touch) is byte-identical (`SIGNAL_IDENTICAL`, same sha256). Timing, SPEF, LEF and Liberty views are
  therefore unchanged: the CLOSED TT/FF numbers and the native pin audits stand.
- post `ot_pg_audit_snapshot` (all master POWER/GROUND terminals, master-driven census): PASS, 0 failures.
- `check_power_grid -net VDD` and `-net VSS` (PSM): all shapes connected, PASS.
- output `6_final_pgbound.odb` next to the input, in `<route root>/pg_bind_eco_native/` (sha256 in run.log).

| view | source | unbound bound | dont_touch | terminals checked | post audit | grid VDD/VSS | signal |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| CAPC s81sl_capc_p1_die_slew | 267b35821 | 3732 | 1866 inst | 480,752 | PASS | PASS/PASS | identical |
| cap_rt | c302169ce | 1186 | 593 | 382,286 | PASS | PASS/PASS | identical |
| cap_tr | 0ecc0c258 | 658 | 329 | 151,204 | PASS | PASS/PASS | identical |
| dsdv_mu_hslot | adb53b6fe | 332 | 166 | 215,246 | PASS | PASS/PASS | identical |
| dsdv_mu_land | 263e13fc3 | 304 | 152 | 546,800 | PASS | PASS/PASS | identical |
| s81sl_vn (INF.13, not in the earlier census) | b384d72cb | 5998 | 2999 | 1,830,160 | PASS | PASS/PASS | identical |

Counts equal the earlier read-only census exactly. s81sl_vn (CLOSED b384d72cb) had the same defect (5998 terminals); every S81 view routed by this flow in default PG mode must be assumed to have it until audited. Fleet: unpinned `ot-run --mem 16 --threads 1 --dir <route root>` (data-local),
units in each `ot_run.log`.

## Flow fix for every future route (not applied here; ROOT merger owns common_flow)

The strict-mode hooks already bind before protecting (`ot_pg_bind_before_protect` at every protection site). Either set
`"pg_strict": true` in each S81 kit at its next regen, or make the default branch of those protection sites call the same binder
(or `global_connect`) before `setDoNotTouch`. The final strict guard then refuses any instance that still escapes.
