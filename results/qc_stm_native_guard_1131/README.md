# Native whole-STM boundary checks

The exact mapped PRE-D13 `slw_stm_v3` parent counted in `../qc_stm_native_count_1131` passes both standard native boundary checks:

- PORT_BIND: 17,874 netlist bits = 17,874 declared bits, zero missing/extra bits or bad straps.
- FACE_GUARD: 17,698 checked bits, 17,698 OK, no failure classes.

The mapped source is unchanged. No generic boundary registers, profile changes, cycle changes, reset changes or guard exceptions were added. Standard clock/strap/landing classification explains the distinct checked populations. This receipt makes no placement, timing or signoff claim; the existing physical outline separately has only 3.99% standard-cell fill of free core area and remains held.

The previous synthesis-only generation omitted `--clock-landing`. Its missing landing metadata must not be interpreted as a native source failure. The private guard directory was copied from the actual generated kit, then `land_slots.json` was produced by the standard current `gen_phys.kit_rtl_land_slots` API using `clock_landings.Landings` on the exact frozen d90 plan and matching `results/qc_die57_1031/bind/sidecar.json`. That API verifies every declared depth/ring/origin against the actual 13-source bound RTL closure. Result: 12 hold_mux buses, 12 ring_start buses, one origin_start bus. No metadata exception was invented.

Tool snapshot: `443d6117a`. Runtime: `intel2:/srv/opentallas-scratch2/claude/codex-qc-stm-count-1131/guard_native`. Both tools consumed the unchanged actual `phys/slw_stm_v3/run/results/asap7/dp_slw_stm_v3/base/1_2_yosys.v`. Standard commands were `port_bind_gate.py NETLIST guard_native` and `face_guard.py NETLIST --pins guard_native/pins.json --out guard_native/face_guard.json`. Full `--clock-landing` generation from this tool snapshot separately failed before producing a physical kit because its unused whole-die reset generation resolved unrelated east-STM sink-bin files against the tool snapshot; that failure is preserved in `gen_land.log` in the live runtime. It does not replace or waive either native check.
