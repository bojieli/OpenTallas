# HBM-RATE-DROP (10-19): why HBM-DS and HBM-Qwen fell 35 % and 57 % below the price of record

Lane HBM-RATE-DROP. Branch `claude/hbm-rate-drop-1019`. This is analysis only. **No price of record, record.json or
token_compose input was changed.**

Inputs:

- `results/arch/hbm_reprice_1019/reprice3b_{current,successor}.json` from LH-REPRICE3 (main, `tools/hgi_sim/d4g_reprice3b_1019.py`, which wraps
  `d4g_reprice3_1019.py`).
- The token composition from TOKEN-REC (`claude/token-rec-1019` f3e18d747): HBM-DS 1,233.4 tok/s against 1,905.4, and HBM-Qwen
  403.2 against 946.2.

Probes:

- `probe/`: read-only wrappers of the LH-REPRICE3 tool, run unchanged on the fleet bundle
  `ot-epyc6:/srv/opentallas-scratch/claude/lh-reprice3/src`.
- `probe/scenarios.json`: every scenario.
- `probe/records_only_hbm_bw_{ds,qwen}.json`: hbm_bw cycles per record class.
- `cur_asis` reproduces the committed numbers exactly (DS 1,206.3 / Qwen 407.0 with bank-latency budgets).

## 1. The drop term by term (current controller, 45.03 B/edge/SM)

Each term's cycles are its cycles alone on the 1905.4 / 946.2 basis (629,775 / 1,268,222 cycles at 1.2 GHz). The "share"
column is that term's part of the total drop: DS 343,145 cycles (629,775 to 972,920 composed); Qwen 1,707,969 cycles.

| unit / term | DS cycles | DS alone | share of DS drop | Qwen cycles | Qwen alone | verdict |
|---|---:|---:|---:|---:|---:|---|
| **HBM-BW controller** `hbm_bw` (45.03 vs 99 B/edge/SM) | 163,313 | -20.6 % | 47.6 % | 1,545,856 | -54.9 % | DS: **real**. Qwen: **real, but 54 % of it is a modelling error** (2x per-SM bytes; see 2a). Corrected Qwen 706,923 (-35.8 %). |
| Bank-latency budgets (x-load 65, COLL 84, DMA 93, IDX 181/75 incl. VM glue g4 +10; on top of `all`) | 97,960 | -9.85 % | 28.5 % | 21,920 | -0.7 % | **Real, but conservative**: fully-exposed upper bounds, not GEN2d measured depths. COLL 74 is measured (CODEX-COLL-SAFE E+84). Possible overlap with `collq` (2c). |
| Attention: `att_s32` 32,249 + `att_merge` 9,264 (DS); `att_qwen` 176,166 + merge 8,461 + `pvm_fold` 288 (Qwen) | 41,512 | -6.3 % | 12.1 % | 184,915 | -13.4 % | DS: **real** (measured S32 span). Qwen `att_qwen`: **double count x2** (two TP-4 KV-head records charged a full TP-8 head each; 2b). Corrected 48,042 (-3.65 %). |
| COLL: `collq` 19,159 + `e86_tkm` 576 | 19,735 | -3.0 % | 5.8 % | 2 | 0 | Real (measured gather-master span). |
| SM programme store / descriptors (C + C2 + P2): `att_prog` 0, `att_desc` 0, `sm_svc` 16,688 | 16,688 | -2.6 % | 4.9 % | 0 | 0 | Real but conservative: worst layer x 43, post-hoc fully exposed, so it can overlap the BW floor (2d). **Not a double count with SMB 1,661.8 / 844.4** (2d). |
| pg_stream / SU pgslice: `pg_cmd` 3,582, `pg_operand` 1,397, `pg_vmwrite` 6,108, `pg_inject` 597, `pg_reset` 4, `pg_fault` 0 | 11,688 | -1.9 % | 3.4 % | 9,978 | -0.8 % | Real. `pg_inject` is over-charged (every SU VM read, not only inject users). |
| GEN2e SU LG tap relays `gen2e_su` (+8 read / +8 write) | 9,160 | -1.4 % | 2.7 % | 7,808 | -0.6 % | Priced (planned profile, PRE-RELAY). **Possible overlap** with `pg_vmwrite` / `bank_pin` (2c). |
| Landing: `land` 7,198 + `hc_xr` 262 | 7,460 | -1.2 % | 2.2 % | 888 | -0.1 % | Real (priced factor). May partly overlap the relay depths inside the bank-latency budgets. |
| SAFE pin registers: `bank_pin` 2,141, `hc_tree` 1,053, `pt_p2`, `qcore_r6`, `su_red` | 3,194 | -0.5 % | 0.9 % | 2,885 | -0.2 % | Real, small. |
| IDX: `idx_link` 240 + `idx_pin` 224 (+ IDX budget inside the bank-latency row) | 464 | -0.1 % | 0.1 % | 0 | 0 | Real, small. |
| INT8 path `qwen_int8` | 0 | 0 | 0 | 0 | 0 | 0 (measured within price; SMB-INT8). |
| GQ issuer (+2 transport edges a GQ-local launch) | not priced | ~0 | - | - | - | Opt-in; below 0.1 % on any count. |
| Interaction (`all` minus the sum of single terms) | -6,200 | | -1.8 % | -94,415 | | Overlap of terms in the S2 schedule. |
| token_compose overlap (S2 COLL / non-COLL sharing) | -21,830 | | -6.4 % | +28,130 | | Composition, not a hardware term. |

### Grand totals

| | DS AR | Qwen AR |
|---|---:|---:|
| Price of record | 1,905.4 | 946.2 |
| `all` (every term) | 1,338.1 | 410.1 |
| + bank-latency budgets | 1,206.3 | 407.0 |
| Composed (TOKEN-REC) | **1,233.4 (-35.3 %)** | **403.2 (-57.4 %)** |
| **Corrected Qwen accounting** (2a + 2b), current controller | 1,206.3 (unchanged) | 582.4 with budgets; composed about 577 (**-39 %**) |
| Corrected, SAFE successor controller 90.67 + bridge +1 | 1,406.9 | 876.5; composed about 868 (**-8.2 %**) |

## 2. Modelling errors and double counts

### (a) Qwen hbm_bw counts twice the per-SM bytes (modelling error, 838,933 Qwen cycles)

The Qwen records are the **TP-4 programme** compiled for a 32-SM die. `ds_die_split._qwen_job` states: "16 SM: TP-8, rows
per SM unchanged". The base timing therefore streams `ceil(m/32)` rows per SM at bw/32 = 98.96 B/cycle/SM.

The REPRICE3 floor (`d4g_reprice3_1019.py`, `per_sm_bytes = n * ceil(m/16) * ESZ`) divides the TP-4 die's rows over 16 SMs.
That gives 118.25 MB per SM per token. The Qwen3-8B INT8 linear weights are 7.57 GB; TP-8 over 16 SMs gives **59.1 MB** of
codes per SM, which is the base's own `bytes32`.

The same floor also drops the fmt-3 transport factor of 1.25 that the base charges (160 B stride per 128 codes). That error
is in the other direction.

Correction (probe `FIX_SM` + `FIX_TR`): per-SM bytes = n x ceil(m/32) x ESZ x 1.25, which is 73.9 MB of physical HBM bytes.
Result: hbm_bw for Qwen goes from 1,545,856 to 706,923 cycles; Qwen alone goes from 426.4 to 607.6 tok/s. ATT records carry
the same /16 versus /32 error (`FIX_ATT`).

The DS records are not affected. The per-die SM bytes (FP4 88.3 MB, FP8 65.7 MB, BF16 57.7 MB) match TP-192 die shares
(the full model divided by 115 to 173). d4g W1 deals the die's m rows over 16 SMs, so /16 is right for DS.

### (b) Qwen att_qwen charges two KV heads per TP-8 die (double count, 128,124 Qwen cycles)

VEH-ATT3 measured 1,195 QK / 2,364 PV cycles for **one** KV head (P 8192, 512 rows/SM, 16 SMs). The TP-4 programme has 2
KV-head records per layer, and their base cost is serialised at die-wide bandwidth. `att_qwen` charges each record the full
one-head span over `nsm = 16`. That is two heads per layer, where a TP-8 die holds one.

Correction (`FIX_ATTQ`, nsm 32, so each TP-4 record is half a TP-8 head): att_qwen goes from -12.20 % to -3.65 %. The
VEH-ATT3 owner should confirm that the TP-8 die runs one KV head (4 query heads) per layer.

### (c) Possible overlaps (each below 1.5 %, to audit; not corrected here)

- `gen2e_su` (SU LG tap: bankface 1 + core 6/3 + own 4) against `pg_vmwrite` +12 (pgslice_lg drain write). Both are
  charged on SU records that write VM, and both sit in the LG region. Also, the gen2e "bankface 1" against `bank_pin` +1.
- `collq` (measured gather-master span) against the bank-latency COLL budget 84. This depends on whether the HBM-COLLQ
  bench span already included the VM bank round trip.
- `land` (landed half-cycle hops, a factor on tok/s) against the GEN2c relay-lane depths inside the bank-latency budgets.

### (d) SM programme memory: SMB re-price 1,661.8 / 844.4 against LH-REPRICE3

There is **no double count** in 1,233.4 / 403.2:

- The SMB re-price (`d4g_reprice_smb_1019.py`) was a separate run on the older REPRICE basis 3e3fd2aa0, and it is
  superseded.
- REPRICE3 carries the SMB terms once:
  - `att_prog` 0 and `att_desc` 0. These *removed* REPRICE's att_desc of -3.81 %.
  - `sm_svc` 16,688, and `qwen_int8` 0.
- LH-REPRICE3 wraps REPRICE3 without re-adding these terms.

The residual risk is `sm_svc`. It is added post hoc, outside the schedule, and is fully exposed (worst layer 388 x 43 + 4).
At 45 B/edge the SM records are stream-bound, so the 70-edge partial-wave service time would mostly hide under the stream.
This is up to 2.6 % DS of over-charge.

### (e) HBM-BW: did 95 B/edge replace 99 B/cycle/SM wrongly?

No. The units match: one SM clock edge at 1.2 GHz, per SM (4 PCs x 32 B x 0.9766 / 1.2 = 104.17 peak, and 98.96 = 95 %).
The composed record uses **45.03**: the current production master, row-per-block, measured (HBM-BW 9e8fcf77e). The other
numbers are not adopted:

- 95.19 is the controller-only DS figure with the expert layout triplicated. It is unqualified.
- 90.67 is the SAFE successor at its static 96 cadence. It passes production 66 ops / 154 GOs, but its physical closure is
  open.

The floor is an increment over the 99 reference: max(c, fa + B/45) - max(c, fa + B/99). It keeps compute hiding and does not
double count with the measured attention spans.

The only errors are 2a and 2b (Qwen accounting).

### (f) Open audit, DS base against the 99 B/SM floor (not a price; for the next re-price owner)

The DS native SM.MATVEC costs are op-shared walk prices, so records share the op's price. On FP4 expert records, the
per-record cost is below the record's own bytes at 99 B/edge/SM (implied rate up to about 235 B/edge/SM). The increment is
therefore taken against a 99 reference that the base never charged per record.

Charging the floor against the record's own cost instead (probe `FIX_REF`) is an upper bound, because it adds a first
access to every record of a flush group. Those bounds are:

- 1,573.8 DS at 99 (`ref99`).
- 1,094.9 at 45.03 with budgets (`ref45`).
- 1,276.3 at 90.67 (`ref90`).

So the modelled DS hbm_bw term is, if anything, a **lower** bound. It is not an over-charge.

## 3. Structural recovery for each real cost above 3 %

All options are timing or layout only: **no numerics change**. All keep the static schedule (no credits or backpressure).
All are safe-design checklist compatible.

| real cost | recovery (structural) | estimated gain | closure safety / status |
|---|---|---|---|
| HBM-BW controller (DS -20.6 %, Qwen corrected -35.8 %) | **Adopt the SAFE successor PC controller.** It has bank-parallel ACT lookahead, per-bank AQ summaries with a two-stage ACT select, refresh lookahead (no REFpb on the next block's banks), and response reservation sized to the round trip. | DS 1,206.3 to **1,406.9 (+16.6 %)**. Qwen corrected 582.4 to **876.5 (+50 %)**. At 90.67 the Qwen stream (815k) hides under SM issue (974k), so Qwen hbm_bw becomes 0. | Function PASS (66 ops / 154 exact GOs, 4 runs). Physical work is open: 5 non-reset fanout roots above 32 (cc723735d untested), CTS, actual-1024 clock certificate, and the macro pin coupon. Area +11.6 to 13.7 mm2 (die about 680 of 858). **This is the single biggest lever for both designs.** |
| (same, interim, no RTL) | **Qwen static weight image slot-packed** (8 blocks per row index) on the current controller: 58.8 B/edge measured. | Qwen corrected 582.4 to **720.1 (+24 %)**. | Compiler or image layout only. Qwen has no expert copies, so capacity is fine. DS cannot use it (the row-index bound needs the successor). |
| Bank-latency budgets (DS -9.85 %) | (1) Replace the fully-exposed budgets with GEN2d measured lane depths. (2) **Issue x-load / COLL VM reads one record early** into a double-buffered SM_X / COLL operand register. The static schedule knows every address, so the round trip overlaps the previous record. | About 60 to 80 % of x-load + COLL (43k + 44k single), so **DS +5 to 7 %**. | No shorter lanes and the same landed relays. Adds 1 operand buffer per client (SRAM if over 2 kb, checklist item 5) and is handed to the compiler schedule (item 8). |
| DS attention S32 span + merge (-6.3 %) | **Multi-block PV calendar**: a second p-store bank / per-block accumulators, so that p-load 128 + pv_node 160 + folds 40 + publish 64 overlap the next block's stream (only about 276 of each block op streams). Overlap the SU merge tree with the next head's QK. | About half, so **DS +3 %**. The same lever gives Qwen corrected att -3.65 % to about -1.5 % (**+2 %**). | SM tile is critical: gate PNGs go to COORD-REVIEW, no submit. HBM-ATTGAP / HBM-NEXT-ATT4 own it. |
| COLL collq (-3.0 %) | Below the threshold after rounding. Ring-A merge register overlap is possible later. | below 1 % | none |

### Estimated landing points (composed, ratio-scaled; these are estimates, not prices)

| | DS AR | vs 1,905.4 | Qwen AR | vs 946.2 |
|---|---:|---:|---:|---:|
| Today (TOKEN-REC) | 1,233.4 | -35 % | 403.2 | -57 % |
| Accounting corrected (2a + 2b) | 1,233.4 | -35 % | about 577 | -39 % |
| + Qwen slot-packed image (no RTL) | 1,233.4 | -35 % | about 713 | -25 % |
| + SAFE successor controller | about 1,440 | -24 % | about 868 | -8 % |
| + early-issue bank reads + PV calendar | about **1,570** | **-18 %** | about **885** | **-6.5 %** |

## 4. Recommendation for the owner

1. **The Qwen -57 % is mostly a modelling error, not hardware.**
   - The LH-REPRICE3 BW floor counts twice the per-SM bytes for the TP-4-shaped Qwen records.
   - att_qwen charges two KV heads per TP-8 die.
   - Corrected, Qwen on the current controller is about 577 tok/s (-39 %), and with the successor controller about
     868 (-8 %), which is inside the 15 % ledger.
   - A fresh re-price lane should apply fixes 2a / 2b in `d4g_reprice3b`. The tool change is in `probe/r3fix.py`
     (FIX_SM / FIX_TR / FIX_ATT / FIX_ATTQ). That lane then re-composes.
   - I did not change the price of record.
2. **The DS -35 % is real.**
   - The current PC controller keeps one open row per PC: 45 B/edge against the 99 the price assumed. That is -20.6 %.
   - Fully-exposed bank-latency budgets cost -9.9 %.
   - SAFE-path attention costs -6.3 %.
   - These are timing costs, with no numerics change, so the owner's 10-18 exception (HBM may exceed 15 % AR loss without
     a numerics change) covers them. They are still far below the accepted ~1,950 DS AR.
3. **Priority: close the SAFE successor PC controller physically.**
   - It is the single biggest lever: DS +16.6 %, Qwen +50 % (corrected).
   - Remaining work: the five fanout roots, CTS / actual-1024 clock certificate, and the macro pin coupon.
   - Then GEN2d measured bank-client depths with early-issue VM reads, then the multi-block PV calendar.
   - Expected landing is about DS 1,570 (-18 %) and Qwen 885 (-6.5 %).
4. **Decision for the owner.** Should the HBM release keep DS at about 1,570 (-18 % vs 1,905.4, -20 % vs 1,973.3) as an
   accepted timing-only exception? The alternative is to fund a further DS lever:
   - P=3 / more PCs per SM is already the next-release die.
   - A larger lever is to re-pack DS experts so that row-per-block disappears even on the current controller; this is
     capacity-bound today.
5. **Audit before the next re-price:**
   - DS base against the per-SM 99 floor (2f), where the modelled term may be a lower bound.
   - The overlaps in 2c.
   - sm_svc exposure under the BW floor (2d).
