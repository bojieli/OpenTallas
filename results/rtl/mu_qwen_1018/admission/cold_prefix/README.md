# Cold context, row prefetch, and explicit INIT contract

This is a **BLOCKED model packet**, not a selected production startup epoch.
The single `manifest.json` binds the compiler and FACE/list-player inputs:

- Existing SEG2 and TXDP are decoded from the pinned source header and exactly
  recompiled before modification. The source header's old H/FIRST are not used.
- An explicit user0 kind12 context follows the real source AUTH/WITNESS replay
  interval. The WITNESS send is retimed when compute checked-RX latency changes;
  the original AUTH-to-WITNESS gap remains1057 edges. The context binds the
  public PW1024/DW8 dense-ledger digest, image epoch, capability, generation,
  token, position and user0 epoch. WIRE beat remains0.
- The row is prefetched **before** INIT. Actual provider core_start requires the
  whole row and scale already resident; merely postponing first L0 is insufficient.
- Source-frame paired head segments are emitted only in K_TX/C_RX for this cold
  fetch. All four full32-word calendar images include the new SEG2 and retain
  source-frame segment0/segment1 contents. Put them in a separate cyclic release;
  the old `ovl_release` files must stay pinned and unchanged.
- Cold T is MARK/INIT/END, appended at46 after the canonical45 per-token stage
  starts and END. Total49 fits64. Explicit INIT row47 is certified against its
  exact T word and the source PW range52/3. Cold END must not start the steady loop.
- E SEG0 contains steady events with head_ref61; E SEG1 contains cold prefetch
  events without that offset. Both tables total8 words, SEG1base4. The existing
  static cold mode selects E SEG1 at MARK. INIT stage0 does not restart E.
- `face_prefix_cfg_writes` exports actual T/E words and base writes. T is a
  **stage-control-only** source image: native CLOCK/LEVEL and ordinary host/result
  token-epoch closure remain owed. The L/Q production image is a separate binding.

The default model now prices measured SAFE3 C_RX calendar→emb_rx pin age3
(receipt7248f0679) and actual FACE/provider safe-consume age3
(receiptc11632a5b). Raw GI INIT→emb pin63 is measured0877475d8; LP input3 and
provider's following-edge sampling are recorded separately. Die SF/data/clock
lane ages remain unbound rather than being silently canceled.

Current nominal example uses K checked age2 **unqualified**. It derives:
AUTH checked95, initial context checked1192, prefetch reference1200, external
INIT1409, raw-GI INIT1412, emb pin1475, provider safe sample1476, external
L01743. These are common-link-reference model edges. They are not a physical
FIRST selection. `absolute_startup.FIRST_OFS` is null. K receipt, final die lanes,
consumer token/epoch identity, final calendar SRAM event proof and full programme
identity can change the startup numbers. The recurring period remains8053632.

The public example context is explicitly token777/position5/context epoch048c,
image epochbeef/generation2 and command-class programme identity. It is not a
production checkpoint token certificate. `production_bound` remains false.

Fleet validation, Verilator5.050 / Python unittest:

- Ten cold compiler checks: valid source plan, T49/E8 capacity and explicit INIT,
  wrong image context, omitted context, reordered context, omitted INIT, wrong
  PW range, wrong T selector, row not resident before consume, changed period.
- Actual mapped word-provider boundary witness rejects the proposed late fetch
  at core_start1064 before row completion1337. An early-prefetch control completes
  at974 before core_start1064 and reads all64 words exactly. Its input is the
  explicit checked-decoder boundary, not the full FACE/SAFE D2D chain.
- Five additional tests verify the separately opted-in SU landed price; no SU
  change is applied to this public frame.

Reproduce on fleet from the repository root:

    PYTHONPATH=tools python3 -m unittest \
      qwen_static_schedule.test_mu_cold_prefix \
      qwen_static_schedule.test_su_landed_price -v
    P=results/rtl/mu_qwen_1018/admission
    PYTHONPATH=tools python3 -m qwen_static_schedule.mu_cold_prefix \
      --admission "$P/F16_P2/admission.json" \
      --frame "$P/F16_P2/paired_frame.json.gz" \
      --source-ovl "$P/cold_prefix/source_ovl_release_img.svh" \
      --d2d-age-receipt "$P/cold_prefix/compute_d2d_age_receipt.json" \
      --provider-age-receipt "$P/cold_prefix/face_provider_age_receipt.json" \
      --token 777 --position 5 --context-epoch 0x48c --image-epoch 0xbeef \
      --generation 2 --out /absolute/fleet/work/cold_prefix

Run the actual provider witness with `run_mu_cold_provider.sh WORK` on fleet.
