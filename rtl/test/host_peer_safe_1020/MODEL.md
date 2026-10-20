# Current peer successor: source7338ce567

**Candidate only, default0, no layout gate/adoption.** Bare datapath preserves all qualified transfers, credits, faults and edges. Two p19232x546 macros replace >2kb queues; effective four entries each. The512b mailbox remains flop storage (<2kb), captures whenever empty including invalid cycles, then holds while pending via32kept same-age hold controls, each16bits. Mail hold copies are set from the exact next pending state in two independent source cones. A real take while empty captures the producer word on that edge; once pending, the held word is immutable until the send edge. Invalid mailbox payload has no reset and cannot become visible until an admitted take.

TX payload captures without an emit hold-enable; onlytx_v qualifies consumption. Normal RX payload also captures freely, qualified by normal_rx_v. Thirty-three kept predictive choice controls each drive16bits, using exact post-edge nn/pending/rr from two separate same-age state cones. No broad inverted-source union remains: actual-Lib effective census includes both polarities.

Latest pureRTL Verilator5.050 campaign uses --x-initial unique/--x-assign unique and randomized unreset initialization: PASS100000 edges/22438normal sends/27960peer receives/18705peer sends. Bypass/address/choice/mail-hold mutants differ at5/7/5/6. Default0 comparison is separate. All payload comparisons are qualified by matching valid signals; valid/credit/ready/fault/drained compare every edge. Older evidence below is retained.

Native bare source FAIL8839roots with **one offender: rawrst_n139**. All non-reset data/control/selector source cones <=32. Public reset-only wrapper adds the standard two synchronous reset-landing stages, eight final same-release-edge kept copies, one first-stage copy, and split32: **PASS8865roots/max32/zerooffenders**. Reset family loads18,18,18,18,18,18,18,14. This coupon is explicitly reset-only: no input/output data pin stations and no source reset waiver. Assertion/release shifts by two clocks at this wrapper boundary; bare data latency adds zero.

Mapped area58170.69538um² including two177.768x160.392um macros and682.43148um² sequential cells. Earlier third-SRAM mailbox candidate area86700.18786um² is superseded by the same-age512b hold implementation, saving28529.49248um² (~32.9%). Full pin registration, final footprint/43.2-lattice geometry/reach/clock price, and production traffic budget remain HOLD before any layout. Current peer RX head/valid remains the original combinational handshake boundary; source changes preserve it exactly, and any registered boundary successor must explicitly price its added edges.

Census prototype exact toolsource94de8573f, actual5SS Liberty families AO/INVBUF/OA/SEQ/SIMPLE +macroSS; no imported cell functional model used. PDK HQN model-integrity warning therefore affects neither pureRTL proof nor native counts.

# Historical bounded queue step

# Peer queue bounded successor

Base a7b57f71f, opt-in SAFE_SRAM=1, default 0. Existing four credits, no added edge; this block preserves the existing exceptional peer credit protocol. No adoption or layout gate.

Two queues become two 32x546 p192 SRAM macros; effective capacity remains four each (528 and 512 used bits), allocated 34944 physical bits versus 4160 former queue flop bits. One synchronous read and one write per macro per edge, payload bandwidth 528/512 bits per edge. Read address is post-edge head; captured same-edge data handles SRAM read-before-write collisions. Three kept pointer/count source regions per queue feed at most twelve 16-bit bypass selectors. Captured bypass data is unconditional; payload and bypass have no reset. All controls/counts reset.

Consumption proof: any valid head follows an admitted write after reset. The first write into an empty queue collides with prefetched head and establishes captured bypass. Otherwise a preexisting head is in SRAM before the read, or simultaneous tail write/head advance collides and selects bypass. Unconsumed invalid payload is outside the valid-qualified interface contract. Reset drops both queue counts; no pre-reset payload is consumed. Fault and credit/control outputs must remain cycle-identical.

Remaining full-root families before native census: reset on 1544 payload bits, tx emit/choose mux controls, mailbox capture enable. These require separate <=16-bit control/source/reset partitioning; this queue step alone makes no native32 PASS claim. Pins/reset landing, final geometry/area/clock reach remain HOLD. No layout before complete mapped actual-Lib BUF/INV-effective census <=32, exactness and causal mutants.

Measured source 16c53cf70: Verilator5.050 PASS100000 samecycle; 22438 normal sends, 27960 peer receives, 18705 peer sends. Bypass and wrong-address causal mutants differ at edge5/7. All valid/control/credit/fault/drained outputs compare every edge; payload compares on valid. Resets every1024 edges, malformed frame and overcredit injections included. Initial undercoverage bench failure is retained; seed-once correction establishes real traffic diversity.

Mandatory mapped actual5-family SS Liberty+macroSS census **FAIL**, not a layout candidate: 10257 roots, five offenders, max1639. All 2187 named queue drivers <=32, including bypass32 loads for each16-bit selector. Complete remaining families:

| Net | Loads | Source family | Required next structural step |
|---|---:|---|---|
| rst_n |1639|1544 existing payload reset bits plus control/queue state|remove reset only from proven valid-qualified payload; kept reset leaves for control and pin reset landing|
| _07119_ / _09506_/Y |1045|emit hold/enable, from fault+physical+nn+peer_pending|enable-free tx payload launch and <=16-bit same-age control producers|
| _07140_ / _09541_/Y |1025|take_peer mailbox capture from fault+pending+peer_tx_valid|<=16-bit mailbox source capture controls with retained same-edge state|
| _04054_ / _10747_/Y |993|choose_peer mux from nn+peer_pending+rr|kept <=16-bit selector producers, not buffer copies|
| _04060_ / _10753_/Y |33|opposite-polarity choose_peer upper/tag path|same source partition, all-driver census must include both polarities|

No role errors, no constant functional output bits. Pin-registration/storage contracts remain separately unevaluated by census; direct source inspection confirms two real macros and unchanged four-entry capacity. Strict no-gate/no-submit/no-adoption HOLD until all remaining families, registered peer valid/data output boundary, reset landing, actual mapped area/geometry/reach and clock costs qualify. No native-cell behavioural model proof used: direct RTL miter only, so the HQN model-integrity warning does not invalidate the exactness evidence.


## Full historical r6 leaf coupon (3707551fc)

The exact historical leaf has135ports/6301bits:2801input (2798data +clock/tworesets),3500output. Existing recipe4 adds2798input and3500output pin FFs; its +1input/+1output data edges are preserved, so no new data edge or H delta is introduced. The original peer_rr still asserts asynchronously and releases after3core edges; the existing outer reset landing shifts assert/release2edges. Reset copy counts change only same-age multiplicity.

The standalone peer_rx_data/valid boundary is internal to this leaf: peer_link_rr_sram.u_m -> u_rank__peer_rx_data/valid -> root__u_root_mux.u_m.physical_rx_data/valid. That existing _pl2 receiver captures rq_d on rx_take&&shape and sets rq_v on the same edge; peer_pop equals the same valid/ready event. Thus the source's bypass/count outputs already terminate at the receiver's existing data/valid registers. The new SRAM source does not require a new peerRX output station in this historical leaf. External physical RX/TX and normal stream top ports retain recipe4 stations. No new +1edge/H delta is proposed.

Pre-map reset split inventory: coordinator5464/28 copies ->max196 (minimum171copies), rankcodec967/16->61(min31), rootmux536/3->179(min17), controlpacket2619/12->219(min82). New peer140/7->20 passes. These are independent legacy sibling reset families, so isolated link native32 does not qualify the full leaf. Full mapped census is running; none of these refusals is hidden or waived. Increasing region count alone also requires checking that each reset producer/root stays<=32.

Preliminary packing uses the actual two p192 macros177.768x160.392um (LEF explicitly allowsR90), rotated to160.392x177.768um at43.2-lattice origins(43.2,43.2)/(259.2,43.2). Proposed432x388.8um outline gives55.608um channel, minimumedge12.408um,10.8um halos and full-width cell band with y231.768..378.0. Existing face pin countsN1551/S1638/E1557/W1555 yield3.590/3.792/4.005/3.999pins perum, below6. Macro read/write pin faces eachcarry546pins across177.768um (~3.07/um). The old280.8square is not reused. Exact full-leaf mapped area, standardcellutilization/pin-bound fill justification, actual boundary reach<=405um and clock station siting remain unqualified;432um outline width alone does not establish data reach. No layout before full native32 +ROOT helper acceptance +approved physical slot.

The provisional outline grows from historical280.8square (78848.64um²) to167961.6um²: +89112.96um² /2.13018x footprint. This expansion is a proposed model cost, not an approved HOST die slot or packing result. H/data latency remains unchanged; physical slot and reach require ROOT disposition before a layout gate.
