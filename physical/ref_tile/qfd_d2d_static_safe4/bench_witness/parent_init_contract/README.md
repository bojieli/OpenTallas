Parent reset/first-use ancestry: missing production precondition, no qualification

Source examined: /home/ubuntu/scratch/qw-l1seam/dh2/{die.v,die_glue.sv}, old GEN0d4c; exact hashes, trace instances, driver graph and extraction log are included. This old GEN instantiates qfd_d2d_static, not the current physical qfd_d2d_static_ovl PR1/RC1 candidate. It supplies ancestry evidence only. No timing or placement rerun occurred.

Actual clock ancestry: d2d_rom.ck and sys_face.ck both use n_clk_d2d, driven by clk_rx.pll_d2d. The glue assigns pll_d2d=pll_fwd; ckb_rom qfd_ckbump produces n_pll_fwd and n_rst_fwd. qfd_ckbump is expressly a HARD-MACRO MODEL in rtl/qwen_split/qfd_link_slots.sv. Its simulation initial #RST_NS20 and HALF_NS0.41667 behavior does not establish a production package POR pulse or clock-running guarantee.

Actual reset ancestry:

- ckb_rom.rs -> rs_bump qfd_rstsync.arst_n; rso_d=n_rst_d2d. qfd_rstsync has asynchronous assertion and two-stage synchronous release.
- D2D por_n: root sync2 plus four forwarded-reset stages, ending at n_rst_d2d__r4.
- D2D rst_n: root sync2 plus three forwarded-reset stages, then four reset-replicator nodes (PAD0,0,8,0 in source-to-sink order), totaling16 further ordinary rising edges; sink n_rst_d2d__fo1__r3__t5. Total ordinary rising-edge stages18, plus actual forwarded stages3.
- SYSFACE rst_n: root sync2 plus four forwarded-reset stages, then eight PAD0 replicators totaling16 ordinary rising edges; sink n_rst_d2d__fo2__r4__t24. Total ordinary rising-edge stages18, plus forwarded stages4.
- Every reset-replicator D/clock and relay input/clock is in the JSON. Plain replicators are unreset and require actual root-level flushing. Forwarded reset stages alternate source/lane clock polarity and land on receiving root; stage count is not automatically an integer root-cycle delay. The actual native clock/phase receipt remains required.

Actual first legal inputs:

- SYSFACE is the actual producer of cfg_tx_we via four forwarded-data/landing stages; cfg_rx_we, cfg_addr, cfg_data, cal_start, cal_seg and result_v each arrive through three stages. This old unequal cfg_tx_we path is not qualified as the current production binding.
- The examined SYSFACE source has a three-edge regional release: rr_s[1:0], then rr_q[4]=rst_loop. Its u_cseq reset is rst_loop; u_cseq is the declared single cfg/calendar producer. It writes all32TX+32RX table words, then both segment bases, before cal_ready. Initial cal_start is reset0 and remains0 through init. Actual caller/image/port ages must be joined, not inferred from an unrelated standalone sequencer bench.
- D2D wrapper PR1 input flops, including cfg_data/addr and cal_start, are unconditional unreset captures; many output valid pin flops are unreset too. There is no generic production boot_armed fence at these boundary outputs. The D2D core's ot_rst_pipe has2plain regional stages following its2async-input stages; it requires clocks during reset. Calendar seg1/table and SRAM data are unreset. Defined configuration/slot-write lifetimes, rather than zero values, must establish their eventual observability.
- The source-pair startup proof shows all copies converge within3legal edges (unreset608/92/32 at1/2/3). It does not prevent early divergent copies from perturbing original state or storage. A source-correct cold protocol must keep every observation invalid and initialize every subsequently read word/state after those possible perturbations.

Explicit missing parent preconditions:

1. Actual production POR/reset assertion, running-clock and native forwarded-lane phase contract; a simulation pulse or testbench repeat4 is insufficient.
2. Actual current OVL candidate binding, with source hashes and exact reset/producer data ages. Old GEN0d4c cannot supply this.
3. A defined observation boundary held invalid until regional reset has asserted, all relevant copied states have captured, and each calendar/slot/program word is defined by a qualified write before its first read/use. Masking top outputs alone does not undo early writes.
4. Reset/abort/restart proof: either existing correspondence persists or a complete reinitialization/qualified-write sequence precedes the first valid use; no arbitrary state-equality premise.

Source guard pricing proposal, NOT implemented/adopted:

A guard must begin at a qualified real POR source, before unreset forwarding/tree state, and explicitly hold root reset/producer launch and physical valid observation fences until the actual tree and state lifetimes are defined. A generic guard placed only after the delayed D2D reset port cannot prove earlier observations safe. With no qualified POR event at all, deterministic arbitrary-state startup cannot be guaranteed by adding an uninitialized counter.

Let Kflush be the actual worst native reset-tree propagation bound in source-root edges, plus regional assertion reach, plus the proven3copy-capture bound. Bind Kflush to source/native corner receipts; do not choose an arbitrary delay or derive it from a simulation time. A root guard then holds the root reset level for Kflush running edges after a real asynchronous POR assertion/release, and producer reset/launch must use the same guarded contract. A separate observation fence must remain invalid until the actual downstream reset/defined-word joins; any route/landing ages are additional priced state, not waived wiring.

For a source-proved Kflush<=31, a5bit saturating counter plus1armed bit is a6FF lower-bound implementation. Using existing DFFASRHQNx1 master for all six costs2.274480um2 FF LEF area; comparator/increment/mask logic, clock buffering, recursive reset/fanout copies, observer/producer fence routes and any diagnostic pin/landing are additional UNMAPPED costs. Counter width is ceil(log2(Kflush+1)); no mapped total is claimed. Optional boot_armed diagnostic is one real source status bit and needs a typed route/endpoint if exported. Initial assertion must meet actual library asynchronous requirements; there is no zero-init assumption.

The guard adds Kflush source cold-start edges plus actual downstream reset/landing ages. It need not change any normal issue/transport FF age once armed, but ROOT must approve and GEN/compiler must bind the altered cold-prefix contract. Holding/resetting the producer is essential so early image writes are not dropped. No guard, new clock port, extra normal cycle, constraint change or gate is adopted by this proposal.
