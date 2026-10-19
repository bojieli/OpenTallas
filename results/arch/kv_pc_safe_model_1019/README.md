# PC / PC_H structural source model

**MODEL HOLD: a real boot-return fault is dropped.** In the exact old prototype source, `land_er[0/259/260] -> ler_v/cr/f -> bfault -> u_chain.fault` is functional fault logic, but the tile leaves `w_pc__chain_fault` unexported. Native synthesis consequently removes that fault cone and all 261 `pc__land_er` inputs. Those inputs cannot receive a source-spare waiver. The selected GEN7's distinct unified-305-bit wrapper also leaves this same chain fault unexported; its separate exact-source trace and proposed same-domain registered integration are in `FAULT_MODEL.md`. Fixing storage alone cannot close PC.

This step finishes uniform classification of the retained synth-native graph and proposes a bounded SRAM architecture. It does not qualify a successor or authorize RTL, synthesis, CTS, routing or submission. The original PC WARN / PC_H FAIL packet `1248d0585` remains unchanged. Earlier incomplete audit records `d03233299` / `2dfe7accc` remain historical evidence.

The inputs are the already completed read-only metadata pickup at `/home/ubuntu/artifacts/kv-pc-contract-1019/{pc,pc_h}` and terminal gate metadata at `/home/ubuntu/artifacts/kv-pc-terminal-1019/{pc,pc_h}`. No extraction or EDA run was repeated. Input hashes are in each summary; the old immutable ODB identity is retained by the pickup summary and terminal manifest. Reproduce the light metadata audit with:

```
python3 tools/qwen_kv_die/pc_safe_model.py \
  --pickup /home/ubuntu/artifacts/kv-pc-contract-1019 \
  --terminal /home/ubuntu/artifacts/kv-pc-terminal-1019 \
  --out results/arch/kv_pc_safe_model_1019
```

The script independently reconstructs BUF/INV-transparent components from every retained native master pin and its direction, including output BTerms. It compares complete endpoint sets and every driver count against the original records. All native FF are exactly `DFFHQNx1_ASAP7_75t_R` or `DFFASRHQNx1_ASAP7_75t_R`; there are no other sequential/macro masters, connected INOUT pins, unknown source components, or multiply driven components. Transparent intermediate outputs remain in the original records but are counted once through their semantic source for the repair cost. Clock-only exemptions require that **every actual endpoint** is a native FF `CLK`; no exemption is inferred from signal names. Reset endpoints are included wherever they occur, including mixed data/reset FF roots and the physical constants.

| Complete native source-root fact | PC | PC_H |
|---|---:|---:|
| Cells | 181331 | 180521 |
| Native FF | 39989 | 39690 |
| FF roots above 32 / maximum pins | 188 / 2405 | 184 / 2405 |
| Genuine combinational roots above 32 / maximum | 324 / 2023 | 323 / 2023 |
| Constant roots above 32 / maximum | 1 / 4024 | 1 / 4023 |
| All nonclock violating roots | **513** | **508** |
| Clock-only source roots | 10 | 10 |
| Top data/reset input maximum | 3 | 3 |
| Extra FF copies lower bound at **32** loads | 1532 | 1523 |
| Extra combinational copies lower bound at **32** | 1754 | 1743 |
| Extra physical constant instances lower bound at **32** | 125 | 125 |

These split counts are sums of `ceil(loads/32)-1` on frozen source roots. They are **not** a complete repair fixed point: duplicated D/enable/reset cones increase upstream loads; reset polarity, hold feedback and useful Boolean dependencies must remain exact. Macro migration also changes the graph. The optional 24-load robustness row is retained separately in JSON, not substituted for the acceptance rule. Enabled or unreset clones may not assume matching initial state; first-use convergence/reset ancestry needs a real source proof. No BUF/INV or alias copy closes a logical fanout failure.

Native FF totals differ from the old mapped-textbook totals 41933 / 41634. These are distinct recorded analysis stages; the missing 1944 instances have not been reconciled, so neither count is silently relabeled. Known master-area subtotals are 24543.88452 / 24458.44572 um², with one TIELO master geometry absent from the earlier geometry dump. FF split lower-bound area is 569.99052 / 566.84124 um². None is a full successor-area claim.

The fixed-face audit uses actual BTerm rectangles from the original native geometry dump and strict direct data-FF ownership through BUF/INV only. PC has 4374 direct data boundary bits / 3575 distinct FF; PC_H has 3295 / 3276. **805 / 25 data FF are shared by multiple physical faces.** Clock/reset input owners are excluded from this data ownership count. The complete identities and faces are retained. A single FF serving opposite faces is not a pair of face registers; source-equivalent same-edge output copies must be allocated and their upstream load charged, without adding a boundary age. These copy counts overlap fanout repair and must not simply be added to it.

Both variants also have ten active inputs with combinational logic before the first FF (`pc__ki` nine bits, `pc__fi` one), 261 native-unused `pc__land_er` inputs, and two native-constant outputs `pc__land_es[287:286]`. The latter originate in the source assignment `if(bh) land_es[287:1] <= {1'b1,1'b1,address29,data256}`, with otherwise-held unreset payload. Their legitimate constant-field/registered-pin/invalid-first-use contract remains **unapproved**, even though native optimization ties them high. The dropped functional fault above prevents treating the dead-input family as generic spare pins. There is no complete actual placed stage-reach certificate yet. The old estimated reach and outline alone do not prove every source-to-pin path is <=405 um.

## Exact front storage and consumer lifetime

An important source correction is now pinned: the actual front and return are `qkd_kv_hbm_elastic_front_mc_nc` and `qkd_static_kv_return_slots_mc_nc`, embedded in `rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv`. Both exact frozen manifests bind blob `381ac5e3a7fdf355c295d8c3eaec30c474311d86`, SHA256 `16ac2306ab9b5e707c276042080c03225ab04773f43169d376905c05b0508f0f`. The older standalone `*_mc` files describe similar behavior but are not the actual instantiated source identity.

The declared front is 32x297 = 9504 bits, width-banked 75/75/75/72 across four independently delivered write clocks. Native storage is 32x288 = 9216 FF. The exact consumer ledger explains all 288 removed bits: `front_co` has only its front output and return input connection; the return's `hd` packs `co[281:26]`, `[17:12]`, `[11:9]`, `[7:1]` plus all epoch bits. Thus `co[8]` and `[25:18]` are unused downstream. They map exactly to omitted bank-0 positions 7 and 17..24 in all 32 native words; every other bank bit is retained. The script binds these equations, exclusive parent connection, native bit identities and source hash. This explains the old count without introducing any new pruning or changing generic defaults.

Despite sixteen declared kept pointer copies, the front's four asynchronous bank reads use copies 0/4/8/12. Native pointer Q0 reaches 2405 loads. At the consuming edge, `out_q` captures the current asynchronous word when `take`; the static first-put contract is three edges after the captured `blk_go` pin, including back-to-back last-take/start. `pending + go_q - start`, write/take pointer updates, saturated stall counting, occupancy, hold, overflow/go faults, arbitrary storage initialization, output hold, and reset priority remain part of equivalence.

## Bounded SRAM candidate, requiring ROOT review

The first candidate keeps all four source write-clock domains and uses **eight `ot_sram_1r1w2c_32x64_m1`** banks, two per 75/75/75/72-bit slice. Source primitive `e26d92503`; exact diagnostic coupon `3ff02bde1`, contact audit `3e95aae81`, auto-main `944bbb859`. Each macro is 31.992x17.304 um, 553.589568 um², with two clock contacts and 103 W/E contacts per face (5.95238/um). Eight macros cost **4428.716544 um² / 16384 physical bits / 16 macro clock contacts**, compared with 9504 declared useful storage bits (6880 packing waste). Logical source demand is at most one 297-bit word per HBM edge in each direction, including 256 payload bits. Macro nominal bandwidth is sufficient; producer throughput is not qualified by that arithmetic.

The prior single synchronous coupon proves its actual 250 contact/PG/OBS/via escape and DRC0, TT+422.52 ps / FF+17.87 ps. It **does not** prove this eight-bank placement, independent write-clock phases, FIFO lifetime, arbitrary read/write collision behavior, parent clock matching or rate. New macros stay on the 43.2-um lattice, with real W/E pin-face channels, connected PG contacts, legal OBS/vias and a full standard-cell band. No eight-bank floorplan or whole-PC slot is claimed here.

A candidate pre-read requests `(rp + take) mod 32` before each reader edge, so the synchronous macro word could be available for the *existing* next `out_q` capture. This is a candidate equation, **not a zero-cycle proof**. A physical same-address read must be disabled when its result is undefined, with exact current/previous-write forwarding; planning reserve is 297 payload FF plus 48 address/valid FF, before reset/control fanout and native timing. Actual clock-phase ordering, initialization, first-use, full-block readiness, wrap, overflow, and simultaneous last-take/start must establish that the selected word is identical on every qualified edge. If that fails, the added read edge must be explicit in the compiler/die/SU/MU calendar; `successor_latency_edges` remains null.

Whole-source storage is broader than the front. Retained native graph also includes the return payload 2304 bits (48 pointer FF are separate), control-down FIFO 2304 bits and control-up FIFO 2064 bits. Preliminary width packing suggests another 8+5+5 macros, but their exact reset/CDC/collision/read-age contracts and complete indexed-storage inventory are not closed. A front-only repair cannot qualify PC. Full macro area, local control/reset copies, clock-tree load, legal parent slot, placement reach, actual TT setup/FF hold/native matching, and token throughput/cycle delta remain null until the complete model converges.

The next authorized step is ROOT review of this finite model and selection of the smallest actual-source lifetime/clock proof. Keep original routes and their failures; no gate retry, source SAFE parameter or new submission is authorized by this packet.
