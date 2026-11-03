# DH58-RFRTL (helper of DIE-HEAD-58): RTL side of HEAD RE-FORM batch l48rf (CLOSURE-LIST HEAD-046)
Branch claude/dh58-rfrtl-1103 (off main 08542fa9d7d), wt intel2 /srv/opentallas-scratch2/claude/dh58/rfrtl, data intel2 /srv/opentallas-scratch2/claude/dh58/rfrtl_data, epyc2 /home/ubuntu/scratch-root/claude/dh58-rfrtl.
OWNER 07:0x: 150k / util / +10% quick-place are AIMS (advisory), only sign-off blocks. hd_st_m SIGNED -> unchanged.

## 2026-11-03 06:55 PST CENSUS v1: real ORFS synth std cells per HEAD type (signed hard cores + SRAM macros are macros, not counted)
Source: newest kit synth per type (run/logs/.../1_synth.json + mem.json, kit_wave/dh55 kits, l48x/l48z/cland vintages), census_i2.{json,tsv} [CHECKED].
Memories > SYNTH_MEMORY_MAX_BITS (4096): 0 in every measured kit (mem.json $mem_v2 rows, all kits synth with the 4096 default).
| type | std cells | std area um2 | macro area um2 | macros | >150k |
| hd_host (unsplit) | 204,630 | 31,297 | 124,005 | 72x sram 256x64 + 38x 32x64 | YES -> HSPLIT |
|   hd_host_w (HSPLIT genP) | 102,350 | 15,869 | | | no |
|   hd_host_e (HSPLIT genP) | 85,797 | 13,527 | | | no |
| hd_mesh | 191,052 | 29,507 | 124,005 | 72x 256x64 + 38x 32x64 | YES (plan said 140k) |
| hd_lep0N | 176,571 | 26,247 | 1,670,090 | 4 lep_pair + 45 sram | YES (plan said 365k) |
| hd_spn | 94,043 | 14,072 | 0 | | no |
| hd_tile (glue) | 64,684 | 10,351 | 490,075 | 4 elemA_cv + elemB_cv | no |
| hd_st_n4 | 64,069 | 8,940 | | | no |
| hd_spn_end | 60,758 | 8,986 | | | no |
| hd_st_k5 38,078 / hd_st_turn 37,674 / hd_ctl_n 36,745 / hd_st_n3_turn 34,099 / hd_st_str 32,080 / hd_st_n3_transit 31,950 / hd_host_n 18,450 / hd_spn_wshim_rx 16,402 / hd_turn_a 16,307 / hd_turn_b 15,144 / hd_spn_eshim_rx 14,018 / hd_st_m 5,064 / hd_spn_wshim_tx 3,473 / hd_mesh_e 2,721 / hd_ctl_e 2,715 / hd_spn_eshim_tx 1,207 | all < 150k |
| hd_ctl | PENDING: no kit ever synthesized; ORFS synth probe of ot_s81hd_ctl_core (plan sources, 4 sram64x512 macros) queued epyc2 |
| hd_serdes | PENDING: probe of ot_s81hd_serdes_link (kp4_dchn signed core blackboxed, 2 sram macros) queued epyc2 |

## 2026-11-03 07:13 PST hd_ctl measured: NO split needed
ORFS synth probe (epyc2 dh58-rfrtl/synth/hd_ctl_core, plan l48h0 sources, defines NATIVE32/_OFF): ot_s81hd_ctl_core 95,986 std cells, std area ~14,204 um2 (+ 4 sram 64x512 macros 53,300 um2). Kit wrapper (landing ring, face/strap regs) adds ~5-15k (lep0N ring = 6.8k flops) -> hd_ctl ~105-115k < 150k. Memories: 18 inferred, largest 74x48 = 3,552 bits; 0 > 4096. Plan 300k was an over-estimate. RFPLAN: size hd_ctl from ~110k cells (std area ~16k um2 incl wrapper) + 4 macros.

## 2026-11-03 07:13 PST SPLIT BOUNDARIES v1 (for DH58-RFPLAN slot reservation; all seams = registered at both faces, valid/fault reset, data unreset)
1. hd_host (204,630) -> hd_host_w 102,350 + hd_host_e 85,797 (DH56-HSPLIT form, claude/dh56-hsplit-1103@fbf08fbda2): W = lane0 + HBC1 + host276 rx/tx + frame mux + job-active pin (W/N faces); E = lane1 only (S face, coll_i1/coll_o1). Seam buses: l1_rx E->W 558 b {flt4, rx_v, rx_d553}; l1_tx W->E 554 b {tx_v, tx_d553}. Cycles: seam +4 each way (wrapper boundary flops + E mid stages), HOST1 egress coll_o1 +1 (E co_m), W lane0 stage +1 on lane0 RX (open item, HBC dates +1). Continuing it here.
2. hd_mesh (191,052; plan said 140k) -> hd_mesh_a (W: lane a u_la + own BEST rx u_own + RX copy FIFO/word port; faces coll_ia/coll_oa + m_tx_i/m_rx_o) + hd_mesh_b (lane b u_lb only; faces coll_ib/coll_ob). Same seam as host: b_tx W->E 554 {tv_b, own_frame553}, b_rx E->W 558 {fl_b4, rv_b, rd_b553}. Est. a ~105k / b ~86k. BALANCED form (exact by construction): lane a TX and RX get the same seam cycles as lane b (+N each), so the endpoint = unsplit mesh_ep_core with m_tx_i delayed N and m_rx_o delayed N (lane rx_v/rx_d have no ready, pure pipes). mesh_b has the SAME form as host_e (one mesh lane + face regs) -> uniform template candidate (one type for host_e and mesh_b if the face pin order matches).
3. hd_lep0N (176,571; plan 365k) -> hd_lep0N_a (LEP shared: ro/ri ring port, IN_PIPE, RX merge g_rxm, MU tag/land u_land + 5 sram128x256, copy-A lane pair 0/1 g_tx/g_rx + its 2 lep_pair cores; ~134k) + hd_lep0N_b (copy-B lane pair 2/3 g_tx/g_rx engines + their 2 lep_pair cores; ~43k). Seam: ring beat ro (1104 b) A->B registered (+1), B RX beats/faults B->A registered (+1); lane ready/credit handshakes stay INSIDE each block (credits are per lane), so no combinational ready crosses the seam. Flop split from the kit netlist: B = 10.1k of 41.3k flops (24%). Boundary to be confirmed against the generator (head_lep_nr_sources.py) before RTL.
4. hd_serdes (plan 422k = 232,594 shell + 189,510 KP4): probe running (ot_s81hd_serdes_link, kp4_dchn blackboxed). Proposed natural boundary (OWNER 10-29 shared codeword kept): hd_serdes_tx = KP4 enc + PMA TX bm (ck) + pma_tx/pma_tck pads; hd_serdes_rx = PMA RX bm + KP4 dec (incl the signed kp4_dchn core) + rate matcher (pma_rck -> ck) + status st. Seam = only e_flt (1 b, TX->RX status, registered, sticky fault +1 cycle) + rst (each block keeps its own 2-flop ck sync). Data paths do not cross. If rx > 150k: second cut inside kp4_dec on its submodule boundary (dsyn | bm | dchn | dout), numbers first.
5. hd_ctl: no split (above). All other types < 150k (census v1).
