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

KV checked age3 is now source-bound to actual release353123a8d WITNESS
receipt3de5bd37c. The current nominal example derives:
AUTH checked95, initial context checked1193, prefetch reference1201, external
INIT1410, raw-GI INIT1413, emb pin1476, provider safe sample1477, external
L01744. These are common-link-reference model edges. They are not a physical
FIRST selection. `absolute_startup.FIRST_OFS` is null. Final die lanes,
consumer token/epoch identity, final calendar SRAM event proof and full programme
identity can change the startup numbers. The recurring period remains8053632.

The public example context is explicitly token777/position5/context epoch048c,
image epochbeef/generation2 and command-class programme identity. It is not a
production checkpoint token certificate. `production_bound` remains false.

Fleet validation, Verilator5.050 / Python unittest:

- Eleven cold compiler checks: valid source plan, T49/E8 capacity and explicit INIT,
  wrong image context, omitted context, reordered context, omitted INIT, wrong
  PW range, wrong T selector, source-specific INIT age, row not resident before consume,
  changed period.
- Actual mapped word-provider boundary witness rejects the proposed late fetch
  at core_start1064 before row completion1337. An early-prefetch control completes
  at974 before core_start1064 and reads all64 words exactly. Its input is the
  explicit checked-decoder boundary, not the full FACE/SAFE D2D chain.
- Five relative-list tests verify literal WRAP_BASE recurrence, halt replay,
  long-gap prefetch spacing, actual-frame capacity and missing/early launch
  rejection. Declared diagnostic phases fit3261 C_TX/K_RX and3262 C_RX/K_TX
  words (AW12). These are not production phase witnesses.
- Five additional tests verify the separately opted-in SU landed price; no SU
  change is applied to this public frame.

Reproduce on fleet from the repository root:

    PYTHONPATH=tools python3 -m unittest \
      qwen_static_schedule.test_mu_cold_prefix \
      qwen_static_schedule.test_mu_cold_lists \
      qwen_static_schedule.test_su_landed_price -v
    P=results/rtl/mu_qwen_1018/admission
    PYTHONPATH=tools python3 -m qwen_static_schedule.mu_cold_prefix \
      --admission "$P/F16_P2/admission.json" \
      --frame "$P/F16_P2/paired_frame.json.gz" \
      --source-ovl "$P/cold_prefix/source_ovl_release_img.svh" \
      --d2d-age-receipt "$P/cold_prefix/compute_d2d_age_receipt.json" \
      --kv-age-receipt "$P/cold_prefix/kv_witness_age_receipt.json" \
      --provider-age-receipt "$P/cold_prefix/face_provider_age_receipt.json" \
      --token 777 --position 5 --context-epoch 0x48c --image-epoch 0xbeef \
      --generation 2 --out /absolute/fleet/work/cold_prefix

Run the actual provider witness with `run_mu_cold_provider.sh WORK` on fleet.

The relative list encoder `mu_cold_lists.compile_bound` requires a complete
source launch ledger, including admission-to-go guard and every calendar's
reference-to-core-start age. It refuses missing ages instead of choosing FIRST.
The current nominal edge example is deliberately rejected under the older
+4 launch model: its earliest prefix would need go before admission completes.
The enabled FACE/list/SRAM launch measurement must retime that prologue. T/E
word contents remain unchanged by a global prologue shift.

The source packet's cap0 now appears explicitly as
`image_identity.capability_guard_satisfied=false`. Actual fusedcap1 programme
emission is required for the full FACE cold guard. Capacity/fault fixtures must
not be relabeled as a real programme or given a fabricated footer.

Publication and sampling are separate boundaries. The GI receipt measures an
input sampling edge to settled emb_start publication (+63); the provider samples
that registered output on its next edge. The enabled FACE selector owner now
measures T-start sample C→Ecal-start sample C+3, INIT publication C+212 versus
consumer pin sample C+213, and E FILL publication E-start+209 versus consumer
sample+210 (header+210/+211). Those enabled-component measurements do not bind
the missing die/LP clock phase. Final source receipts must preserve that
convention rather than merging publication and downstream sampling silently.
