# FALLBACK-LAND 2026-10-26: what would a bottom-up landed-seam fallback cost? (ANALYSIS ONLY, all numbers UNCHECKED)

The fallback is per-partition clocks, with a LANDED crossing (forwarded clock, fixed latency, +K = 2 or 3 cycles) at
every partition seam. It has no FT routing (a lane that crosses N partition faces lands N times) and no island drivers.
No rule, plan, RTL, calendar or physical build changed. Every price below reuses an existing token tool unchanged, with
lane latencies raised by K per crossing. Seam inventory: Codex census codex/shared-core-0733@cb4bde4fc
results/fallback_land_0733.

| Die | Seams per token-critical layer (K-cycle crossings) | Added cycles/layer K=2 / K=3 | Landing area: ring basis (5.4 FF/bit) / gross 2-3 FF | tok/s vs current price |
|---|---|---|---|---|
| QC | ~388 per layer (36 layers) | +776 / +1,176 (FE-land variant +960 / +1,360) | 5.95 mm2 (0.73 %) / 0.97-1.45 | 4,051 -> 3,702 (-8.6 %) / 3,545 (-12.5 %); FE-land 3,628 / 3,477 (-10.4 / -14.2 %) |
| KV | 22-48 per attention request | +44..96 / +66..144 | 2.79 mm2 nominal, 2.00 occupied (0.93 / 0.67 %) / 0.45-0.68 | Qwen pair (QC+KV): -9.1..-9.6 % / -13.1..-13.8 % (FE-land upper bound -15.4 %) |
| S81 | ~450 face crossings per layer (214 with FT kept), 40 layers | AR +900 / +1,351 per layer | 5.23 mm2 (0.66 %) / 0.85-1.28 | AR 784.9 -> 766.8 (-2.3 %) / 758.1 (-3.4 %); MTP 2,749.3 -> 2,690.5 (-2.1 %) / 2,662.0 (-3.2 %) |
| HEAD | ~30-58 per lm_head pass (once a token) | +60..116 / +90..174 per token | 0.99-1.61 mm2 (0.3-0.5 %) / 0.16-0.24 | < 0.02 % AR, <~0.1 % MTP (graph estimate, not composed) |
| HBM (note) | 8-14 per S2 record (graph radius 7, diameter 14) | +16..42 per record | 2.72 mm2 (~0.3 %) / 0.44-0.67 | DS AR -5.7..-13.8 %, Qwen AR -1.3..-3.2 % (r25gq --op '*' --op-delta) |

## How each row was made

- **QC.** intel2:/srv/opentallas-scratch2/claude/fallback-land-1026/qc (07:18-07:19, copied to `qc_intel2/`). Every
  plan partition-boundary port on a v7 bind lane gets +K: 2,987 ports and 1,918 lanes. The plan is 54a1aeb5, not the
  current 40493490d candidate, which has 2,993 ports. Repricing uses the nativev7 composer (same harness as Codex's
  one-edge price: baseline 296,341, chained 8,131 per layer). k2: CB16 16->38, slice hops +58, L9 +14, slice-crossing
  law 796->1,372, die edges 1,209->1,969 per layer, 324,277 cycles per token. k3: 338,677. The FE-land case also lands
  the FE reach seams: 330,901 / 345,301. QC lanes already cross one partition per port (width x max(faces, ports) =
  1,277,486 = the census), so this is the no-FT form.
- **S81.** `tools/s81_dv/tokfunc/compose_tok_ds.py --lat` on main ac2ad01a8, with every lane of
  physical/die_plan/s81/lat/s81_latency.json raised by K x faces (no FT) or by K (FT kept). The baseline reproduces
  784.9 / 2,749.3. This is a LOWER BOUND: measured field records keep old embedded wires, and link_end is a bound
  that is not substituted.
- **KV.** `results/token_pass/toksched_1025/kv_v39r_price.py` with every lat_v39r lane delta = K x faces (or K). The
  low end is the priced bundles (36 requests + embed). The high end adds one serial pass of each interior family. The
  absolute rows are on the old qwen_rom DAG (4,810.9). For the pair, the per-layer delta is added to the QC composer
  result.
- **HEAD.** Estimated from the seam graph only, because compose_tok_ds carries the head die as a +34 tail: sp -> t
  ring 24-29 seams out, 4-29 back.
- **HBM.** `tools/throughput/accepted_cost.py compute r25gq --op '*' --op-delta {16,42}`, read as 8 seams x K2 and
  14 seams x K3 per record. The accepted B1 operation -> lane map is absent (OWNER? already logged), so this is an
  assumption, not a join.
- **Area.** The ring basis is the QC qc_cross summary: 6.79 M FF / 5.874 mm2 over 1.26 M bits, i.e. 4.66 um2/bit,
  DEPTH4+RDREG1 at ~5.4 FF/bit. It is applied to each die's nominal seam bits and is a logical bound, UNMAPPED. The
  gross columns are Codex's 2/3-FF envelopes. Neither includes per-partition CTS roots (QC 377, S81 398, HEAD 326,
  KV 160, HBM 88), forwarded-clock wires, epoch/reset control, or replanning area.

Not counted anywhere: handshake/epoch re-alignment of the static schedule, the calendar effects of KV interior
chains beyond one serial pass, and S81 field-internal seams.
