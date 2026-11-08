# CODEX SVC softmax folding 2026-11-08

CODEX took over missing R5 softmax 2:1 arithmetic on codex/svc-sm-0222. Own source intel1:/srv/opentallas-scratch2/claude/codex-svc-sm-0222/repo (base includes compiler a8175d573b).

## Design
Preserve sixteen logical score lanes and their golden reduction order. Eight physical multiply/add/exp pipelines each retain two independent score histories and maxima. Pair their outputs back into the original sixteen-lane vector before unchanged SMC/SMR. Four physical divide/RoPE pairs retain two logical pair counters/cosine stores and rebuild the original eight-pair vector. ot_s81_su_sms LANES defaults16; only LANES8 selects folding. SE assembler guarantees input rows at least4cycles apart. H8 compiler SO operand rows change to spacing2; no ready/credit queue introduced. Denominator held until final all-head SO.

## CODEX notes
- Original H8 predecessor changed attention width but left full16lane softmax arithmetic. It cannot claim R5 area fit.
- Initial scalar proof build failed syntax due missing whitespace at a numeric literal/ternary; corrected.
- lane_base_r1 exp event data matched, but max scoreboard assumed reference event arrives first and failed when optimized folded max arrives earlier. Separate asynchronous max queues correct that bench assumption; lane_base_r2 now runs.
- divide_base initial miter compiling. Its source snapshot predates per-context fault-bit correction; no final proof credit from that build. Recheck with corrected source after terminal.
- Conservative estimate: shared physical leaf arithmetic same as original~88.7k SML/~57.7k SMD plus duplicated small history/state; expected below150k each. Actual synth/physical release NOT RUN.

## Next
Collect leaf proofs and context-swap/stale-den mutants; run one full real head arithmetic miter to price fixed latencies; publish own branch. Coordinate LANES hookup with svc_rtl and H8-only SO valid bubbles/SOT dates with parent compiler. No plan adoption, P&R, merge or tag.

### 02:4x result
Published WIP abc8340852 to hub codex/svc-sm-0222. lane_base_r2 PASS110 comparisons (both contexts maxima and exact e data/flags, four repeated jobs). divide_base PASS96 vectors preliminary; fullhead uses final per-context fault vector. Active fullhead gate: intel1 ot-run unit85117-1794134363, head_base/,24GB4threads. Active mutants: lane_mut_ctx (MUT1 swaps context memory destination) and divide_mut_stale (STALEDEN1). Final area and P&R NOT RUN. E vector cadence is2cycles; end-of-E and denominator/PIO must be repriced from actual integration, not inherited H16 constants.

### 2026-11-08 03:16 PST actual gates and one physical pilot
Published hub codex/svc-sm-0222@1ababd922b: original SMS default byte-identical to c477959f3c; separate folded SMS top. Fullhead arithmetic PASS148 ordered E/SO/DEN comparisons at nv1/8/40 (production640score positions), intel1 unit85117-1794134363 exit0; contextswap mutant CAUGHT106 mismatches and stale-den CAUGHT64. Folded behavioralSMH DOP2 firstE lastscore+103, Erow interval2, firstSO firstPV+52, DEN afterlastscore148/177/256 fornv1/8/40. NativeSU_SMU_T service/calendar timing remains unqualified; parent/RTL lead hold calibrationfalse.

ActualTT833RVT sizing: pairedSML99,978cells/12,411flops/11,268.96948um²; pairedSMD62,884cells/7,553flops/6,834.84156um². Eachbelow150k. Eightplusfour total1,051,360cells/117,491.12208um² beforeunchangedroot/tap, about44percent reduction versusold~1.879M (notexact50percent). BothYosysCHECK0problems; source-pinned stat/check receipts onbranch. Sizingfrontend/packaging failures closed: ORFSmkdir/SDCcopyrace fixed byprecreatingdir; wrong bareSYNTHESIS corrected to-DSYNTHESIS; missingTC_LIB_FILES corrected toTC_NLDM_LIB_FILES andODBpackingreused mappednetlists (bothpackunits775398/775431 exit0).

Root explicitly authorized one conservative leafPLACE independentoffullR5proof. Selected pairedSMD155.52square,4.32margin,measuredcorefill31.7percentbefore301faceflops,15percentclock/channelreserve,M6,pd0.40,clock/resetcentroid. Actualgeneratedpins/PDNimageVIEWED /tmp/codex-smd-review-0222/preplace.png; committed results/geom_review/svc_sm_fold2_pilot_1108/preplace.png+review.json PASS_CONDITIONAL_PLACE_ONLY. PIN CYCLES +1RX/+1TX inpilotface shell only (notadopted intoR5).
RUNNING: intel1 /srv/opentallas-scratch2/claude/codex-svc-sm-0222/pilot_divide_vA2/ot_s81_su_smd_fold2_pilot_vA, unitoth-ubuntu-1073999-1794136301, GOALplace,32GB8t; run_place.logcurrentlyYosys/ABC andinlineLECwatcher. HOLD_ROUTE+DO_NOT_COUNT. Firstgeneratorpartialpilot_divide_vA failedonlyownPythonimportpath forface_shell; correcteddriver andfreshvA2kit, noP&Rretry.
NEXT: collectLEC+PLACE; renderactualplacedODB density/pins/PG, VIEWimage anddiagnoseallsmells beforeanyCTS. NoR5parent/PORchange, no merge/tag/deletion.

### 2026-11-08 04:0x PST local control re-form
Baseline leaf PLACE failed geometry, preserved on canonical intel2:/home/ubuntu/OpenTallas codex/svc-sm-local-0222@334164c855. Measured 54,733 placed cells / 6,182um2 / 29% core util; peak density0.435, no bins>.7, pins8.4% track use, clock entry2.98um from actual sink centroid. FAIL smells: global reset spread273.5um/fanout308, quotient MSB139.8um/51, pending106.2um/130. Actual layout+density PNGs VIEWED, no CTS/GRT/route. Mapped LEC now EQUIVALENT 9532/9532, no differs or undecided.

Fresh source-specific re-form: six kept same-edge reset sources and localized first consumers; four kept serializer word-group phase copies; five kept quotient-normalization copies per divider. Original shared RTL and previous passing baseline remain unchanged; 0 mission cycles added. Paired divider arithmetic PASS96, same-edge/fractional-reset witness PASS16016, control mutant CAUGHT1001/16016. Proof logs and old failure images committed. New local source files and two generator/hook files are opt-in; not yet integrated into production folded SMH.

Fresh form estimated area7134.84um2 (original measured area+300 reserve), estimated63,884 cells, 155.52um square / 4.32 halo / core fill33.1%, M6. Control-only bands are nonexclusive and fit <=92um W+H; reset roots clustered near clock centroid. Actual fresh pin/band PNG VIEWED and review results/geom_review/svc_sm_local_pilot_1108/preplace_review.json PASS_CONDITIONAL_PLACE_ONLY. New PLACE through ot-run32GB8t on epyc4:/srv/opentallas-scratch3/claude/codex-svc-sm-local-0222/ot_s81_su_smd_fold2_local_pilot_local_vA (copy then admission); HOLD_ROUTE+DO_NOT_COUNT. Source kit generated on Intel1 from3969c606f4; canonical branch latest334164c855 adds review only. Next collect new measured area/PLACE renders and act on all smells; no unchanged retry.
