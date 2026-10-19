# HIDX joint native-cohort source model — terminal construction FAIL

This is a finite structural analysis packet. It contains the first failed native packing, one explicitly authorized demand-driven refinement, and a read-only correction of per-contact wire-cap accounting. No synthesis, placement, OpenROAD, CTS, router, source protocol change or production adoption occurred. Original actual checkpoint 70042afe82ff76fc2657f45fb6c2a89f91eed2993add8e9dc89f2fc612fc88a6 and all predecessor failures are unchanged.

The proposal removes the one-quad-per-bucket constraint: twelve genuine quad cohorts initially occupy three per north/south half-band bucket; pairs and slices are assigned by actual fixed-port native capacitance costs. The contiguous 104-row band uses 36/32/36-row stripes, native site widths, the existing 10.8um clock spine and unchanged 140.4um pin outline. All 504 legal rows, 11,145 genuine native cells, 2,904 FF, original source cycles and every 80fF output load are retained. There are zero new drive buffers, FF or data cycles.

## Actual-demand refinement

The first native packer failed on pair[0]'s genuine 39-site FF atom (ep8 unit2305073, actual exit1). Its native fill was47.4454% and atom reservations83.3085%; aggregate area fitting did not prevent interval fragmentation. Exact source, failed log, initial diagram and STATIC_FAILURE.json remain immutable. A later ROOT instruction explicitly authorized deriving actual demands and one bounded analytical refinement.

Each real multirow capture bundle and single-row functional atom was packed using actual native widths, unchanged FF→INV→BUF affinity, existing physical gaps and two eight-site candidate routing margins per region. Necessary width floors include widest atom, total reserved atom area / rows and native cell area /60% density. The reported width is a verified finite constructive pack, not a globally optimal width or an exact monotone-search proof. At36rows, genuine quad demand is273sites and slice163; at32rows pair demand is240sites. Binary search retained and finally reverified a feasible full interval pack. DEMANDS.json and ACTUAL_ITEMS.json preserve every item and coordinate.

The demand allocator moved real slice[6] from bucket3 to4 using native-port weighted cost (delta−206722.7960688). This repaired the over-demanded bucket without a blind row-size sweep. All11,145 actual native boxes then fit without overlap. Every cohort has40–60% native mass; extra genuine empty sites are distributed across the region. Exhaustive window maxima are2.7×2.7um70.0%,5.4×5.4um67.0%,10.8×10.8um57.125%; single-row5.4×.27um67.0%. Small-window hotspots remain explicit. SOURCE_MODEL.png and SOURCE_DENSITY.png display native boxes and true empty sites, labeled SOURCE ONLY.

The reused exact native fiveTT/fiveFF Liberty collector reports11,449 nonclock nets,252884.4995um nominal RMST, maximum root path252.768um, zero nominal RMST cap excess and all2,904 FF CQ load axes within their actual native grids. These are unconstrained geometric wire models, not waveform/setup/hold or real-clock evidence. Native M4 band cut demand remains952 versus468 PG-clear candidate rays (340 after128 source-clock reservations), motivating the explicit exterior ownership attempt.

## Complete finite ownership attempt

The same frozen demand plan was passed once through the finite shortest-H-path, actual-PG-clear M3+M5 vertical ownership constructor. Unlike the predecessor, every net can select the nearest band or exterior H ray; fixed ports, PG, outline and clock reservations do not move. Native wire widths remain18nm onM2/M3 and24nm onM4/M5. Actual PG ray/default-via inputs and source hashes precede the unpinned launch.

| Ledger | Result |
|---|---:|
| Horizontal trunks |11449/11449|
| Assigned modeled native-contact leads |30536/31384|
| M3 / M5 leads |17233 /13303|
| Missing contacts |848 across476nets|
| H extensions colliding after vertical ownership |2290nets|
| Geometrically complete / incomplete nets |8683 /2766|
| Union-wire cap excess TT / FF |124 /127nets|
| Union-cap excess among complete geometry TT / FF |35 /38nets|

All31,384 native contact records are accounted:30,536 have explicit modeled lead geometry;848 have explicit failure witnesses. Every contact still has native local access/via/DRC HOLD. Complete proposed root-to-contact path lengths are enumerated in COMPLETE_PATHS.json.gz; maximum among geometry-complete nets is199.524um. No reach claim covers missing contacts or conflicted nets. Source statement “all complete paths short” cannot repair missing ownership.

Actual run ep7unit237572 was unpinned16GB/2threads and ended RAN exit0; exit0 means the model completed with FAIL. Constructor maximumRSS153988KB. Per-net geometry, all848 contact failures,2290 ownership failures, source/input manifests, logs and proposed PNGs are retained. No unchanged greedy retry followed this terminal construction.

## Wire/via accounting correction

The constructor's raw229TT/233FF cap counts sum each contact's vertical path; same-net collinear overlaps can be counted twice. Those values are preserved as RAW_UNQUALIFIED for geometry capacitance. The read-only union collector retains layer, orientation and exact track coordinate, unions same-net H/trunk/local-jog and M3/M5 centerline intervals at unchanged native widths, then uses actual native layer-C coefficients and real native/external loads. Its corrected candidate counts are124TT/127FF. Unknown via/enclosure/fringing capacitance remains HOLD, never a qualifiedzero. A first example is real XNOR2xp5 net7317: native+externalTT4.342268fF plus union-wire25.66588349 =30.00815149fF versus native23.04fF maximum. Thirty-fiveTT/thirty-eightFF excess nets have otherwise complete modeled H/V geometry, so overlap correction does not erase this candidate's electrical failure.

The139560 per-contact native layer transitions are NOT unique implemented vias. Exact shared-cut union, local source M1 landing, fixedM4/M5 port jog stacks, via-cut staggering and native metal enclosures remain explicit HOLD. No full via/PG cost or timing closure is inferred from that ledger. Actual PG2,117,134 rectangles and128 clock ray reservations are reused inputs, not fresh PG-contact proof for relocated cells or implemented clock routing.

The same issue exists in predecessor148b: its raw278TT/280FF cap counts used the same per-contact sum. Read-only union of its unchanged geometry gives164TT/174FF candidate cap excess, including50TT/58FF geometry-complete nets. Original reports remain byte-identical. HISTORICAL_UNION_SUMMARY.json explicitly supersedes the raw cap interpretation; its9836 missing contacts and574 extension failures remain the independent finite-construction rejection. Incomplete wire plus unknown vias does not by itself prove a cap lower bound when double counting is also present.

## Concrete unsatisfied obligations and next structural choice

This finite joint proposal fails simultaneous H/V ownership: picking a horizontal interval before actual vertical ownership causes2290 later extensions to collide, even with M5 available. The next selected structural mechanism must jointly reserve the real branch topology and both horizontal/vertical intervals, and shorten complete local branch paths rather than forcing all contacts through one extended H trunk. Where actual native cap still requires a genuine drive buffer, its native input load, functional polarity, real site/PG area, output cap/transition domains, all upstream waveform/setup/hold and clock budgets must be priced together. No buffer remedy is claimed here because complete legal ownership, exact via fringe and native timing remain unknown.

All native pin/via access, full signal DRC, current native PG contact/conductor/short proof, candidate clock structure and root load, source slew/setup/hold, true parent phases and small-window density review remain HOLD. No new physical grant is requested. This packet supplies a concrete source rejection and obligations for ROOT's next structural choice.

Reproduction consumes the byte-pinned native exports under /home/ubuntu/artifacts/hidx-joint-source-model-1019/input (pre-run SHA manifests), existing generic strict collector dependency from c74808561, and immutable predecessor148b geometry/verdict under /home/ubuntu/artifacts/hidx-exterior-construction-1019/output. Those already preserved large inputs are referenced rather than duplicated in this artifact-only commit. Native Liberty image remains sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29.
