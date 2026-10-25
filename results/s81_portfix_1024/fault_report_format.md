# S81 die fault report format (S81/PORTFIX-FLT, S81 DECISION 4, 2026-10-25)

Rule: each unit has ONE 1-bit sticky `fault` output. Detailed status and fault-code outputs are dropped from
partition ports. The die ORs the unit faults on two registered 1-bit fault rings. The sequencer/host unit
(`dsdv_hostb_seqhost_mux`) latches a sticky die fault word and reports it to the host in band on the existing host
return `t_host`. This adds 0 lanes and 0 frame kinds.

## 1. Fault rings

| ring | path | stops |
|---|---|---|
| sid | seqhost `sid_ro` -> 16 C slice partitions -> seqhost `sid_ri` | `ot_s81_frs #(NL)`: local faults = the C slice / end-slice wrapper `fault` + feeder lanes (bk_sel -> gunit -> s_3N_C, each LP -> its C slice) |
| vid | seqhost `vid_ro` -> 16 svc partitions -> seqhost `vid_ri` | `ot_s81_frs #(NL)`: local faults = svc / irg / pvso entry / etap + feeder lanes (iqf -> svc_0, eng -> svc_14, phy_hbm -> svc); `ot_s81_frs0` where a partition has no local source |

A stop is a registered OR: `s <= s | (|f)`, `fo <= fi | s` (async active-low reset clears `s` and `fo`). Every hop
is a flop, so no combinational path crosses a partition. The ring is a static level with no handshake. The ring
heads `sid_ro` / `vid_ro` launch the seqhost's own sticky fault, so a seqhost fault also travels the full ring. That
traversal is proof that the ring is closed.

Latency, measured in `tb_s81_fault_ring` for a fault captured at stop k (0..15):
4 + (15 - k) edges to the `t_host` bit. These are the stop hop, the downstream hops, the ring-end pin flop, the sticky
word and the word register. From the own fault to the sid/vid bit via the ring head: 19 edges. These are status
levels only and add 0 cycles on any compiled schedule.

## 2. Die fault word -> host (`t_host`, 77 b, unchanged width)

`t_host = {alive[76], st11 = {fault[75], wf4[74:71], sseq6[70:65]}, t_v[64], t_d[63:0]}`.
The seqhost now drives the former `wf4` field with the die fault word:

| bit | name | meaning |
|---|---|---|
| 75 | fault | core fault (seq_host sh_lk: ingest / host-sd / lane / issuer / wf) OR sid OR vid OR own |
| 74 | sid | sid ring returned a fault (any C slice stop, or own via the ring head) |
| 73 | vid | vid ring returned a fault (any svc stop / feeder, or own via the ring head) |
| 72 | own | seqhost's own fault: former `t_mf[3:0]` (MU hslot collision / off-calendar / RL return / config, hwin RX tag / late / window config, static KS6 starter) OR former `hostb_fault[2:0]` (HOSTB landing select faults, KS/HBE source slot faults) |
| 71 | wf | OR of the core's former detail wf bits {rg_f, rg_drop, svc_f, vf} (the detail is dropped) |

`alive`, `sseq`, `t_v` and `t_d` are unchanged.

What the host sees: the s_7N lep (`ot_s81sl_lep_core`, HOST_EN 1) sends a THOST frame (type 3) on every `t_v` and
on every change of `t_host[76:65]`. A status-only change merges into a pending `t_v` frame. So each newly set fault
bit reaches the host as a THOST frame whose payload `[4 + 65 +: 12]` holds `{alive, fault, sid, vid, own, wf, sseq}`.
The bench decodes it on the host side of the real lanes and PHY. The s_0N HBC return record samples the whole
77-bit `t_host` too, so the word also rides the HBC return.

Timing: bits [75:71] leave the seqhost one edge after the core's `t_host` register. Only fault/status bits are
affected; t_v, t_d, sseq and alive keep their edges, so the data and host-return paths add 0 cycles.

## 3. Reset

Sticky faults are control state (OWNER DECISION 13 wavefront). The die reset clears every stop's `s`/`fo`, the
seqhost's ring-end pin flops, the sticky `own`/`sid`/`vid` and the word register. After reset the host receives a
THOST frame with the bits 0. This is checked in the bench's RESET phase. Each unit's own sticky fault also clears on
that unit's reset.

## 4. Per-unit 1-bit fault (what is OR-ed) and dropped status outputs

| module | new `fault` = sticky OR of | dropped ports |
|---|---|---|
| `dsdv_bk_sel_vmtx` | bk_sel fault, selids fault, rung collision mf, vmux collision (former `vm_fault`), tree TX fault (former `tx_st[0]`) | `vm_fault`, `tx_st[15:0]` (TX cause code, done, armed, busy) |
| `dsdv_idx_rg3`, `dsdv_idx_rg3_nq`, `dsdv_idx_rg3_nq_native` | the reader's fault causes `fc[7:0]` (registered, reset by the relayed reader reset) | `st[9:0]` (fc 8, act, fault) |
| `dsdv_svc_rs_pvso_entry` (+ face variants `dsdv_svc_rs_pvso_entry_fv_*`) | entry fault, PV/SO ingress fault, half-join fault, collision, program fault (now registered sticky, +1 edge on the level) | `so_ready`, `so_done`, `so_fault_code[11:0]` |
| `dsdv_hostb_stage_hbc` | stage faults `[11:0]`, HBC fault, return fault (sticky) | `return_fault`, `arm_mask`, `arm_commit`, `fault[11:0]`, `context_valid`, `receiver_edge`, `boot_edge`, `hbc_fault` (old `fault[11:0]` replaced by 1-bit `fault`) |
| `ot_s81sl_slice_lepw_mab_hbc_prod_mu_72` / `_r4d_mu_72` (s_0N) | `hb_fault` = the HBC's 1-bit fault | `hb_arm_mask`, `hb_arm_commit`, `hb_fault[11:0]`, `hb_hbc_fault`, `hb_return_fault`, `hb_ctx_valid` |
| `ot_s81_mu72_lnland` k_st | decision: pure PHY status, not a fault. The PHY rx fault already reaches the lep through lane `flt[2]`, which goes to the lep fault collector and the wrapper `fault`. New variant `ot_s81_mu72_lnland_nst` (no k_st/n_st) is used in s_0N prod/r4d, s_0S `lepw_mu_72` and s_7S `lepe_nh_mu_72`. s_7N `lepe_mu_72` keeps `ot_s81_mu72_lnland` because its lep consumes `l*_st` for the host-plane `f_lf` live/fault status. | (internal only: no partition port change) |
| `dsdv_hostb_seqhost_mux` | own = OR(former `t_mf`, `hostb_fault`); + ring ends | `t_mf[3:0]`, `hostb_fault[2:0]`, `hb_job_active` (= `t_host[65]`, still in t_host); added `sid_ri`, `vid_ri`, `sid_ro`, `vid_ro` |

## 5. Evidence

The bench is `rtl/dsrom_sys/s81_dv/unit/test/run_fault_ring_bench.sh` (`tb_s81_fault_ring.sv`). It chains the real
`ot_s81_frs` x 32, the real `dsdv_hostb_seqhost_mux`, the real `ot_s81sl_lep`, 2 lanes and the UCIe PHY model, then
a host-side frame decoder. Base PASS. Six mutants FAIL: stop not sticky, ring OR dropped, local fault dropped, ring
heads not driven, own bit dropped, sid/vid fields swapped.

The bk_sel unit bench is `rtl/dsrom_sys/s81_dv/idx/test/run_bk_sel_fault.sh`. A real vmux collision raises a sticky
fault and reset clears it. The vm_fault-dropped and non-sticky copies FAIL.
