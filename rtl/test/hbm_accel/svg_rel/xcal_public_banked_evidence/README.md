# Opt-in public banked XC functional composition

The new `ot_hbm_svc_sm_xcal_rel_banked` and `_rel_t_banked` compose the production-width two-bank calendar and semantic XC app with the historical descriptor and target collar. Only the two new wrapper files are added; both canonical public wrapper files remain byte-identical to base `f1a223a78`. This is a functional composition. Host/descriptor/collar physical qualification is OPEN; no gate, timing, placement, fanout, reset, or full-tile SAFE claim follows from this receipt.

The model commits `583e28c64` and `4196c9628` precede RTL `6daf49dbe`. The app dependency is official `af72bbedb..a1e52e87c`; its final semantic DUT remains `2210ef72c`. Our imported dependency commits are byte-identical cherry-picks. The final wrapper RTL is still `6daf49dbe`, including during the historical failing active-status test. Bench/model-only commits qualify the intentional status correction instead of changing the source to reproduce the old false-idle gap.

## Integration mapping and latency

Both wrappers expose `clk_core`, `clk_bank0`, `clk_bank1`, and `rst_n`; all other host inputs and existing outputs retain canonical names/widths. `_t_banked` additionally exposes `command_envelope[174:0]`, `command_class_observe`, and `command_context_valid_observe`. The envelope is `{valid,class,kv_desc[63:0],cmd_ext[108:0]}`. Its aliases describe the actual public command/KV pins, including under diagnostic mutations. Default `CLASS_ENABLE=0`, `CLASS_MUT=0`, `MIRROR_MUT=0`; default PREL1 and production PAW11/DD256. Existing MUT1..5 remain opt-in diagnostics.

Each calendar bank is an actual `ot_smh_calendar_bank_leaf` with W173/XW5 and BANK0 or1, on its explicit bank root. Central `ot_smh_banked_xc_central` runs on `clk_core`: native request67, row173, word_ok11 and row_token67 are connected per bank, plus native config enables/address10/data256. Existing descriptor SRAM, host rc, and descriptor identity/reserved-bit checks are retained. In particular reserved231:200 remains zero, including200; class does not reuse that field. Four actual SRAM macros remain: two1024x256 program banks and two128x256 descriptor macros, 73,728 bytes total. DD128 uses one descriptor macro instead.

| Path | Additional edges versus corresponding canonical PREL profile |
|---|---:|
| Descriptor admission / GO schedule | 0 |
| Banked calendar | 2 |
| Existing R/C, PREL0 or1 | 0 (canonical behavior retained) |
| Full175 cache mirror | 2 |
| Public command, all64 KV, independent class/valid association | 4 total |
| Runtime done and fault | 4 total |
| Configured and target-local config faults | 0 (collar chronology retained) |

Done/active/fault have two output tail registers. Host running/fault are aligned by2 before the tails; native application fault is captured before the two fault-tail stages. The direct wrapper fault output is Q, without a combinational output OR shortcut. The unchanged target collar still owns its historical target/config status behavior. The semantic local post-R/C guard remains independent of any downstream assembled-command guard; its fault precedes mirror2. The wrapper does not add another semantic guard or change the common app.

Retained observation aliases count as physical pins: direct555 inputs/353 outputs=908 total; target332 inputs/354 outputs=686 total. Observation adds177 output aliases, not zero-cost extra visibility. Public host/descriptor roots and these aliases remain physically unqualified. Fleet tests tie the three roots to aligned equal-frequency clocks; they are not a phase or physical proof.

## Exact intentional status correction

`n_done` tracks admitted GO minus consumed native cal_done. It increments on GO alone, decrements on cal_done alone and holds on simultaneous events. Final done requires `n_go==0 && n_done==1 && cal_done`. A run is rejected while a descriptor run or programme remains outstanding. The old predicate `cal_done && !running`, transplanted into the deeper banked calendar, could complete a previous programme after the last GO while another programme remains outstanding.

The nine-edge tight case admits GO at513/522. The naive predicate is witnessed at522 with descriptor running0 and outstanding2; native completions are consumed at523/532. There is exactly one public final completion. The ten-edge case admits GO513/523 with first completion consumed on523: increment and decrement coincide and the outstanding count stays1; final completion is consumed533. There is again exactly one public final completion.

Active deliberately remains1 during outstanding work. Every other edge compares active to canonical+4. An active mismatch is accepted only for new1/old0 with an independently maintained outstanding-programme history at the matching five-edge pipeline age. The bench independently requires active continuously1 from first admitted GO through final consumed cal_done+4, and0 on final+5. It also compares DUT n_done against the independent ledger every checked edge.

For the final PREL1 baseline, the repaired old-idle edges are116/117,310/311,529/530 and714/715 across the four scenarios. At each, descriptor running=0, app_active=1 and n_done=1. Single-case GO/completion-consumption edges are109/119,303/317 and707/717. Tight-GAP10 repairs are530/531. These are bounded intentional status corrections; full old-status equivalence is not claimed. The original six active-only failures are retained in `historical_active_mismatch_3da10b7cd.log`. That first bench checked strict active only for single-GO cases; the final bench removes that tight-case gap and checks all cases using the independent ledger. Command/KV/done/fault comparisons remain strict everywhere.

## Immutable fleet evidence

`functional_94dbdbbaf/receipt.json` contains every compile-source SHA256, Verilator version, fleet unit, and result. Frozen wrapper source is6daf49dbe; final test source94dbdbbaf. Fleet host selection was unpinned via `ot-run --mem16 --threads8 --dir /tmp`, placed on ot-epyc6, unit `oth-ubuntu-2458897-1792432665`. Verilator5.050. All12 builds ran and produced simulation result lines; top-level fleet exit0 alone is not the oracle.

Five positives PASS448 checks each (2,240 total): PREL0/1 times CLASS0/1 at GAP9, plus PREL1/CLASS1 at GAP10. Each profile checks four scenarios: both programme-bank boundary1023/1024 with format and relocation; last row2047 with loops and literal commands; descriptor127/128 and tighttwoGO; reserved descriptorbit200 rejection. All64KV bits are patterned and preserved; command-zero/KV-nonzero and extension-only magic-low83-zero are exercised. Wrong-target overwrite is ignored in positives. Independent canonical class/valid is carried alongside canonical R/C, not taken from the new DUT.

| Negative | Result / errors | Witness |
|---|---|---|
| MUT1 rc starts0 | FAIL44 | first command extra edge5, status/ledger checks |
| MUT2 wrong command/KV slices | FAIL27 | full175 mismatch |
| MUT3 host reset never releases | FAIL260 | missing command/completion |
| MUT4 bypass R/C | FAIL38 | command arrives2 rather than4 edges later |
| MUT5 ignore target id | FAIL6 | wrong-target programme overwrite reaches command |
| CLASS_MUT1 mismatched semantic class | FAIL251 | envelope mismatch and registered fault |
| MIRROR_MUT1 mirror one edge early | FAIL36 | command first delta3 |

MUT4's diagnostic generic central shares the same two real SRAM-bank outputs, adds no SRAM, and its requests are asserted equal to the app requests every checked edge. Default MUT0 eliminates this diagnostic central. Each committed negative log contains `XCAL_PUBLIC_BANKED FAIL` and a fatal `public banked XC mismatch` witness. There is no expected-failure waiver.

Replay individual profiles with `bash rtl/test/hbm_accel/svg_rel/run_xcal_public_banked.sh OUT MUT PREL CLASS CLASS_MUT MIRROR_MUT GAP` inside an unpinned fleet job with the exact sources in the receipt. No simulation or synthesis was run locally.

## Pre-gate checklist

1. Pins/reset: OPEN for cloned host/descriptor/collar; no native boundary/reset qualification claimed.
2. Reach: OPEN; no wrapper placement or outline proposed.
3. Fanout: OPEN; child mapped evidence is not a wrapper census.
4. Depth: OPEN; functional pipeline edges are explicit, physical path depth unmeasured.
5. Storage: four actual SRAM macros and350 mirror bits are explicit; full wrapper storage/depth audit remains OPEN.
6. Floorplan/access: OPEN; canonical macros unchanged, no cosmetic LEF edits.
7. Clock: three distinct source ports, aligned functional bench only; native timing/spread/reset-source graph remain OPEN.
8. Schedule: functional PASS for exact+4 command/KV/done/fault; active correction precisely bounded and separately proven. Parent owns shared compiler and whole-service price.

This packet authorizes integration into the explicitly flagged functional composition only. No canonical/default replacement or physical release approval is implied.
