# S81-SMWIRE: SO target on the S81 MU die, GEN mu5 strict bind (10-19)

Branch claude/s81-smwire-1019 (on GEN mu4c source claude/s81-bind-mu4-1019 19bf4121e). Compiler placement patch:
claude/s81-smwire-xsbf-1019 145dbd28e (off main, tools/s81_dv/layer_prog/xs_bf.py).

## Result
- **Strict main die_port_bind PASS on GEN mu5** (plan p4l_lkcol_mu_pf, bind_table_p4l3_mu.json, land plan p4l3):
  unread 0, output open 0 (was 10 on mu4c), undriven/multi/tied/unbound/stub 0, pad bits 210,532 (-96: pv lane bits
  514..561 now carry pv_x on both entries). die.v sha256 9ac324e7..., ot-epyc7:/srv/opentallas-scratch/claude/s81-smwire/gen_mu5/bind/.
  port_bind_mu5.json / .log here.
- The 16 SO targets are placed INSIDE the 16 svc_rs slices (no new die block / plan link). Plan delta for S81-DIEPLACE:
  plan_block.json (+~0.0048 mm2 / slice, 4 SRAM 32x64 each; rsv tile fit 1.124 -> ~1.120, no outline change).
- Calendar delta (MU.S81.CAL.1): calendar.json (`priced_edges`): +3 q words (SOT) a job; attention tail from the last SO
  write to the last XS arrival 115 edges (E half, S tier) / 132 edges (W half, N tier via the G-unit rung); END after
  the last booked head retire.

## RTL (what changed and why)
| piece | file | function |
|---|---|---|
| config source | sm_target/dsdv_sm_wire.sv dsdv_svc_sot | SOT q frame (type 14, len 2) after WIN_LOAD: owner (tag/user checked vs WIN_LOAD, epoch from host), jids, obase, route, entry window, per-head edges |
| target | sm_target/dsdv_sm_so_target.sv | Codex 90917d90d; HEAD=-1 = head strap pin (role tile) |
| gather words | dsdv_sm_gw | beat -> lo, hi, hdr{5A, owner, head, group, idx} on the slice's P.V return tree (merge: 2 words/cycle = existing fault) |
| entry stamp | dsdv_sm_gx | booked window -> pv_x (pv lane spare bits 514..561) |
| svc_rs | svc_rs/dsdv_svc_rs.sv, dsdv_svc_att.sv | target + sot + gw inside the core (SMT=1); faults -> slice lf / up tree / jd; so_pend holds done until clean retire; att accepts type 14 |
| landing | land/dsfd_dvland_pvrd.sv | stamped words bypass the P.V RD calendar -> B words kind 2 |
| C3 xr | slice/ot_s81sl_xr.sv | B kind-2 words -> one XB ring beat -> ci (route 1 line E+W, route 2 V) |
| ring stop | slice/ot_s81sl_rstop.sv | ci XB: own XS delivery (line) / 4-fragment V train (V) |

## Benches (Verilator 5.050, ot-epyc7; logs in results/rtl/s81_smwire_1019/)
- tb_smwire_e2e (make_bench_e2e.py / run_e2e.sh): real SMS DUT + slab reference heads -> SOT frames -> sot/target/gw ->
  tree stand-in -> gx -> lane -> pvrd -> xr HB1 -> 4 rstops; bit-exact at the XS gather ports.
  base route 1: 192 beats at s_3S/s_4S/s_2S each, 0 at s_3N, constant latency 16 / 18 / 18 (+5 one hop), all faults 0;
  base route 2: 192 at s_3N (latency 22), 0 on the line; SMS PASS 609 checks.
  Mutants all FAIL: SMW_MUT 1 tag (sot fault, no config), 2 lane data, 3 short window (landing fault), 4 route bits (xr
  fault), 5 idx; TARGET_MUT 1..5 CAUGHT; RTL OT_SMWIRE_MUT_ORDER (data mismatch), OT_S81SL_RSTOP_MUT_CIXB (s_3S 0 beats).
- regressions: xr_bench HB0/HB1 PASS + hops/row/porder/nocol/bwide FAIL; rstop_sid PASS + tiercol FAIL; pvrd PASS +
  mut_cal/mut_sel FAIL; die-build lint of dsdv_svc_rs / dsdv_svc_rs_entry 0 errors.

## Not done here (owed)
- svc_rs is not hardened (cluster); xr3 kit still owed (BIND); xg/rstop re-kit owed (new V-train register) -> SLICE.
- xs_bf.py tier placement 145dbd28e needs ROOT merge + a frames/ROM regeneration before the wo_a token pass.
- The full 16-slice svc_rs bench (rs_bench.sh) with SOT/SO frames and the rung transit through the real G-unit are
  not in this bench (tree stand-in, direct rung); a die-section token pass must assert them.
