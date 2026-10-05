# HBM-accelerator 1.2 GHz closure: DS attention tile and engine (family attn, 2026-10-05)

Status: the RTL is final, exact and cycle-measured. Its routes are running and have been handed to Codex
(`attn_CODEX_HANDOFF.md`). No block is `closes_signoff` yet. Per-block detail is in `closure.json`.

## Design (new files only, default off; as-built and `_l` files byte-identical)
- `rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv` is the engine: the REPL2 controller plus FPL/FML/NBANKP and the options
  NARROW, MFAN, TRX, F12/FPLX and TILE_S.
- `ot_hdc_v41x_attn_tile_s.sv` is the head-group tile. Exact companions are `bmul_s`, `deq_a`/`deq_b`, `chunk_s` and `qaddf`.
- `ot_hdc_v41x_kreg.sv` holds the kept-hierarchy copy register.
- `ot_hdc_v41x_attn_tile_s_phys.sv` holds the hardening wrappers.
- `rtl/chip/physical/ot_v41_attn_eng_s_ctl_phys.sv` is the controller vehicle.
- The FP32 adds are the SU agent's f12 units: `rtl/hdc/ot_hdc_fp32_f12.sv`, LAT4 in the tile, LAT5x in the lane trees and merges.

## Cycles (full shape H16 D512 TD32 NL4; one job; 1.2 GHz)
| config | T=128 | T=640 |
|---|---|---|
| cited baseline ILV0 PW1 FPL3 (does not close) | 225 | 609 |
| closing, same controller config (ILV0 PW1, F12) | 268 | 652 |
| as-built ILV1 REPL2 NS2 PW2 FPL3 | 197 | 453 |
| closing physical controller (ILV1 REPL2 NS2 PW2, F12) | 240 | 496 |

- Each attention job gains +43 cycles: tile passes +24, lane tree +8, merge +10, MFAN +1.
- MTP verify at P=6 (L0 0/188/218) also gains +43 per layer, only in the pipeline fill:
  - T=640: 2196 / 2423 / 2603.
  - T=128: 652 / 1527 / 1707.
- Per token there are 2 T=128 and 38 T=640 attends:
  - Same controller config: +1,720 cycles = +1.433 µs.
  - Closing physical controller vs the cited 225/609: −4,264 cycles = −3.553 µs. This assumes the PW2 p-supply,
    which is unvalidated on the HBM SU.
- Scaling rule: full shape = D64 full-schedule vehicle + FX × 3, where FX is the lane-tree add latency. It was
  checked at FX 3 on both controllers: 216/600 → 225/609 cited, and 188/444 → 197/453 measured at full geometry.

## Exactness
- tile_s vs tile_l lockstep, every output on every cycle, 0 mismatches: `lockstep/`. Cases: H16 TD32 NB5 PW2 F12;
  H4 PW1 F12; FPL7 variants.
- Engine equivalence vs as-built on the campaign benches is bit-exact against the golden on the small and dpt8 shapes,
  for ILV0 PW1, ILV0 PW2 and ILV1 REPL2 NS2 PW2. The only cycle delta is last_pv +1 (MFAN): `gates/equiv_*`.
- The 1M job shapes are bit-exact: `gates/sched_final.json`. MTP verify P=6 at T=640/128 and 3 L0 values is
  bit-exact: `gates/verify6_final.json`.

## Index path
index_q, index_scores and topk_local are model-priced in the baseline. No HBM-accelerator RTL instantiates
`ot_hdc_v41x_idx_*`, so they are not closed here. Their status is in `closure.json`.

## Replay (remote hosts; Verilator 5.050; declare memory honestly, about 100 GB for the FPL>3 vehicle builds)
    python3 tools/hbm_fmax_attn_gate.py equiv --only small --param NARROW=1 --param MFAN=1 --param TRX=1 --work W --out R
    OT_ATTN_VL_CFLAGS=-O0 python3 tools/hbm_fmax_attn_gate.py sched --hier --param NARROW=1 --param MFAN=1 --param TRX=1 \
        --param F12=1 --param FPLX=5 --lat 4,6 --banks 0 --work W --out R
    OT_ATTN_VL_CFLAGS=-O0 python3 tools/hbm_fmax_attn_gate.py verify6 --hier --no-as-built (same params) --work W --out R
    lockstep/run_v2.sh <tag> -GH=16 -GTD=32 -GNBANK=5 -GBW=3 -GPWORDS=2 -GHG=4 -GFPL=4 -GF12=1 -GNCYC=20000
    full-geometry FPL3 build: tools/hbm_fmax_attn_full.py --pwords 2 --param ILV=1 --param REPL=2 --param NSTAGE=2
Routes: see attn_CODEX_HANDOFF.md. Afterwards, run tools/hbm_fmax_attn_abstract.py for the tile parent.
