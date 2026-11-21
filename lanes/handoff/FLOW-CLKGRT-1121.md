# FLOW-CLKGRT-1121 handoff (Opus 5.5; flow-fix lane: clock nets keep near-CTS routes through congestion GRT). CURRENT 2026-11-21 17:xx PST

## Done
- main 6eeda31903: kit_wave.py private-spec --rt SHA (COORD ask): declared tools runtime rt/<sha12> for gen/kit_rtl/launch tree,
  recorded in spec private.rt + kit_env_provenance.json (tools_sha, rt_declared); env + ENV-PROVENANCE unchanged; stage flow
  refresh still from rt/current. Test: tools/autopilot/test_private_spec_env_provenance.py::test_private_rt_declared_and_recorded.

## Diagnosis (hroot D25d a5, copy of 4_cts_pre_tt.odb)
- 1796 clock nets (1191 leaf); NDR only on 148 non-leaf nets (CTS_NDR_0), none on leaf nets.
- OpenROAD GRT: set_routing_layers -clock acts on NON-leaf clock nets only; FastRoute has no fixed-net mode; critical-net
  priority is slack based (clock nets excluded); -resistance_aware orders clock nets first (3D phase only).
- a5 congestion reports: congested edges 2845 (it 5) -> 1245 (final); 81 clock nets still cross final overflow edges.
- Clock-only route of the same DB (3 min): clk_t9 branches 115/187/214 um (a5 congestion GRT 301/217/271), t18_regs 172 (388),
  t23 103 (353), t17 129 (294), fclk_hroot 55 (432). Overflow of the clock nets alone: 51.

## A/B running (epyc8 /srv/opentallas-scratch2/claude/flow-clkgrt-1121; harness h/arm.tcl, h/run_arm.sh, h/ff.tcl, h/summ.py)
- arms base / clkfirst (2 phase, no reservation) / resaware / nondr / hook (= tools/die_plan/grt_clock_first.tcl, reservation on)
- summary: cd <W> && python3 -I h/summ.py out base clkfirst resaware nondr hook
- logs intel2 ~/tmp/clkgrt_<arm>.out; units in those files.

## Prepared, NOT pushed (lane clone epyc10 <W>/repo): tools/die_plan/grt_clock_first.tcl + gen_phys grt_clock_first_cfg/install
  (gen env OT_GRT_CLOCK_FIRST=1) + test_grt_clock_first.py. Push only if the hook arm wins.

## Next
1. Read arm results; pick by clock spread/insertion + overflow + TT/FF.
2. Push winner opt-in (ot-push-main); prove on FABLE-FIX-KV-HUB-R2's b1 kit via private-spec --ab OT_GRT_CLOCK_FIRST=1 --rt <bind sha>.
