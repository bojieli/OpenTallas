# HHP c708 guard -> KV boot / REOPEN calendar hook (TOK-ALL-17, 2026-10-27 17:58 PDT)

Emitter: tools/qwen_kv_die/hhp_boot_calendar.py. For all 128 PCs it builds the boot -> run -> re-load calendar in
gateway edges (qkd_embgw_boot_s HOLD 64 / GAP 1, asserted against kv_static_die.BOOT_GW) and checks it with
hhp_phase_guard.check at PHASE_DELAY 1 (c708) / 0 (main); exit 1 on any violation.
Hook: physical/die_plan/qwen_kvsys/cores/harden/kvspc_phase_delivery.apply_kit(..., calendar_report=) now FAILS CLOSED
(HHP_PHASE_CALENDAR_MISSING/BAD/FAIL/STALE) unless given an unmutated, admitted d=1 report made under the current
guard (sha256). transform() (bench path) unchanged. NOTE: codex/kv-cores-1351 gen_core_kit_kv.py --kvspc-phase-delivery
calls apply_kit(kd/'rtl') without a report: after this lands it must pass calendar_report (intended: no c708 kit without
an admitted calendar).
Ages: asbuilt_boot_bus_ages.json = extract of intel2:/srv/opentallas-scratch2/claude/codex-kv-image-1027b/prep_native2/
relay_stages_asbuilt.json (sha256 a38125fd..., source commit e33504a6f, Codex KV image lane 10-27): est trunk 13..77 +
group fork 0, bw->kvs_ctl 4, ctl->hroot WS 77 / WN 21 / ES 70 / EN 13, hroot->PC31 1..3, chain hop relays 0, est->host 5.
WORST corner, UNCHECKED element constants: EST_PINS 3 (max), BW_PIN 1, SLICE 0 (min), HOST_LAUNCH 0 (min), HOST_PIN 1.
Result (calendar_c708.json): ADMITTED 128/128. Min margins: W 7 edges (EN_11), S 72 (EN_11), E 92.
main d=0 (calendar_main_d0.json): ADMITTED, W 8 / S 73 / E 93.
Mutants (mutant_*.json): writer word at BOOT_END-2, slice at REOPEN+0, emb return issue+1: each FAILS 128/128.
Info: with HOLD 0 the S margin is still 8 at EN_11. S is carried by the boot-word path, which crosses the same
ctl->hroot trunk, not by HOLD. The gateway comment 'est trunk shorter than HOLD' is false as built (est 77 > 64), and
harmless.
Tests: tools/qwen_kv_die/test_hhp_boot_calendar.py: 6 PASS (real calendar d1+d0, 3 mutants, kit hook fail-closed
x4 + positive transform, committed report current).
Open: W margin 7 edges rests on HOST_LAUNCH_MIN 0 and EST_PINS 3 (not netlist-read). A measured est pin count /
HOST barrier->writer latency would make it CHECKED.
