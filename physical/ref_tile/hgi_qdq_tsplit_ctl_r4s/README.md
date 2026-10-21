# hgi_qdq_tsplit_ctl_r4s -- ot_hgi_qdq_transport_ctl_r4 (HBM-QDQ8 2026-10-20)
Deep strap QUANT transport controller for hb_quant_NW split r3 (ot_hgi_qdq_host_split_r3). GEN2e4 r11 needs RL 54 at
hb_quant_NW (RLI = 58 + 2*XR); ctl_r3 accepts RLI <= 46. RLI 2..126 / WCI 2..63 straps; command ring A
ot_sram_1r1w_128x64_m1_p192, commit ring B ot_sram_1r1w_64x16_m1; 108 x 129.6 um; clock spine.
Bench: tools/hgi_unit_tput/run_qdq_host_split_r3_lockstep.sh (ring SRAMs + pointer random at power-up): split r3 == monolith
at L 7 / 54, XR 0 / 12; mutants m2 (unpriced relay) / m3 (ring read late) LOCKSTEP_FAIL; d: ctl_r3 refuses L 54.
## Safe-design checklist (gate 3 @6b7a3b1ee)
1 Pins: PASS -- every cmd/strap pin captured in one flop (+8 kept bank-base copies), outputs registered; reset 2-flop face landing.
2 Reach: PASS -- reach 1.9 um max stage (textbook).
3 Fanout: PASS -- native census max 27 loads (limit 32); gate 1 tap fanouts (167-220) removed structurally (no strap taps).
4 Depth: PASS -- 281.7 ps max depth; no comb in->out.
5 Storage: PASS -- command (48 b x 128) and commit (2 b x 64) delay lines in SRAM rings, flops only DL=26 decode pipe.
6 Floorplan: PASS -- 2 macros, >= 20 um from every (all-pin) face, 20 um channel; util 4 % std (pin-limited, 588 pins, as ctl_r3 11 %); aspect 1.2.
7 Clock: PASS -- spine, 991 sinks, TT/FF insertion 264.4/210.5, pin-flop spread 29.6/23.3 ps; io_hold_margin 0.025 (spec, as ctl_r3).
8 Schedule: PASS -- static; same edges as ctl_r3 (rq +3+XR, wq/done +9+3XR vs monolith); no ready/credit.
Trial GRT overflow 0 (M2 5.2 %). Gate PNGs gate_layout/{floorplan,density}.png inspected (cell cluster below ring A toward the S wq face).
Fallback kit hgi_qdq_tsplit_ctl_r4 (TritonCTS) FAILED gate 2 spread 87.2/83.1 -> not submitted.
