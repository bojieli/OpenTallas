# QC PROG s8b archived native geometry review

Verdict: FAIL for current physical release. Independent review before requested PG-only repair STA.

Personally viewed auto_geom.png from the actual archived 6_final.odb (intel2 autopilot/closed/qwen_compute/qfd_dv_s8x_prog__s8b__6aa7f1fc4d/base). Four horizontal SRAMs stack vertically in a 259.2x354.24 outline. Their read flops hug W faces while p_q output flops hug E; the bottom pin/register bands carry write/read controls. PG-only reconnection does not fix the long cross-bank data/control paths. No cells overlap macros; signal pins registered. Historical routed DRC0 remains valid at its scope. Kernel channel/fill warnings are macro-dominated information, not a new gate.

Main geom_rules exact sequential reach census: 2,429 captures, 89 >405um, worst446.364um u_twpw/q (203.364,39.825) -> g_prog[1].g_r.u_lo_we/q (36.72,319.545). Other failures: pcap[512..597] upper-W source flops -> p_q lower-E captures (~428um); pp_idx[0..8]/pp_re lower-E -> top SRAM address/read controls. Full maximum pair per failing capture in long_r2r.json. Fix requires replanning/moving those existing register banks or a priced structural pipeline; no reset/timing waiver.

Pin->reg p90 32.74um, max42.47; pin_unreg0, cells_on_macros0. Clock entry distance499.35um is information only: actual leaf->own-driver max71.44um, so that AUTO-GEOM root-distance row is not claimed a new clock failure. No new route/STA was submitted. Original PG-invalid signoff retained and exact refs retired by existing RETIRED_SIGNOFFS mechanism.

Read-only geometry job intel2 codex-support-0822/prog-review, ot-run unit oth-ubuntu-2069132-1793287808, terminal exit1 from geometryFAIL; no physical edits.
