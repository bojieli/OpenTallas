# B2 IDX.INDEX native control and physical plan

Source adapter: 0d8f55c19, unchanged arithmetic, reduction order, selector tags and mutant points. Integration base ade0e472cb38c5c9cb30479cf4ef41e7fed0b220. Historical packet results and the 29,447-flop / 929-ps adapter gate are not physical or throughput qualification.

## Native ownership and service budget

SW slice sid=0, wide client slot=5 (SW KE=6), 8 lanes, sector low three bits select bank. Read request native8x17, read credits8, reply8x257; write request8x281, credit8, commit8; independent registered request/grant handshakes. RRS=WRS=3 gives LQ=10. Query A 4096 words, weights B32 words and optional C IDs plus values belong to REPL [262144,294912). Outputs O/R and optional D IDs plus values belong to SW [0,65536). All full 40-bit bases and extents are validated before dispatch. The legacy18-bit core sees validated offsets; read translation adds native sec16 mirror bit, writes add SW ownership. A/B/C are all mirrored, so no per-request mirror owner switch is necessary. O/R/D are all owned SW. Owner remains fixed until completion after every write-done.

L24 price remains1080 streaming cycles, allowed maximum1188. L20 and L2 must also be exact. Scorer remains64 keys/cycle, four stacks16 each; adapter must accept four read sectors/cycle and issue one sector/lane/cycle subject to credits, query32 words/cycle, output8 survivors/half beat plus two candidates/beat. One record dispatch register adds one exposed streaming edge, to be measured rather than repriced. LQ10 is finite; read landing DL2 additionally bounds issue reservations. No whole-array bench.

## Physical cuts before structural RTL

No flat route is eligible: current29447 sinks exceed15000 for a new root. Candidate hierarchy has two four-lane landing tiles (pin captures,2x256-bit landing per lane, pointers, read reservations/credits, write pin launch), four unchanged output packer tiles, and one bounded core containing issue/log, gather, query ring, keep stages and selector ingress. A synthesis census must determine whether core itself needs a keep tile and a selector FIFO tile; estimated split is not acceptance. Root per leaf <=15000, no datapath reset, control reset fanout measured.

Candidate cluster envelope640x480um: two lane tiles on W/E, core centre, packers at output faces. Registered reach <=500um; external SW lane station is approximately1886um away vertically from IDX site and therefore requires at least3 intermediate registered stations (actual Manhattan and legal positions must be measured in native die placement). Each seam uses an ordered finite-credit link; credits cover registered round-trip and every captured pending beat. Arbitrary delay-only flops on valid/ready are prohibited.

Conservative major-cut demand: read half4x(17+1+257)=1100bits/cycle; write half4x(281+1+1)=1132, combined2232. At480um span, M5 horizontal pitch0.064um, reserve25% power/access/spare, capacity5625 tracks, ratio0.397. Orthogonal selector cut: fs90+qb1048+kin345+to612+co72+qbr1+toc1+coc1+ev2=2172bits/cycle; M4 vertical0.064um over640um with25% reserve=7500 tracks, ratio0.2896. These are planning upper bounds, not routed evidence; actual PG/OBS must be deducted and no M6 child signal is allowed. Leaf M5 signal/PG default; cluster layer grant must come from die lead if M6 inter-child routes are needed. Pins belong to registered faces; avoid a pin-driven outline increase.

## Required evidence

Pinned existing source0d8f55c19 BASE/MUT2 incremental production build is owned by throughput agent on EPYC4; no duplicate. New native mapping gates need exact address/data/mask/credit/done propagation and invalid full40-bit/extent negative controls. Structural hierarchy requires a source-matched composition exact+mutant and production rate gate before route submission through ref_tile. TT/FF/SS, DRC0 and child_lint cap are required. No closure, native production qualification or die assembly is established by this plan.

Native transport implementation: ot_hgi_idx_b2_station uses existing finite burst-owner/release-handshake station at K6/ID5, native REQW17 read and281 write. Upper24 padded lanes are zero at every physical boundary and synthesis must prune them. Native tap137bits read up and2249bits write up; old SPEC129/2241 counts omit mirror sec16. Station source needs its own synthesis/reset-fanout/physical gate; no physical acceptance claimed.

## Reused actual synthesis gate, source hash confirmed

The preserved PVE1 gate `idxw_b2-20261012-202510` has adapter SHA256 `5bbff6eea5bb2d5638bd8690960869a28e5dde14d741a6c7094a674d3a74bd85`, exactly the imported0d8f55c19 source. Its actual textbook receipt is `pinned_adapter_textbook.json`:184343cells,29447flops,0macros. The offending stage is `k1_q[19][0] -> k2_ord[19][11]/D`,929ps/26levels. The dominant high-fanout points are selector FIFO head `tfh[1]`4874loads and query ring pointer `rg_rp[0]`4097loads. Splitting lane pins alone cannot cure those core paths. Keep ordinal division requires an exact registered pipeline; FIFO/ring gathers require regional pointer copies at actual hard-tile boundaries or local SRAM. Added stages must be measured against immutable1188cycle maximum, with golden field ordering and candidate matching unchanged. No new synthesis was duplicated to learn this.
