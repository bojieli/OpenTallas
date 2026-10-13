# Strict CTR input capture: physical and stage specification (proposal only)

Current tuple: NG256/D5120/NCOL3/GS8/S_RD2/S_RT4/ML5/AL4/CHAIN_STEP6/READ_STAGE1. CTRA and CTRB slots remain576.72x21.6, M5 signals/PG, M4/M5 pins. Old a9 jobs failed GRT; neither view is CLOSED. Historical raw-port boundary cones remain453/793 endpoints through4/5 levels. This proposal adds real pure input captures, never raises density/cap or relaxes SDC. No RTL change is authorized here until root coordinates POST express and fit.

## Timing constraint and robust solution

Let E0 be the edge that stores a return request in CTR rdq. In the current proved3c implementation:

| Event | Edge |
|---|---|
| CTR packet pin flops; rq_q reflects rdq | E0 |
| CNL rq/hs input capture; CTR rd2/rv2 origination | E1 |
| CNL registered hrq; READ_STAGE1 metadata relay | E2 |
| CTR OR/insert and rdm/rvm merge flops | E3 |
| ctrn registered return face | E4 |

The existing READ_STAGE1 relay is already required to align metadata with the added CNL request capture. It cannot instead sample raw hrq at E2: that edge would capture the previous request's hrq. Moving merge logic into ctrn before its output flop would violate ctrn's own pure input-boundary rule. A larger fused block could share the capture/merge stage but changes partition, ABI and cuts; it is excluded from this no-ABI proposal.

Robust independent-leaf implementation: retain READ_STAGE1(E2), add PIN_RETURN1 coherent metadata capture at E3 alongside raw hrq pin captures, then merge at E4 and ctrn output at E5. Request timing/state stays unchanged. Throughput remains one packet/cycle; one return latency cycle is added. All sideband/status bits in the packet are captured with its metadata. Each independent local flag is captured before its OR, shifting its event by the same one cycle. DS remains ML+7*CHAIN_STEP=47; mixDM18 and scaleDY11 remain unchanged.

Forward HOP_F=2+RLY=4. Return HOP_R=2+RLY+READ_STAGE+PIN_RETURN=6 (current5). Let shortfall=(NP-L1)*(HALF?2:1)=2 at production and NG64. Forward padding stays HOP_F*shortfall=8. Return padding becomes HOP_R*shortfall=12. Thus RP=RT+2+(2+RLY)*shortfall+(CNL_PIN+PIN_RETURN)*shortfall=15 when RT1 (current13). RET_EXTRA changes1->2, adding TWO centre return-only cycles; never change forward FP or DS47.

## Relocate control epoch without another latency cycle

Cth currently feeds ctra/b fv_local/fdx_local[103:0], which are one-cycle captures of ctfx's fv/fdx. Feed raw ctfx fv/fdx[103:0] to the CTR input boundary instead and place those exact111 capture flops inside EACH CTR leaf. Drive every internal command reference (ng_v/hs_v/u_q including n_hs/n_cs/n_gs/rh/sc_run/vs/vy) from that local captured bundle. Ctpl continues to receive cth fv_local/fdx_local to preserve its PB/hpr pairing. Cnl continues its own full/specialized command capture. Do not delay rv_in/rd_in before their existing packet pin flops, and do not change rq_q, hs_run or hs_c generation/output epochs. tid8/last1 and rst_in already enter local configuration/reset flops; clk is the clock pin.

## All raw input capture counts and store lead

Counts are conservative additional clocks before synthesis pruning. S_RD2 gives fv7+controlfdx104=111. Raw hrq_n/hrq_s are1024+1024=2048 bits per leaf. yb_n/yb_s are128+128=256. CTRA has cs128 and independent flags nflt16+hnz8+pflt8+hov1=33; CTRB has no external cs/flags (those inputs to its shared internal core are constants). All of these captures are direct wires into flops, with data reset unnecessary and validity reset mandatory.

Pure cs/yb pin captures would shift storage writes one edge. Reuse existing store-to-origination lead to keep external event readiness unchanged: capture yb_q at the original ybuf-write edge; write ybuf on existing y_d1 and a new delayed yi8 index. Keep oq_rdy's increment from y_d1 at the same edge as before; first packet origination is the following edge, so newly stored ybuf is ready. Capture cs_q at the original psb-write edge; use a new delayed vs[DS] valid and existing po_i to write psb on the following edge. Keep po_v/po_i origination unchanged. This is safe only after proving no selected ybuf/psb read precedes the delayed write; add stage assertions and full golden/mutant gate. Do not use po_v as the CS write enable: it masks non-last tiles whose psb is needed when the packet returns.

| Leaf | Existing READ1 conservative bound | Direct raw captures | Extra store index/valid | Bound |
|---|---:|---:|---:|---:|
| CTRA |7128|111+2048+256+128+33=2576|yi8+cs_valid1=9|9713|
| CTRB |6186|111+2048+256=2415|yi8=8|8609|

The extra coherent E3 metadata capture adds1140 CTRA and conservatively1268 CTRB clocks, so final bounds are10853/9877, still below15000/root. Bounds intentionally do not subtract replaced/reused registers. Measure actual area, placement and clock load at576.72x21.6 before route; these estimates never waive the60% admission criterion. Existing direct rv/rd pin registers and tid/last/reset capture are included in the starting bounds and remain intact.

## Centre pads and hard-master reuse

Keep the parent split forward F13 leaf and four return R6 slice instances (two1078-bit payload slices x two6-cycle stages), i.e. current12*2156 return data clocks. New centre delay14*2156 must append one full-width2156-bit R2 leaf (4312 data clocks plus its reset), instead of widening R6 to R7 or increasing a root beyond15000. Current CCR core14718 clocks stays untouched; existing528-bit metadata2 leaf1056 clocks is instantiated TWICE in sequence for metadata4. Flags/PI/export nodes and crd data must get the same extra2 cycles. These are new leaves requiring M5 views and closure; no old-view alias. Production zero-depth/empty-centre soft cases must continue to work without fictitious hard R0 macros.

## Pin plan and route proof

Use the current physical slot and registered ABI; no new output bits. Spread normal control/packet ports on-grid, but group hrq by actual producer lane columns, not merely aggregate bit order. For hrq_n/s each128-bit group index n=0..7, column=n%4: groups n=l and n=l+4 share column l at x0/144.72/289.44/434.16. Uniform aggregate bank-major spreading alone can send bank1 lane0 towards the east side and recreate old horizontal congestion. Place raw-data input flops near their matching N/S faces; colocate OR/mux logic with those groups and register outputs at the return face. No output unregistered bypass. Input captures are the structural fix; pin grouping supports that structure.

Validate the minimum full HC composition containing CNL_PIN1/CHAIN_STEP6/LANE_SPECIALIZE1/PIN_RETURN1/RET_EXTRA2 and parent split pads, with all request/data/index/flag/store-lead epoch assertions. ProductionNG256 m0 must pass all rows, mutant1 must fail numerically with completed jobs; reducedNG64 m0/mutant3 provide the first cheap stage proof. Record measured cycles against the published budget; POST express must coordinate these timing changes rather than adopt stale gate records. TT>=0, FF>=0, DRC0 and child_lint/current caps remain required on every changed/new leaf.
