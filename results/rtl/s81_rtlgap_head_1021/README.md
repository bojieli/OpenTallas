# S81-RTLGAP/RG-HEAD: head producer binding and MTP draft transport (10-21)

Tree lines: TOK.DS.BENCH.4.1 (head producer in the die) and TOK.DS.BENCH.4.3 (MTP draft body/seed transport).
Base: the 72-frame MU die RTL `claude/s81-die72-g3-1021@4ee613834`. Branch `claude/s81-rtlgap-head-1021`.

## 4.1 What was missing

The head producer's arithmetic chain was already proven in pieces: the final FFN POST (9b2e70333, all 80 VS13 to VP POST
to VN beats PASS) and the vp NORMR / vn / xfin / vq norm sequence (beat bench g_b37). What was missing in the die was the
link between them and the head. Three items:

1. **Head gain source.** The head-norm gains (64 FP32 per leaf) had no row region and no writer. The GAIN rows 64..79 lie
   inside VPX, which the allgather overwrites on every layer.
2. **pre1008 lifetime.** The final head must use the same token's final-FFN pre row (G-unit row 1008), not attn row 1000.
3. **No path off the die for the normalized x.** vq sends the 80 BF16 XB beats with the line default hop counts, and
   a line beat with hops 1 is delivered, never forwarded. So no XB beat could ever leave the stage die. PRODUCTION_BINDING
   item 6 asks for exactly one gather path.

## 4.1 Design (decisions)

- **Placement.** Head hc_pre and norm run on the final stage die, which owns h after POST. Only the 80 normalized BF16
  beats (10,240 B) go to the head die. The alternative was to send h (40 KB) and build a vector plane on every head die.
  The chosen placement is the PRODUCTION_BINDING chain.
- **Gains (`leaf_rows.HEADG` 480..495, BOOT-resident).** The gains are written once at boot by CTL target-5 row writes:
  16 rows per leaf, 1,280 CTL beats in all. This uses the existing xr row-write path, so no RTL changes.
  `lower_head.py boot-gains` emits them from the released 5,120-word FP32 head-norm weight. HEADG has no other writer.
  - Rows 448..463 were not usable: they hold the final FFN combined rows (`final_ffn.COMBINED`). They are now registered
    in `leaf_rows` as FFNC so the regions are checked as disjoint.
- **pre.** NORMR uses a0 = 1008 (GU_FFN), the final-FFN HC pre row of the same token. Its lease runs from the G-unit L5
  write to the last head NORMR read. The next token's attn HC writes row 1000, never row 1008.
- **Egress: `ot_s81sl_rstop_xo` (new leaf) in `ot_s81sl_xg_xo` (new; same ports as xg).**
  - The flag is header bit [20] of an XB beat, which is bit 7 of vq's global beat index (vp a1[7:0] goes to vq m_i at
    [20:13]). The compiler sets it only on the head norm's NORMR, with a1 = 128 + 5 sid + k. vp and vq do not change. The
    gather index [19:13] is unchanged.
  - Only sid 1 (s_0N) forwards a flagged XB beat. That covers a beat delivered from the E line with hops 1, an own beat,
    and a V-assembled beat. The beat goes out on ro_w with hops 1, to lep pair A. That is the stage NEXT circuit in the
    G4/LINK5 circuit plan, and the head die is the next stage after the final stage.
  - Each of the 80 beats reaches s_0N exactly once.
  - The beat crosses in one 80-beat lep MU TX window (lep and dsdv_mu_land NB 80). The window stamps the {user, pos} tag
    into [1077:1045], which an XB beat leaves clear. A stale beat with the same index is therefore rejected at the head
    die's landing. Admission is exclusive and static: the window is opened only for this phase.
  - The egress adds 0 edges.
  - A collision with another ro_w source, or two egress sources in one cycle, is a sticky fault. It is never arbitrated.
- **Programme (`tools/s81_dv/layer_prog/lower_head.py`, family plugin for `head.hc_pre` and `head.norm.*`).**
  - Per tier: one GAIN (a0 = 480, tier slice mask), then per slice 5 NORMR and an XFIN_GO.
  - Size: 98 CTL rows and 98 templates, which fits in one job (100 calendar rows with KIT/END).
  - The CTL arrivals agree with `row_ctl_events`.
  - Compile smoke on the compiler's die of record: OK.
  - Status: PARTIAL.

### Safe-design checklist (rstop_xo / xg_xo)
1. Pins: unchanged; every rstop input lands in a flop and every output leaves one.
2. Reach: unchanged (inside the xg tile).
3. Fanout: the new selects xl / xo / xa drive the 1,104-b ro_w mux exactly as the existing fw / ow / aw do. They need
   the same kept-copy treatment as the closed rstop, which has none of its own. Waived as identical in kind.
4. Depth: +1 mux level on ro_w.
5. Storage: none added.
6. Floorplan: an xg re-gate is owed for `ot_s81sl_xg_xo`.
7. Clock: one region; unchanged.
8. Schedule: static, 0 cycles added. The s_0N egress slot rule is stated below.

### Evidence
`rstop_xo_bench/`: Verilator 5.050 on the fleet (ot-epyc5, unpinned ot-run).
- The existing 16-strap `tb_s81sl_rstop_sid` passes on the variant: 144 checks.
- `tb_s81sl_rstop_xo` passes: 138 checks. It covers egress rules E1..E7 on 16 straps, and a 16-stop die ring with
  S/N lines and V rungs. In the ring:
  - 80 flagged beats leave s_0N ro_w exactly once each, bit-exact.
  - Nothing appears on s_0S ro_w, s_7S ro_e or s_7N ro_e.
  - Every stop still gathers all 80.
  - 80 unflagged beats produce 0 egress.
- Mutants xooff, xoall and xonoflag fail the xo bench; tiercol fails the sid bench. Witnesses are in `check.json`.

### Open (not closed here)
- **Per-layer die bench.** `dv_layer_compile.Die` is still the p4l bind9 model, and it refuses the G3 xr (XR1F SHA not
  in `xr_timing.QUALIFIED`; XR1F adds 0 cycles). The head producer is therefore compiled on bind9, not on the 72-frame
  netlist.
- **16-slice NX/XB composition timing (GAP_NORM16, shared with every layer norm).** rstd and the per-slice XB emission
  edges are plan values. The composition must also keep at most one beat per cycle on s_0N ro_w: a line delivery and an
  own or V-assembled beat in the same cycle is a fault. If the composed timeline cannot meet that, the fallback is a
  10-beat SRAM merge queue for s_0N's own and assembled beats.
- **Consumer: the head die (S81.HEAD), which has no netlist.** The LM head (TOK.DS.LAYER.5) cannot run on the 72-frame
  die because it is not in it. The existing interim measurement is still `head_tp4_interim.py` (641239174).

## 4.3 MTP draft body / seed (design; no new stage-die RTL needed)
- **Body ownership.** DSpark blocks mtp.0..2 are three more transformer layers. They run as three more stages of the same
  72-frame die type. Stage and die count come from the qualified capacity (LEAD-S81 chain72), and `dv_layer_compile`
  already selects `mtp_draft`.
- **Seed.** The draft input is the main model's raw final h (pre-norm; MTP applies its own hnorm). It travels to mtp.0 as
  a normal stage hop: 320 beats on s_0N pair A, the LINK5 NEXT circuit, with the existing `lower_hop` and LINK5
  calendar.
- **Draft body output to the draft heads.** This is the same 80-beat flagged-XB egress, through `ot_s81sl_rstop_xo` on
  the mtp.2 die.
- **Markov and draft-seed rows.** These belong to the head die (ot_dsrom_markov_row, `mc.mtp_seq.draft_chain`).
- **Circuit decision owed to LEAD-S81.** The final stage needs two outbound paths: x to the head die and h to mtp.0.
  Each rank die has one NEXT circuit. Proposal:
  - Rank 0's NEXT goes to head die 0, which then broadcasts x to head dies 1..3 over its TP circuits.
  - Ranks 1..3 send h to mtp.0 ranks 1..3. mtp.0 rank 0 takes the replicated h over its TP circuit (s_0S A from rank 3).
