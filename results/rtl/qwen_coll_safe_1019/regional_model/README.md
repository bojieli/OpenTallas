# Regional codec ownership decision model

**Neither variant is implemented or qualified. No next S1 gate is authorized by this model. ROOT must select a measured crossing contract.** The inherited phase-1 integration failure remains an independent blocker; an unchanged sum of TX/RX ages cannot qualify a calendar.

The source-bound S1 gate failed on codec0 TT boundary spread450.8ps, while cal_ck38.9ps and cal_lck0.6ps passed the80ps spread rule. It has1155 TX,1152 RX and99 control flops on the shared codec root. `synth_cones.json` measures exact1_synth.odb cones: TX337.323um² flops+662.384um² combinational; RX336.186+716.155; control36.917+746.627. Control/RX share694.854um² of CRC/check logic. **RX owns the complete CRC/slot/epoch checker and reports narrow fault metadata to control. These overlapping cones must not be summed or duplicated.** Union combinational area1428.563um², total codec flop area710.425um². New smaller-width landing combinational/CTS area is not measured; no exact mapped area is invented for either proposal.

The proposed face has **ten regional CTS entries, eight unchanged raw hard-child entries and two calendar entries** (20 total; production face_ck becomes100 bits for five faces). Regional ownership is: control; four bank-command receivers; bank-return bridge; TX packet/CRC; RX pin storage; RX checker; RX CDC-write landing. Raw entries still clock only two CDC and four codec children. All native communicating clock pairs must prove TT and FF<=80ps; full-die balance is not a substitute.

Geometry keeps the950.4x561.6 face and the scoped RX+24nm waiver. TX input/PHY buses move to43.2um-high spans y108..151.2; RX output/PHY spans y367.2..410.4.597 M4 pins need28.656um at48nm pitch, so these spans are feasible before pin-fit/DRC. TX/RX approximately1000/1052um² cones each fit a43.2x43.2 local region at54/56% area; these are allocation targets, not placed timing evidence. TX packet region is beside E129.6; RX pin region E388.8; TX bridge around(734.4,237.6); RX checker around(648,388.8); RX write landing around(362.9,388.8); command source around(490,237.6), with bank receivers beside their own SRAM pins. Representative inter-region Manhattan legs are at most352.8um (command source to bank3),324um (bank output to TX bridge),297um (TX bridge to TX packet),276um (RX pin to checker),285.1um (checker to RX write landing). Actual bit endpoints, clock root pins, complete reset/fault bundles and routes still require proof; these points are not a route receipt.

Four new paid crossings are explicit:

| Crossing | Exact bundle before physical subdivision | Width/lanes |
|---|---|---|
| Calendar/TX CDC to bank commands | per bank `{we,wa[5:0],ra[5:0],din[136:0]}` |4x150 |
| Bank-return/metadata bridge to TX packet | per bank `{payload137,rd_v,rd_slot6,epoch8}` |4x152 |
| RX pin to RX checker | `{physical_frame597,observed_valid,expected_valid,expected_slot6,epoch8}` |154+153+153+153 |
| RX checked word to RX CDC write | `{payload546,observed_valid,compiled_write,addr6,version}` |139+139+139+138 |

Every lane is<=154 bits. These are source-visible independent validity/identity bundles. No observed receive, PHY-up or occupancy may select issue. Expected-token and fault/epoch paths must be aligned with these exact stages; fault return can add diagnostic latency but cannot silently change normal publication. Write and read commands move together, preserving KW. All reset copies keep their local two-edge depth; compiler startup/drain must include actual fixed initialization rather than wait for credits.

| Contract | LU/LS | AR256 span | Argmax span | Added token cycles vs current249577 | P/R macros |
|---|---:|---:|---:|---:|---:|
| Current source |53/378|797|446|0|2 per ring,4 total|
| A: independent E2 target, **MODEL** |61/386|821|462|1744,0.699% cycles|2 per ring,4 total|
| B: concrete gated final-capture model, **unqualified** |65/390|833|470|2616,1.048% cycles|4 per ring,8 total|

`make_tradeoff.py` uses the existing single compiler source `qwen_coll_tp8_static_bench.schedule` for every row and saves all six programs. AR pays2*deltaLU+deltaLS; gather paysdeltaLU+deltaLS. Token price is72 AR+1 argmax. Consequently pricing only73*deltaLS would undercount these proposals. Throughput loss, at the same core frequency, is0.694% for A and1.037% for B. Single-word steady issue remains a target of one word per edge; these compiler spans do not prove achieved hardware throughput.

A assumes each of four crossings replaces an existing capture with an independently safe landing that adds exactly two edges: TX+4, RX+4. Its exact payload-state count is5*2376=11880 bits (four stationary slots+one output); **full control/epoch/reset state and mapped area are undefined until a new primitive is implemented and qualified**. There is no qualified E2 view to substitute. This optimism must not be selected merely because LU61 fits the old bank bound.

B uses `ot_qfd_land_gated` sourceff0368257 (physical area receipt from62708ac8f) with its extra final receiver capture. The contract is not automatically E2: actual ring age, K, epoch startup and root phase must be measured. For FIRST1 its exact declared state upper is `9W+5ceil(W/16)+68`, giving23252 bits across16 lanes including144 ICG latch bits; FIRST0 upper23220. W180 previously mapped1746 state bits and616.223700um², with zero SRAM macro area. W150/152/154/139 mapped areas have not been measured. The integrated+3-edge/crossing price is a model until the actual source is composed and witnessed.

B requires the **real four-bank P/R architecture**, not removing the LU guard or aliasing four banks onto two old clock entries. `ot_coll_static_ring` has B4 when LU+2=67>64, but current `qfd_io_collective_static` explicitly rejects it and duplicates two memory roots. The implementation must add four genuine P/R clock entries, four additional32x546 macros, correct selector/address logic and a new packing. Added SRAM capacity69888 bits; exact added macro area4*177.768*81=57596.832um². Total P/R macro area115193.664um². Existing R0 diagnostic kits implement the old two-bank profile and do not qualify B.

Before another S1 gate: ROOT selects the crossing architecture; implement exact source+capacity+clock graph; measure state and cone area for that source; derive calendar/GEN/compiler from one source; prove first operation after both boot orders, repeated reset/drain and epochs; test all native phases with frame identity; run AR256, argmax, consecutive2x256 and2x256+argmax plus MU schedules for steady issue, no overlap/stall/fault and exact expected output cycles. Mutants must catch each crossing's wrong age/slot/epoch, unlanded bypass and missing PHY fault. Only then generate a source-bound geometry and gate TT setup/FF hold>=0, clock-pair TT/FF<=80ps,<=405um data reaches, hold0.03, native clock coverage and pin access/DRC. No masks, oversized route fallback, REVIEW.json or submit.
