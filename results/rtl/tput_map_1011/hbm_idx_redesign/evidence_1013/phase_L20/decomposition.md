# Verified native L20 phase decomposition

The observer run finished HGI_E2E PASS. Its entire 106-record output file is byte identical to the original exact BASE output, including dispatch/retire and checked-word counts. Completion remains 21194 doorbell cycles; INDEX is 1872 cycles, 3756/3756 exact, final VM/HBM mismatch0. The linked model/archive/header hashes and observer source hash are in provenance.json. The original compiled RTL archive was unchanged; the separate observer archive renames its unused original main symbol.

| Sequential endpoint interval | Start → end cycle | Cycles |
|---|---:|---:|
| Dispatch through last selector query block | 2944 → 3175 | 231 |
| Query delivery through all four scorers loaded | 3175 → 3218 | 43 |
| Loaded through first selector score issue | 3218 → 3350 | 132 |
| Score issue window | 3350 → 3535 | 185 |
| Last score through first candidate output | 3535 → 3786 | 251 |
| Candidate output window | 3786 → 4774 | 988 |
| Last candidate through record retirement | 4774 → 4816 | 42 |
| Total | 2944 → 4816 | 1872 |

These intervals partition the record endpoint exactly; labels do not claim that one internal mechanism exclusively owns each interval. The loaded→score interval includes native binding, DRAM/model and registered score delivery (model LAT104/LEG24); this trace does not independently isolate the first DRAM request timestamp. The score window has171 nonzero fire cycles. The candidate window has683 accepted beats across989 inclusive edge samples, hence306 gaps. PK D credits are zero847 of1873 inclusive frame samples, but selector candidate credits are zero only4. Thus downstream PK credit starvation alone is not proof of a critical-path loss: the native candidate producer itself is paced. The WP credited-landing fix's172-cycle gain is from a saturated synthetic source, not this native producer.

Other measured milestones: adapter go2950, query weights ready2968, selector FS landing2953, first query block2970, last query block3175; PK done4786, flush4802, WP FIFO/packet drain idle4813, record retire4816. Old L20 had2717 mismatches OUT OF3756 checked words; the corrected ascending-block-ID golden is the same1366(id,value) pairs and now all3756 match.

TOPK route.top6 is separately dispatched18297 and retired18484 (187cycles, six words exact). TK2 read/insert state3 spans18304→18441 (137cycles), tournament state7 spans18444→18468 (24cycles), final write/drain state15 spans18474→18483 (9cycles); state transitions are preserved in summary.json. The state names come from ot_hgi_idx_tk2.sv; these spans include any stalls in those states. No unit price was changed.

Prepared next structural design task: PROMPT_IDX_ORDERED_CANDIDATE_CODEX.md in the takeover directory. Stream actual scorer block maxima into ordered quarter buffers and serialize global block IDs; reuse closed selector/scorers, disable their legacy candidate path through its existing FS mode, and combine completions. This remains a proposal requiring exact composition and production proof, not measured throughput or accepted cost.
