# Lane Q-BIND (Qwen compute die dv2f7 stub audit), 10-17

Branch `claude/qbind-1017` (worktree /home/ubuntu/wt/qbind-1017, base claude/q3h3-1016 ad3209c7f). Records: `results/arch/qwen_split_compute_1014/q_bind_1017/`.

Die: full GEN `ot-epyc4:/srv/opentallas-scratch/claude/qwen-split-compute/dv2f7/out/case/die.v` (plan dv2f7-diag-r3-ad3209c7f, rc=0, sha256 f19ae643..., 926 instances, 118 masters). This replaces the relay-skip smoke that pb3 audited. The findings are identical.

The slice RTL used is claude/qdv-slice-1016 35bf465bf.

## Status after this lane (port_bind_r3.json, strict v2)

| check | before (pb3) | now |
|---|---:|---:|
| unbound / stub masters | 0 / 0 (with RTL from 3 branches) | 0 / 0 (from rtl/ on this branch + generated relays) |
| ROM-leaf blackbox stand-ins inside qfd_c_b16_dv | 768 | **0**: c1r8 rr parents vendored and merged; cluster closure lints with 0 errors; c1r8 NK/NL benches PASS on the merged RTL |
| relay/reset-repeater RTL | gen_relay_rtl.py aborted on the full die (qfd_rst_rep q1 open) | fixed: qfd_rst_rep / _p8 = ot_qwen_rst_rep PAD 0 / 8 |
| INPUT_TIED | 3 ports / 12,960 b | **0**, every bit accepted and listed in straps_dv2f7.json (see "Tie classification") |
| DIE_PORT_NOT_IN_RTL | 43 | 43 (blocked on the slice port cut, G1-G3) |
| INPUT_UNCONNECTED | 57 | 57 (producers missing, G4-G9) |
| UNDRIVEN bits | 1,072 | 1,072 (G3/G4/G6) |
| WIDTH_MISMATCH | 1 (tt_ctlm ib 354 vs 380) | 1 (G7) |

No die port was added to the die netlist. Every one of the 43 is blocked for one of three reasons:
- the slice RTL port cut cannot be bound by one MY-mirrored master;
- the die writer connects whole ports only, so it cannot split one slice port across the collective and native59;
- no RTL producer exists.

Details follow.

## Tie classification (owner/coordinator 0da rules)

| bits | where | rule | verdict |
|---:|---|---|---|
| 576 | qfd_c_b16_dv.cid 12 b x 48 | (a) identity | OK. Its only consumer is the ROM-leaf tile_id[15:4]. |
| 48 | qfd_c_b16_dv.far 1 b x 48 | (a) identity | OK. Its only consumer is the xcst station index sidx. |
| 12,336 | qfd_c_b16_dv.rs_i 514 b x 24 far-band clusters | (c) provably unused | OK. rs_i feeds only the rs_i->rs_o feedthrough, and rs_o is open on every far instance. A port-free far variant would remove the tie. |
| 1 lane | qfd_d2d_static tv[3]/tp port 3 (RTL literal) | (c) | OK. Port 3 is the KV->compute RX lane, and there is no compute TX on it. |
| — | (d) functional config straps | — | None on this die. |

Once the slice port cut lands (G1), the chain-end idle inputs must be added to the manifest under rule (c):
- W5: st_up_i, sc_up_i;
- E5: ch_up_i, st_dn_i, sc_dn_i;
- the l9_i of any unpaired slice.

## Exact inventory: every unconnected input and undriven bit

The pre-DV producer is taken from q3h5 out_sk die.v.

| consumer.port (bits) | pre-DV producer (removed by DV) | real DV producer | gap |
|---|---|---|---|
| dvs_* .ch_dn_i, ch_up_i, st_dn_i, st_up_i, sc_dn_i, sc_up_i, l9_i, rs_n, rs_s, cmd_i, hr_i (11 ports x 12) | n/a (new block) | neighbour qfd_dv_slice2, c16 rs/rs_o, tt_ctlm (cmd/hr at W5) | **G1/G2**: the die still emits the synthetic port cut |
| io_collective.in_data 512 / in_tag 32 / in_last 1 / in_mode 1 (**undriven** n_dvr_ng_seq_cd_d_{0,514,512,513} = 546 b) | qfd_seq_su_static cd_d | dvs_W5 ch_dn_o[1093:548], the AR word {valid, tag 32, last, data 512} | **G3** port split; **G4** the AR word has no in_mode bit |
| io_collective.in_valid 1 | seq_su cd_d[546] | dvs_W5 AR word valid | G3 |
| io_collective.cmd_mode 1 / cmd_tag 32 / cmd_v 1 / cmd_words 16 | seq_su coll_cmd | **none** | **G5** |
| native59.q 524 / q_committed 1 / q_fault 1 (**undriven** n_dvr_ng_vm_q_0, _q_committed_0, _vm_fault_0 = 526 b) | VM (qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3) q / q_committed | dvs_W5 ch_dn_o[547:0], the D2D word (548) | **G6** native59 re-port |
| native59.kv_we 64 / kv_waddr 1536 / kv_wdata 2048 / native_issue 63 | qfd_sp_su64_sfu | the slice D2D word (8 lanes x {addr 24, FP32}, mask 8, kind 2) | G6 |
| native59.write_commit_line 312 / _mask 624 / _v 39 | VM write_commit_* | none in DV (the VM is in the slice) | G6: drop, or derive from the D2D word |
| embed_prov.core_start 1 / core_token 18 | seq_su embed_scale_re / embed_scale_addr | **none**; the token id comes from the LM-head argmax in the slice root | **G9** |
| embed_prov.embed_code_addr 24 / _re, embed_scale_addr 18 / _re | seq_su | **none** | G9 |
| sys_face.crom_fault_code (8 x crom_g fault_code) | qfd_crom_g x8 | slice st (CROM fault in st[73:0]); every slice st is OPEN today | **G8** |
| sys_face.seq_cfg_image_ready / seq_dc 56 / seq_descriptor_obs 69 / seq_program_obs 76 | seq_su | tt_ctlm / slice st | G8 |
| sys_face.res_issue_fault | qfd_res_train_issue_b2 | none: the res trains are gone | G8: drop the port (rule c) |
| tt_ctlm.am0..5 52 b each | qfd_port_half_b2 x6 | none (port halves removed) | **G7** |
| tt_ctlm.rf0..5 | qfd_res_train_half_b2_0..5 fault | none | G7 |
| tt_ctlm.uf (band-upper faults) | qfd_band_upper_b2_l2_s4 x8 | none | G7 |
| tt_ctlm.b2_status_fault | qfd_b2_word_status | none | G7 |
| tt_ctlm.cp_active | sp_su64 cp_active | slice st (su_active) | G7 |
| tt_ctlm.ld 16 / meok | VM ld / mo | slice st | G7 |
| tt_ctlm.st 49 / xs 57 / su_image_ready / su_observe 16 | seq_su | slice st / SETID enumeration | G7 |
| tt_ctlm.xflt | qfd_xs_tap fault | none (xs_tap removed) | G7 |
| tt_ctlm.ib width 354 (die) vs 380 (RTL) | xs_tap gi rsi | W5 hr_i ib 379 | G7 |

The 43 die ports not in the RTL:
- **22 synthetic** slice ports: ch/cmd/hr/st _{w,e}{i,o} (16), l9_eo/l9_wi, and rs_n0/n1/s0/s1. These are G1/G2.
- **21 W5 re-home stand-ins `r_*`**:
  - r_ng_seq_cd_d_{0,512,513,514} and r_ng_vm_q_0 / _q_committed_0 / _vm_fault_0. These drive the undriven nets above (G3/G4/G6).
  - r_ng_io_out_{data,valid,err,rank}_0 and r_ng_native_vm_ar_0: collective out 518 and native59 vm_ar 520 into the W5 return chain ch_dn_i. Their producers exist. They need the G3 split.
  - r_ng_io_cmd_free_0: a collective output with no DV consumer (G5).
  - r_ng_tt_mx_0 553, r_ng_tt_mee_0, r_tt_ib__rsi_{0,251,353}, r_b2_source_me_go/_split, r_selector_l0_selector_fork_0_sel4: pre-DV tt_ctlm outputs. Their DV replacement is hr 453 + cmd 116 (G7).

## Producer-gap list (for the slice RTL lane / QC owners)

- **G1 (blocking, slice RTL): the slice2 lateral port cut cannot be bound.**
  - The cut is directional: dn = toward W5, with hr/cmd only W->E.
  - dv2r8f7 places one master with the E row MY. A MY mirror puts the master's dn face on the die E side, so at the W0|E0 seam hr_o meets hr_o and ch_dn_o meets ch_dn_o.
  - Fix: symmetric lateral faces. Per face f in {w, e}, each kind gets an in and an out: {st 1088, sc 48, ch 1094, hr 453, cmd 116, l9 514} _{f}i / _{f}o. The die already has these pin slots at these widths, except that it fuses st+sc as 1136.
  - The dn face is learned at SETID: the face the enumeration command arrives on. This is a real producer, not a strap.
  - Idle (zero) words go on the unused inputs, and the unused outputs stay open.
  - Alternative: Q-DV/Q-CLUSTER change the E-row orientation. This is not feasible in dv2r8f7, because an R0 slice under MY clusters misaligns the abutted N/S pins.
- **G2 (slice RTL): split rs_s / rs_n (1028) into rs_s0/rs_s1/rs_n0/rs_n1 (514 each).**
  - They map to {near rs, far rs_o} of the abutting cluster.
  - The die writer (qwen_rom_fulldie.write_netlist) connects whole ports only.
- **G3 (slice RTL + W column): split the ch chain into ar/dd sub-ports**, so that W5 binds io_collective and native59 whole-port with no glue:
  - outbound: ar 546(+1, see G4) and dd 548;
  - return: ar 518 and dd 520.
  - The collective's in_* must take the AR word as the slice emits it, or the slice emits the collective's port set.
- **G4 (slice RTL): the AR word lacks the collective in_mode bit.** The collective's in_* are valid + tag 32 + mode + last + data 512 = 547 b. The slice ar word is 546 b.
- **G5 (no RTL): no producer for the collective command.** The command is cmd_mode/tag/v/words, 50 b, plus in_valid. seq_su issued it before DV. Owner decision: the W5 slice (cmd kind) or tt_ctlm issues it. Also decide what consumes cmd_free (static schedule: observation only).
- **G6 (native59 re-port, owner needed):**
  - consume the D2D word (548) instead of kv_we/waddr/wdata/native_issue/write_commit_*/q/q_committed/q_fault;
  - produce vm_ar 520 into the W5 dd return.
- **G7 (tt_ctlm DV re-port, owner needed):**
  - outputs: hr 453 + cmd 116 to dvs_W5.
  - inputs: the 12 slice st words (74 b), which are open today. These replace am0-5, rf0-5, uf, b2_status_fault, cp_active, ld, meok, st, xs, su_image_ready, su_observe and xflt.
  - ib: settle 379/380 against the die's 354.
- **G8 (sys_face DV re-port):**
  - crom_fault_code and seq_* obs come from the slice st / tt_ctlm;
  - res_issue_fault is dropped.
- **G9 (no RTL): no producer for embedding fetch/token start.** These are core_start/core_token and embed_code/scale addr/re.
  - The token id is the LM-head argmax at the slice root, and it needs an output port.
  - The fetch request was seq_su. Who issues it after DV is open: tt_ctlm, or the W5 slice cmd.
- **Die flow:** once G1-G3 land, dv_case.py must emit the slice2 RTL port names, and the W5 r_* re-homes go. Both are blocked until the slice RTL has its cut.

## Log
- [Q-BIND] 10-17 09:58: c1r8 ROM-leaf bind and qfd_c_b16_dv vendor are on claude/qbind-1017. The relay generator handles reset repeaters. Strap manifest written: 12,960 b = 624 identity + 12,336 chain-end. G1-G9 are open for the slice RTL / QC owners. END.
