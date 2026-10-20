# LEP LOCAL_WD (S81-LEPENH2, 2026-10-20) -- standard NATIVE32_STD lep / lep_nh

Source: claude/s81-lep-localwd-1020 @00d74ec20 = codex/s81-lep-native32-1020 @d1846d61e + 2 files (rtl/lib/ot_sram_showahead_1r1w.sv
opt-in LOCAL_WD, rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv `.LOCAL_WD(SAFE_STD)`; MU path unchanged). Run on ot-epyc6
/srv/opentallas-scratch/claude/s81lepwd with the Codex chain scripts (chain.sh) on the Codex source snapshot + overlay, preflight
tools = codex/s81-lep-physical-preflight-1020 @f37aae333 (preflight_src).

Why: the Codex row-constrained packing (../rowconstrained_1020, rc0 x4) left HOST 5 / NH 0 / MU_A 11 / MU_H 26 nets > 405 um;
41 of 42 were the RX SRAM wdata register (loads: prevdata, the q forward select AND the top-row macro wd_in). LOCAL_WD gives each
128-bit bank its own retained write-data register (same WREG edge, D = wd) driving only that macro's wd_in.

| check | HOST (ot_s81sl_lep) | NH (ot_s81sl_lep_nh) |
|---|---|---|
| Verilator 5.050 benches (bench_summary_v4.json) | lep s1, lep_host s3 PASS; mutants stdsel/vskew/swap/nopair/ksoff/hdrop FAIL (detected) | lep_nh s5, lep_nhr s7 PASS; nhacc FAIL (detected) |
| std phase bench (phase_summary_v4.json) | h1 PASS, stdsel / vskew FAIL (detected) | h0 PASS |
| native census actual Liberty (native_*_land5.json.gz) | PASS max 32, 42,543 roots, 0 violations | PASS max 32, 37,234 roots, 0 violations |
| row-constrained packing (host/, nh/) | 0 nets > 405 (max 404.98), 52,708 cells / 8,396 um2, band density 0.550, worst cut 0.377 | 0 > 405 (max 405.0), 46,312 cells / 7,670 um2, density 0.503, worst cut 0.354 |

Cost: +3,840 / +3,858 cells (~+7% std area, write-data copies); no added edge (same WREG edge). Not a layout qualification:
clock / PG-metal / all-cell ownership in a real kit and the 8-item PNG review remain (Codex STATUS.md); MU (MUBUF4) can set
LOCAL_WD for its path the same way.
