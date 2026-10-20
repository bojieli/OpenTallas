# STREAM mapped source census, 2026-10-20

Both closed STREAM variants fail the mandatory mapped census: **211 roots over32 loads, maximum69, zero Liberty role errors, 33,987 dynamic roots examined**. Their retained synthesis Verilog and synthesis ODB are byte-identical. This is a source topology failure shared by both floorplans. No RTL, helper, physical gate, routing or submission was changed by this packet.

Source49ac29c7e1fbce8855046901fcbd71864a1a227f, core SHA256 caacbf7b9942e21f52284fd39c92905089060f2fbb748233d6d958407c396b19. The exact core source is included. The mapped tool inspected the full qfd_dv_stream_tile top, including the retained wrapper/reset copies. All mapped masters were retained; no cell, clock-name or data-name filter was introduced.

| Source cone | Failing roots | Actual native loads | Source cause |
|---|---:|---:|---|
| sw_v, se_v |2|37|34 face valid captures plus decode/fault inputs share each raw valid port.|
| cm_c[0..31] |32|64|32-bit enabled eword groups consume two mapped select pins per payload bit.|
| pe_c, pw_c |68|33–34|32 payload gates plus shared insertion/housekeeping controls exceed32.|
| te_c |33|52–66|Two select pins per payload bit,26-bit header group and group0 side controls.|
| xe_c |33|48–66|Wide x-tap mux selects, header group and group0 side controls.|
| xw_c |33|40–66|Wide x-tap fallback mux selects, header group and group0 side controls.|
| cv_c[4] |1|56|28-bit held tag update uses two select pins per bit.|
| wa1_c[32] |1|37|Shared open-state and16-bit xbeat update enable.|
| wa_q[26] |1|36|Lane1 low-digit address bit reused through shared slot decoding.|
| Combinational predicate/decode outputs |7|33–69|Four tap predicates each drive33 capture flops; write-any drives36; one lane1 hi_hit branch drives33; complete/write-any drives69 cm captures.|

The seven combinational roots are _54629_/Y (xe predicate33), _54633_/Y (xw predicate33), _55791_/Y (lane1 high-digit branch33), _56266_/Y (completion69), _56273_/Y (te predicate33), _56280_/Y (tw predicate33), _56364_/Y (write-any36). The compressed classification reports resolve every reported sample endpoint to its exact mapped master, instance and pin. The unmodified census records at most40 endpoint samples per violating root; loads and verdicts use all endpoints. Classification does not turn truncated samples into complete endpoint inventories.

There are12,527 mapped sequential cells:529 DFFASRHQN and11,998 DFFHQN, with zero SRAM masters. Source words include1087-bit input pipelines,1024-bit assembly/emit/tap pipelines,512-bit one-hot state and smaller masks/metadata. Their aggregate FF count is not evidence of a single >2kb memory array. The independent storage, functional-pin and registered-pin contracts remain **NOT_EVALUATED**, as the mandatory tool reports. No ASR behavioral simulation or cold-origin qualification is claimed here. No constant top output bits were reported.

## Reproduction and immutable identities

Own fleet directory: ot-epyc5:/srv/opentallas-scratch/claude/codex-qw-stream-mapped-census-1020. Original closed artifacts stay under closure-loop/<exact-job>/routes/<job-with-underscores>/work/orfs, with results/logs suffix recorded in manifest.json. Both originals and their1_synth.odb,1_1_yosys_canonicalize.log,1_2_yosys.log were hashed before and after; all hashes match. Common Verilog05fa8f90ccbe6000309035c3359e7bea8d7b365a7d29f3968f20ea068b5750db, ODBb49f316617b112c5c43c68abe966b779a23efe6ac3a800e5e07838e0a137c8f7.

Current-main tool snapshot940af34287955689574cb1231ae8d7049a925235: native_census.py SHAa3af6dd8f665326b75804a8da115cd5d0f3c8d40265f9ad9a51068cadfcf2cd4; textbook_lint.py SHA4adb3e6072ab0e5d93ddaa5205d5139c37971aa87175b1923beea9261dd2619b. The retained synthesis frontend logs name five unique RVT TT libraries; these exact paths were read from openroad/orfs:asap7lock observed image ID16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29. Their snapshotted bytes/hashes remain in the own fleet directory and manifest. Historical logs do not contain library-byte hashes or an immutable historical image ID; the packet explicitly records the observed retained image and loaded path evidence rather than inventing those receipts.

run_census.py extracts the actual logged library paths, runs the unmodified mandatory tool, and hashes before/after. The runner exits0 after collecting both results; **each census command exits1/FAIL**, individually recorded in manifest. Unpinned ot-run admitted ep5 unit oth-ubuntu-2672443-1792486861, completed exit0. classify_census.py ran as unit oth-ubuntu-2682389-1792487022, completed exit0. No owned fleet processes remain for this packet. Full census/endpoint-classification reports are compressed losslessly; summary.json retains every violation uncompressed.

## Default-off successor model

native32_candidate_model.json is a proposed model, with default_enabled=false and rtl_implemented=false. It budgets15 payload bits per leaf: at most30 mux pins plus two separately accounted side pins. It also introduces bounded registered root banks so splitting leaves does not simply increase the predecessor root beyond32. Input header, payload, valid, configuration and own-write identities move together.

The candidate adds one coherent ingress edge and one completion distribution edge. Pass relay/table/x taps therefore cost+1 external edge; own writes cost+2 versus current t2 (+4 versus the preceding tile, +5 versus qfd_dv_stream). A1024+16-bit payload/beat snapshot preserves the complete word while a later beat enters assembly. The target II remains1, requiring continuous-beat gold evidence. Tag enables and open/beat controls split at the same edge; lane address/enable copies feed disjoint local decoders. Unused kept tw captures may be removed only after a semantic proof. Purely combinational duplication and buffered trees cannot meet this native root rule.

The model gives schematic leaf/root counts and carries actual mapped FF totals, area, slot fit, reset/clock root inventory, warm/first-valid costs and K asNULL. The raw input-stage source-bit ceiling2664 includes fields that may optimize away; it is explicitly not a measured added-area claim. The source/model/continuous-beat/reset correctness, full mandatory mapped census, all-root reset semantics, whole-frontier compiler/calendar acknowledgement, and physical floorplan/reach/phase checks must close before any new gate. Existing CLOSED status and parent-selected final PG checks do not release this source topology.

## Other lane boundary

KV owner has supplied only a **DIAGNOSTIC_ONLY_SOURCE_ORIGIN_WITNESS** graph: source54e9d9c39 plus health-ledger producer17b71, diagnostic table SHA c4c3d2ca791df75b23dc7f6d3cacf465b0acf0db67b0ed4ddd149f6e3e5a7429, bound actual SFM TXDP[22,4,3,3]. Native/physical qualification=false and bind verdictFAIL; canonical production filenames remain absent. It may support source-origin diagnostics, never production F2/phase/package release. GEN common-origin/raw-G/R0/K and the13 current SLICE6 whole-frontier receipts remain blocked; this STREAM packet does not fill them.
