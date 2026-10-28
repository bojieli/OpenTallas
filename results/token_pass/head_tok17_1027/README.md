# HEAD per token, TOK-ALL-17 (Tue Oct 27 06:06:53 PM PDT 2026)

Base: claude/tok16-head-1027@104f3b9818 (TOK-16 rank-merge die bench, results/token_pass/head_rank_merge_1027).

## (a) D = 251 double count: YES, 6 cycles (CHECKED by source + sim)
- Source of D. results/arch/release_rack_1021/hop_latency.json takes D = 209 ns = 251 cycles from
  configs/hardware/technology.json links.rom_board_serdes.hop_latency_s. Its latency_components_s are:
  - channel 200 ns: PMA/DSP + RS(544,514) KP4 enc/dec + PCS deskew + 0.3 m flight;
  - CDC 4 ns;
  - DIGITAL ENDPOINT 5 ns (rtl/rom/ot_rom_pkg_link.sv TX 2 + RX 2 + out reg 1).
  rom_rack_cable_serdes repeats it: "200 ns channel + 4 CDC + 5 endpoint cycles".
- In the TOK-16 bench the digital endpoint is REAL RTL outside D: mesh_ep_core (link_ep CRC/replay + gearbox),
  best64 / mesh64 codecs. The KP4 digital (ot_pdie_serdes, 79 cyc) sits inside D (79 + K 172 = 251), which is
  consistent with the 200 ns channel. The bench has no CDC (rck = ck), so the 4 ns CDC stays.
- So the 5 ns endpoint (6 cycles at 1.2 GHz) is counted twice. The corrected serdes-leaf-to-leaf hop is
  204 ns = 245 cycles (K = 166).
- SIMULATED at K = 166 (build src/build_k.sh 166; logs/run_k166_pos.log). b_i -> final merge = 413 on 2/2 positions,
  21946/4173a558 = golden, DIE_SPINE PASS 8,691. Every copy arrives exactly 6 edges earlier than at K 172 (linear).
  Control: DROP_N=1 -> RANK_MERGE FAIL (logs/run_k166_drop_n.log), CAUGHT.
- Note: the older RTL hop campaigns (links_full_fec.json: "vendor_channel_cycles board 251" + measured endpoint 6 =
  257/traversal) use the same convention, so they carry the same 6-cycle double count. Information only; not changed here.

## (b) REAL ot_s81hd_ctl_core in place of the composed ctl rows (CHECKED, sim logs)
Bench: src/tb_tok17_ctl_lat.sv. It is the main tb_s81hd_ctl_physical (REAL ctl_core: hsf0_static, static_issue,
x store macros, best64/mesh64 codecs, rank merge, dsfd_mtp_seq, host276) plus edge probes. +B2B = 80 XB beats at line rate.
It uses the same file set as tools/s81_head/head_ctl_bench.sh (src/run_ctl.sh). All bench checks PASS: stream/slice,
token value, RESULT 512-b miter, rank miter.

| probe | measured | model row |
|---|---|---|
| last XB beat -> x store ready | 3 | (xb_ingress = 160 beats + 2) |
| static issue (start) -> go at the sn_o pins | 4 | |
| b_i result -> own BEST frame valid into best64_tx | **6** | TOK-16 driver: 1 |
| last decoded peer frame -> merged (mg4) | 7 | TOK-16: 7 (same) |
| merged -> token flit K_TOK on lepk_o0 (dsfd_mtp_seq + token former + issue) | **15 (pos1) / 18 (pos0)** | mtp 6 + out hop 4 = 10 |
| merged -> host RESULT frame at the sink | 19 / 22 | |

- The probes are identical on shuffled and B2B ingress.
- Control: the OT_S81HD_CTL_MUT_SLICE mutant -> FAIL xa slice mismatch (logs/run_mut_slice.log), CAUGHT.

## Per token (composition of the measured pieces; composition UNCHECKED)
- xb_ingress = 160 link beats (stage link rate through lep0N; lep0N is still stubbed, so this is COMPOSED) + 7 (ctl, measured) = **167** (was 162).
- die spine GO -> b_i = **8,691** (TOK-15, sim).
- rank merge = 413 (K 166 sim) + 5 (real ctl own-BEST issue 6 vs the driver's 1; peers transmit at the same static edge, so the merge moves by +5) = **418** (was 419).
- merged -> token on the ctl pins = **18** worst (15 steady) (was 6 + 4).
- **Total 167 + 8,691 + 418 + 18 = 9,294 cycles (7.745 us)** (9,291 at the steady 15). Window 10,357, slack 1,063.
- Still composed or missing: lep0N ingress/egress internals (stubbed), the 160-beat link-rate ingress, the plesiochronous
  CDC (inside D 245), and the full ctl_core in the die bench (the own-BEST +5 is spliced from the ctl bench).

Raw: intel1:/srv/opentallas-scratch2/claude/tok17-head (obj_k166, ctl/o).
