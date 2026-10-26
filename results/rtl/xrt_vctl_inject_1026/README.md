# Current selected XRT V-CTL injection component

Source cbff2e77a (current XRT SHA d09cf3f6fc8045f0078769604bee1abca6b4d0bd5cbd4b6dbf3debd9334e97d3), real ring-stop V pin -> ring-stop delivery -> XRT -> ring-stop E/W output.

HB0 and HB1 each PASS 192 transactions, 4,224 full-word checks, all 16 sid values, targets 0..5. Exactly seven registered edges, no ring-stop or XRT sticky fault. Payload and per-direction hops/source identity checked independently. Both six-edge timing-metadata mutants FAIL; the actual XRT HOPS RTL mutant FAILS. 7 xr_timing guard tests PASS.

Reproduce from repo root via `tools/s81_slice/xrt_vctl_inject.sh OUT` under ot-run. Actual run: epyc1 client PID1215565, localhost unit oth-ubuntu-1218729-1793005896, /srv/opentallas-scratch2/claude/xrt-qual-1026/run_fault, exit0.

This admits the source **model** for compilation. The separate HOST/control entry runtime proof remains mandatory in xr_timing.check_run_source; this component does not qualify a whole entry replay or token pass. No RTL, added-cycle or physical claim.
