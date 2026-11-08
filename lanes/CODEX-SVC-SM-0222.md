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
