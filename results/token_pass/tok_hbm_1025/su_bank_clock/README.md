# SU31 root cause: bank request relays use the serial clock

The 2026-10-25 02:25 su_mon run completed with 640/1046 failed checks. All four
SU tap lg_fault signals first rise at stream edge 5860. The first tap request
is at 5839, bank 0 rq0 at 5845 and bank rr0 at 5853. VM status remains clear.

SU pg_clk/taps and bank clocks are pll_stream. Their request relays and
request alignment pads incorrectly use pll_serial (3:4 rate). The transport
checker counted them as stream edges, so a nominal READ_RETURN=22 did not
represent the actual round trip. A return deadline can miss a valid even
though each slice's nominal lane counts agree. The fault is unrelated to the
constant SU grant calendar and does not justify weakening the fault check.

su_bank_clock.py traces valid bits through sliced and packed relay buses;
43 ordinary request relays/pads have the wrong clock/reset. A successor with
these bound to stream passes 32 request/return clock paths. transport_gate.py
now checks clocks, reads hierarchical-wrapper parameter defaults and follows
the correct valid bit of packed request/return buses. The original SU_BANK
FAIL was a checker gap; with those gaps fixed it passes the nominal parameter
check, while the new SU_BANK_CLOCK gate exposes the actual clock failure.

The minimum real tap + native q0 bank + SRAM vehicle passed 8 writes/8 reads
with exact returned payloads. A wrong-serial-clock mutant is caught by the
unchanged tap fault. This changes zero RTL arithmetic or pipeline stages;
it corrects the existing clock-domain bindings to match the modeled stream
edge counts. No release timing qualification is claimed.

Full SU31 successor replay is RUNNING on epyc2:
/srv/opentallas-scratch2/claude/codex-hbm-token-1025/full
Launcher epyc1 PID2036054, unit oth-ubuntu-3686175-1792921264.
The source/return calendars are unchanged. Existing HC_XRD, HC_XRU and
HC_LAUNCH failures remain and are retained in successor_transport_fail_hc.json.

Collected Qwen chain r0/r5: both finished, 1824/1824 checks fail on the prior
vehicle. That failure evidence remains in the original run directories.
