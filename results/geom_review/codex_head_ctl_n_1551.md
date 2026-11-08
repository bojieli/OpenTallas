# CTL_n private conservative vC source and plan review

Status: SOURCE/MODEL READY; no new physical kit or P&R. No POR update or count claim.

Baseline: actual routed hd_ctl_n vB on intel1, /srv/opentallas-scratch2/claude/dh77w/hd_ctl_n_vB/s81_head/l48uj/items/hd_ctl_n/gen/hd_ctl_n. TT setup -42.58/29, FF hold -33.30/72 (69 input-port, 3 internal), slew TT964/FF628, DRC0. This is a large miss, no ECO.

CLASS: writer START fanout plus long weakly driven FT segments. Exact final netlist identifies the153-load net29017 as a BUFx10 fed from cland_fstart_in_w3d_i, driving write-slot gates; it is not a read-selector net. Native routed segment examples: BUFx3 -> FTw3u_s2.q62/D197.8um, slew521.44ps; w3u_s0 INVinput199.93um/515.43ps; w3d_s1 INVinput189.46um/511.99ps; unit_ft INVinput191.56um/491.31ps. Existing max-wire200 worked geometrically but is insufficient at TT. Original failures preserved.

REDESIGN:
- Optional WRITE_TAIL=0 and READ_CHUNK=0 preserve the default. Opt-in writer8/read32 supports nondivisible515/517 widths with bounded final slices.
- Optional local_chunks.tail=1 protects and clamps last writer/read selector groups. Existing placement keys retain their old behavior when this field is absent/0.
- Conservative private source uses WREG1/FREG1, writer8/read32: input data +1 cycle and receiver K+2 on w3u_i/w3d_i.
- FT w3u/w3d5->6 and unit_ft1->2: +1 output PIN cycle each. End-to-end change w3u/w3d+2, unit+1; rate stays1 word/cycle. Input and output obligations are separate.
- +2758 FFs estimated: core1202, forwarded1556. Same1296x708.48 slot. Native currentUO generation is required; no oldUJ plan/sidecar reconstruction.
- Preserve currentUO GPIO coordinates and layers. Use native OT_CONS_KIT=1, OT_CONS_UTIL=0.35, OT_CONS_MAX_LAYER=M6: gen_phys retains M7 pin access and records the exception in cons_kit.json. M6 is a requested body ceiling, not a claim that every signal shape is below M7. Audit native pins and actual routing-layer reports. The earlier M3 repin proposal is superseded and unbuilt, not active interface debt.
- Explicit legal-site plan estimates w3u max289.008um and w3d281.903um registered hops. Unit registered hop351um requires explicit <=100um repeater segments. At the unavoidable fixed-boundary-order crossing, a100um corridor has1028 data wires versus3645.8 horizontal tracks on M4/M6 (28.2% raw use);50% reserve retained. M3/M5 handle vertical directions.
- Existing HEAD450/342 clock reference retained. Actual PLACE/CTS sink census, clock insertion, related-pair timing, density and GRT overflow must be reviewed before route.

Images viewed: native routed review_vB/paths.png and density.png; proposed diagram codex_head_ctl_n_1551_plan.png. Sparse diagonal banks and boundary clumps are visible. The proposal is an estimate, not a placed image.

Minimum exactness:
- Same-cycle ring default-off/tail proof:24cases/94440checks, widths1/31/32/33/64/65/515/517, WREG off/on, phases0/2/4, constant tails and repeated resets/K changes; writer/read mutants detected.
- Actual vB CA reference, conservative FREG/WREG versus off with K+2 and +1 output word: widths515/517/615, each11520checks and1232ready-word comparisons,0errors; both WFALL modes; constant tail517; FREG mutant detected by readiness loss.
- Native ot_dp_st FT +1 output proof: widths514/512/45,11971fullword/tag/epoch comparisons, asynchronous reset cancellation; data/epoch mutants detected.
- Full private wrapper and default unstrapped CA Icarus frontends pass. This is not full-kit LEC; new kit LEC remains required.

FF internal starts diagnosed read-only on original SPEF: lw statusrelay.ready->agg1.ready -27.24ps; lep_fault cland.ready->lepf statusrelay.ready -25.32ps; unit/lw statusrelay.ready->up_unit.ready -7.46ps. Current supported input-start-only nonport repair should repair these and leave port starts to the parent. Never pad the input-port hold paths.

Next: coherent currentUO native generator with matched plan f140216c876b/sidecar90d006a48f17 and rederived START metadata ab676a5452ab; native unchanged-pin audit and conservative access-layer report; source/placement metadata coupling; one PLACE with HOLD_ROUTE + DO_NOT_COUNT; actual images/full LEC; then CTS/GRT and final qualification/pricing. Old retained SYNTH/FP/PLACE/LEC footprint1.412GiB supports an8GB bounded PLACE disk request under unchanged guards.
