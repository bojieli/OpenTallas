# Qwen3-8B TP8 split: KV/system die contract v1 (2026-10-14)

**Owner decision.** 2026-10-14 06:45 PT: two dies per TP rank. This die holds:

- 4 HBM3E stacks with their controllers and CDC;
- the KV landings and posted KV write;
- near-HBM attention (Q in, results out; the KV history stays local);
- the merged sequencer (with its stage stepper);
- the embedding gateway;
- host and system services (host, host SerDes, PLL / reset);
- the KV end of the die link (`LINK.md`).

**Owner and log.** KV/system-die lead, `el1014-qwen-split-kvsys.log`.

**Generator.** `tools/qwen_kv_die/kv_die.py case --kv-wq-mirror --split` (branch `claude/qwen-split-kvsys-1014`). This
is the TP4 KV-die generator, which closed `die_kv15` (GRT overflow 0, TT +217 / FF +18 on assumed views), carried to
the split.

| File | Content |
|---|---|
| `kvsys_v1/contract_v1.json` | Every slot: outline, instances and orientation, pins per bus (face / layer / offset / bits / direction), clock entry, layer contract |
| `kvsys_v1/pins/INDEX.json` | Master list: status, port-bind class, count, outline |
| `kvsys_v1/pins/<master>.json` | Assigned pin file for every unclosed master. The die assigns these pins top-down; tile kits consume the file. |
| `kvsys_v1/port_bind_v1.json` | NO-STUBS port-bind audit (owner 08:05 PT) |
| `kvsys_v1/window_v1.json`, `window_kvbase_calibration.json` | 2-D window check |

## 1. Floorplan v1

- **Die:** 9.113 x 31.240 mm = **284.7 mm²**. Long axis N-S, within the 33-mm reticle axis.
- **Long edges (W and E):** four HBM3E PHYs, two per edge, 833 x 12,000 µm each. These edges are fully used by
  shoreline.
- **N short edge:** the UCIe x64 macro, abutting the compute die, at the centre column, x 4,168-4,946.
- **N end of the centre column:** UCIe macro, then `qkd_d2d` (the KV end, 777.6 x 518.4), then `qkd_lnk` (777.6 x
  129.6, abutted), then `qkd_seq` (604.8 x 475.2), then `qkd_embgw` (172.8 x 216). `qkd_pll` and the clock / reset
  bump `qkd_ckbump` sit beside the macro. The PLL forwards the clock and reset to the compute die.
- **Die centre:** `qkd_ahub`, 1,175.04 x 760.32, the hard-reciprocal hub kit.
- **S edge:** host SerDes PHY (2,400 x 1,512) and `qkd_host`.
- **Per stack:**
  - band (outward to inward): PHY | `qkd_ctrl` strip | 32 `qkd_cdc_wleaf` + 32 `qkd_kvwq_leaf` | `qkd_land`;
  - group: 4 row engines | `qkd_astk` | 4 row engines;
  - each engine is 4 heads + `qkd_ectl` stacked.
- **Stack pitch:** 14.25 mm. The head slot is the closed `ot_qwen_nearhbm_head_hs`, 734.4 x 855.36 (coordinator: the
  head gets a slot that fits its closed view), so the engine column is 3.55 mm. The S | N groups leave a 518-µm channel
  between them. All shifts are multiples of 43.2 µm, so hard-macro origin residues are kept.
- **Comparison:** Codex's translated candidate was 10.04 x 24.33 = 244.4 mm² with 712.8 x 453.6 heads. The difference
  is entirely the head size (+40 mm²).

## 2. Plan checks (v1, real-case legal with real views)

| Check | Result |
|---|---|
| Legality | 2,586 instances, 0 overlaps, 0 outside. Real case `OT_LEGAL`, `OT_ASSERT PASS`, `OT_PA DONE` with 394 real-view instances bound. |
| Real views bound | `qkd_rhead` = head_hs (128), `qkd_cdc_wleaf` (128), `qkd_kvwq_leaf_s_w129_m` (128), `qkd_kvwq_ctl_bin` (4), plus PHY macros. 76 % of block area is real; 52 placeholder instances (21.7 % of area). |
| Pin-to-pin reach (relayed point-to-point buses, <= 504 µm) | 2,522 hops, **0 violations**. 2,136 relays on 111 buses. |
| Stack-local reach (abutted classes the relay planner never relays) | **192 hops over 504 µm** (max 963 µm, 103 kb): `te` / `ts` / `tp` of the 64 far heads (h0 / h3). The 855-µm head puts the far head of each pair one head away from its control tile. |
| Orientation | The closed head_hs has **no legal MX or MY origin**. Its horizontal pins are on M4 and M6; its vertical pins on M3 and M5. v1 places all 128 heads R0, so heads 0 and 1 face the control tile with their output (N) face, and the col-1 heads' `nb` (E face) faces away from the aggregator. |
| 2-D windows (L-routes between drawn pins; abutted classes excluded) | Fine 260 µm: max **1.47 H / 1.27 V**, 160 windows > 0.60. Coarse 1,040 µm: 1.27 / 1.22. Calibration: the TP4 KV die (GRT overflow 0 measured) scores 0.93 / 0.89 fine, 0.69 coarse on the same metric. Hot windows: the col-1 engines' KV rows (`krs` 1,025 b x 2) and `kvn` rows crossing at the group edges (x 3.6-3.9 mm and 5.2-6.2 mm, y 16.4-17.9 and 29.4-30.7 mm). The 1.47 H is the `d2d_dn` / `d2d_up` abutment face (`qkd_d2d` <-> `qkd_lnk`), not die routing. |
| Pin alignment (`die_top_lint`) | FAIL 309 bundles (jog spills past the channel), WARN 3,207 |
| Relay stages on the link path | `lx` / `lr` (`qkd_lnk` <-> `qkd_seq`) 1 each: K_ST = 1. Sequencer -> stack `aq`: WS 36 / WN 7 / ES 36 / EN 7. Hub -> sequencer `ares` 32. |
| Long control relays | `hc` / `tk` (host <-> sequencer) 69, `kc` (stream commands to the S controllers) 74, `kvn` S stacks 57 |
| Reset | Reset nets are trees from `qkd_pll` `rso_*` (`rst_core_*`), as in `die_kv15`. The reset tree plan has not been re-run for the split. |
| Port bind (NO STUBS) | **REAL 6 masters / 387 instances**: `qkd_rhead` (head_hs), `qkd_cdc_wleaf`, `qkd_kvwq_leaf`, `qkd_d2d` (`ot_qkvd_kv_end`), `qkd_lnk` (`ot_qkvd_split_kvlink`), `qkd_seq` (cluster, HEADS 1 / Q_FP32 1). **MISMATCH 3:** `qkd_ectl` (die binds `ot_qwen_nearhbm_ectl_h`, which lacks `er_data` / `er_valid`; the closed ectl is the three leaves A / B / C); `qkd_ahub` (am x 4 = 144 die bits vs 36 RTL); `qkd_kvwq_ctl_bin` (f0..3: 1,172 die bits vs 1,192 RTL, 5 lane bits x 4 tied). **STUB 10 (16 instances):** `qkd_astk(_n)`, `qkd_land(_n)`, `qkd_ctrl(_n)` (strip frames whose real leaves exist but are not composed), `qkd_embgw`, `qkd_host`, `qkd_pll`, `qkd_ckbump`. **RELAY 20 masters (2,140):** generated lint-stub relay modules; a real relay RTL master is owed. **HARD_PHY 3:** behavioural analog allowed. Digital layer: HBM controller = `qkd_ctrl` -> STUB today; UCIe = `ot_qkvd_d2d` framing / credits REAL, but **CRC / retry / FEC are assumed inside the vendor macro: no RTL = a blocker under the 08:05 rule**; host SerDes link adapter in `qkd_host` -> STUB. |

## 3. Clocking

- One core domain at 1.2 GHz from `qkd_pll`, with per-stack trunks `clk_core_<st>` and a centre trunk.
- HBM hclk per stack, crossing in the CDC leaves.
- Every closed view carries `insertion.json`, and the die delivers each clock at phi - R. **head_hs has R = 993 ps TT**
  (boundary mean, spread 115). That is above 300, so these tiles take an early trunk tap and SKEW 150 on their hops.

## 4. Ordered element queue (v1; refreshed after each chain: see the top of the stream log)

The live queue is the top block of `el1014-qwen-split-kvsys.log`.


## v1.1 (2026-10-14 PM): the single published revision of the day (supersedes the v1 slots / pins)

Files: `kvsys_v1_1/` = `contract.json`, `pins/INDEX.json` + 16 assigned pin files, `plan.json`, `port_bind.json`,
`window.json`, `views.json`, `clocks.json`. Source `a5e4779f9`; prep `tools/qwen_kv_die/chain/kvsys_prep.sh`, export
`tools/qwen_kv_die/kvsys_contract.py`. Die chain `kvs2` (GRT + TT / FF STA, SS sensitivity) runs on exactly this case.

| Change | Why | Result |
|---|---|---|
| Head = native `ot_qkh_head_native` (wires-only parent of 16 lane8 + ktree + front + 16 stations + score) | Codex decision 09:04: head_hs failed the native audit (R 993, spread 115) | port bind REAL; **35 child clock entries** `ck_f/k/s`, `ck_t0..15`, `ck_l0..15` (each its own sink, phi - R_child) |
| Head slot 734.4 x 855.36 -> **1,080 x 492.48**, die-assigned mirror-legal pins (S face M5 in, E face M4 nb, W face M4 clocks) | v1: 192 far-head hops 505-963 um, no legal MX | heads below the control tile are MX again; every far head is 492.48 + 2 x 2.16 = **496.8 um** from its control tile with its bits x-aligned: stack-local reach **0 / 576** (max 498.5) with **no relay and no latency change** |
| ECTL = `qkd_ectl3_s` (A / B / C native TP8 leaves), centred in the column | v1 MISMATCH (bound `ot_qwen_nearhbm_ectl_h`) | REAL; **3 clock entries** `ck_a/b/c` at the leaf centres; t0 / t1 on M5 6-track pitch, bit-aligned with every head ti |
| Write controller = CLOSED sl3 slot `qkd_kvwq_ctl_bin` 172.8 x 129.6; write leaf = CLOSED sl1 slot (with insertion.json) | v1 MISMATCH (5 lane bits tied); old leaf view had no insertion | both REAL with measured R |
| `qkd_lnk` rf / tf bit-aligned with the KV end; lx / lr over the sequencer pins | v1 fine window 1.47 at the d2d / lnk face | gone from the hot list |
| Window check per bit (bits routed from their own pins; DFI from the real PHY offsets) | Codex 10:55: 3.78 was a bundle-centre artifact | fine 1.42 V (tp at the control tiles) / coarse 1.32 H (KV rows krs / kvn above the N groups) |
| Clocks: phi - R per CTS sink (`kvsys_clocks.py`, 6,772 sinks), owner budget (60 + 90 / 150 skew, hold 100) | kvs1 ran ideal clocks | measured R for the 3 bound views, frames ideal (R 0) until their views exist |
| PDN: hv5 macro grid (stacked M5 -> M8) | kvs1 PSM-0039 on all 128 cdc_wleaf | (chain kvs2) |

Die **10.496 x 24.587 mm = 258.1 mm2** (v1 284.7), 2,230 instances, 1,784 relays, pin reach 0 / 2,173.
Port bind: **REAL 8 masters / 423 instances**, MISMATCH 1 (`qkd_ahub` am 144 vs 36), STUB 10 / 16 (strip frames astk / land /
ctrl, embgw, host, pll, ckbump), RELAY 20 masters / 1,784 (real relay RTL with per-bit direction owed), HARD_PHY 3.
The link cost is unchanged (K_ST 1: `lx` / `lr` one relay each): +65 cycles / layer (LINK.md v1b).

Head team (reach rules in `pins/qkd_rhead.json`): inside the 1,080-um head every register hop must stay <= 500 um; the
native station (one leaf, D 2 co-located) cannot reach both a far-column lane and the E face: split its nb stage into
station D 1 + an nb relay leaf D 1 at the E side (latency unchanged), and keep every station within 500 um of the front.

### Die chain kvs2 on v1.1 (2026-10-14 13:00, `kvsys_v1_1/kvs2/`)

Real case legal (2,230 instances), PDN VDD + VSS PASS, full-die GRT overflow 0, STA with phi - R clocks (6,772 sinks):
TT setup WNS -431.3 ps, FF hold WNS -56.7 ps, SS -681.7 (sensitivity only). Real-to-real paths PASS (TT +170.5 / FF +124.2).
TT violators: the closed `qkd_cdc_wleaf` launch (native audit FAIL) into the landing frame over 450-620-um unbuffered
hops; KV-row relay hops detoured by GRT in one corridor above the N groups (kvn / emf / krs). FF violators: only paths with
an ASSUMED placeholder end (frames, relays) against the 100-ps H1 hold budget. Classified table and ranked queue:
`el1014-qwen-split-kvsys.log` (top); `kvs2/classes.json`, `kvs2/grt_<c>_paths.rpt`.
