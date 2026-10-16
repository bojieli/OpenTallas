# Q-PORTMAP b2 source and component qualification

Active Codex continuation, 2026-10-16 09:25 PT. The 08:35 hand-back was superseded by the owner's correction: Claude remained weekly-limited. The earlier physical-wrapper failure was a bench LC alignment defect, corrected without changing the DUT. Its failed artifact is retained.

Source ABI is pinned at `1c8974782`: six homogeneous per-side ports, six GP4 halfbands and eight independent NL2 upper leaves. Eight actual 65-bit outgoing lane-pair faces and eight independent 194-bit returns preserve every valid/use copy. No old GP8/BANDF1/NB3 hard view qualifies the new source. The actual TP8 target has 3,072 groups and 16 lanes, with nonempty output splits 7–11. Split 12 is empty and the b2 scale compiler rejects it for production output.

## Completed evidence

| Gate | Evidence | Result |
|---|---|---|
| Primary physical-source composition, eight NL2 roots, real hold SRAM, LNK2 | E4 unit oth-ubuntu-25950-1792167375; evidence/primary_l2_pass.log | 330800 words, 20675 groups, 2324 operations; splits 7–11 each nonempty; all 16 lanes; same arithmetic as flat tree and original bands; parent station delta 4 against direct model |
| Independent return-status negative | Same immutable binary, +BREAK_RETURN; primary_l2_return_mut.log | Dropping only upper7 return-valid causes the expected finite-phase fault; no data mutation |
| All eight upper fault paths | Primary finite and all-lane NaN phases | finite faults zero; all eight upper fault copies observed after NaN injection |
| Direct arithmetic mutants | direct_mut1/2/5.log | wrong half pairing, wrong upper pairing and wrong compiler frame rejected |
| Actual physical GP4 lane mutant | wrapper_pair_mut.log | wrong lane5 pairing rejected (2216 word errors) |
| Actual controller/port frame functions and QOTS_SMALL address path | AGI unit2260565; frame_pass.log/frame_mut1/2.log | 576 checks pass, real controller and port BANDF1 mutants fail |
| Actual result leaf and hard multiplier | AGI unit2275370; port_pass.log/port_mut_frame.log | 138 operations/writes including zero masks; 6072 edge comparisons; original and new results/rows/masks/addresses/argmax match; wrong physical index rejected |
| Released scale cohort reframe | E4 unit4169438; released_scale_b2_receipt.json | all3072 actual ROM IDs across8 ranks and1184 program records checked; payload/program bytes unchanged; physical active-slot map bijectively reframed |

The result-leaf proof drives declared tree/ROM-column boundaries; it does not establish complete ROM-to-port execution. Q-B2-JOIN owns the separate actual controller-to-six-restored-port proof with 384 real released ROM models and 384 hard FP multipliers, plus the production PAR3 train/VM calendar. The shipped native961w workload uses eight consecutive captures. The simple qfd_res_ser_half_b2 and its 24-edge-spacing bench remain diagnostic predecessor evidence only.

Both actual controller and port use BANDF2 with TCUT7. The upper arithmetic primitive alone uses TCUT6 to express GP4 local levels8–9 and upper levels10–11 with original operand order. QOTS_SMALL uses the same four-position decomposition. ROM_BAND/ROM_HALF select simulation identities; the dense released payloads are replicas, not requantized or permuted data.

The per-half wrapper restores tc341/ty2048 input and cw2050/rq2213 output stations, retaining am52. A distinct kept result_status_v FF captures local_result[2212] at the rq output edge. Explicit parent register subsets total40254 versus39189 in the old three full ports: +1065, not a large FF saving. The port source root has lower bound8913 sinks; actual synthesis/CTS is still required. Native word valid/fault and result valid need separate compiled same-event padding and real fault delivery.

`fullshape_cost.json` is source-shape and candidate-rectangle accounting only. Tree adders remain352. Fixed 128x256 SRAM padding increases mapped hold/wait macros192→288 (+96; +0.373591 mm² macro footprint). Candidate halfband/train/upper rectangles add0.825083 mm² before status collector, channels or mapped packing. Eight upper candidates are each86.4×205.2; their explicit data-flop lower bound is6720/root before adders/control. These are not routed area or CTS measurements.

The compile contract for each actual parent lnk is F+R=2*L across all eight real return paths, where F/R count external registered transport only; parent lnk=L, internal leaf receives L+1 for the two parent stations. Odd sums need a real pad. GP4 parent L<=54. Selector reaches upper at band c+3+F before upper DLY1. LNK2 here is a measured component configuration, not a die-wide production constant.

Q-COMPUTE-DIE owns the actual source-complete graph and relay allocator, candidate grants and adoption. Historical64 stages/op,2.7% and0.3–0.6mm² estimates are superseded/unqualified. Native full-token fixed-cycle proof, actual allocator price, TT setup>=0, FF hold>=0 and DRC0 remain open. A new source-specific upper kit uses the formal assigned pin/slot artifact; synthesis/CTS is live and no inherited physical view is used. Its legacy26-bit selector ABI has only four consumed bits, awaiting actual mapped census and coordinated source specialization.
