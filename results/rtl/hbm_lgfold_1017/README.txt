LG tap fold (coordinator HANDOFF 0db 10-17: lg_static_bank (64) and _term (32) fold each tap into its consumer tile; no 37.8-um slots).
d4f contract: per quadrant q and bank pair g, the chain HC (term tap, local hc_<q>g) -> SFU (tap, local sfu_<q>g) -> SU (tap,
local su_<q>g) -> hb_vms_<q> bank. Consumers: hc_<q>g / sfu_<q>g = ot_hgi_sfu_lg_pair_leaf, su_<q>g = ot_hbm_su_static_pgslice.
New masters (pure composition, unchanged leaf/tap RTL inside, same edges):
  ot_hbm_vm_lg_pair_tap / _term          two taps of one bank pair (RET_PIN=0: return edges are parameters, no rret/wret straps)
  ot_hgi_sfu_lg_pair_tap_leaf (14/11)    SFU level: pair leaf + pair tap; replaces sfu_<q>g + lg_<q>_1_b{2g,2g+1}
  ot_hgi_sfu_lg_pair_tap_leaf_term (18/15) HC level: pair leaf + terminal pair tap; replaces hc_<q>g + lg_<q>_2_b{2g,2g+1}
  ot_hbm_su_static_pgslice_lg            SU level: unchanged pgslice + pair tap (10/7); replaces su_<q>g + lg_<q>_0_b{2g,2g+1}
    (pgslice ports unchanged except lg_* now face the VM bank; new lg_read/lg_write, far_rq/far_wq in, far_rr/far_w_done out)
Calendar selects: calendar_<q>.lg_local_read/write[b] go to the folded tile's local_read/local_write[b-2g] (SU: lg_read/lg_write).
Bench tools/hbm_static/lg_fold_run.sh (iverilog): every folded tile vs its discrete die composition (leaf PIN_RST=1 + taps with
  RET_PIN=1 straps), all outputs, every edge, 20k random edges incl. a mid-run reset: bench_pos.log PASS; bench_mut.log (folded SFU
  bank-1 payload mux selects far) FAIL as required.
Kits (mk_lgfold.py): hbm_sfu_lg_pair_tap_leaf_1017 and hbm_hc_lg_pair_tap_leaf_term_1017, pin-bound 216x216, recipe 4.
Die effect: -96 tap instances/slots, -64 x 1,112-bit leaf<->tap seams (SFU+HC) and -32 SU<->tap seams; +20 strap bits removed per tap.
NEXT (H-NETLIST/H-DIE): switch sfu_<q>g/hc_<q>g/su_<q>g masters, drop lg_<q>_*_b* instances and their rret/wret straps.
NEXT (HBM-SU lead): harden su_<q>g with ot_hbm_su_static_pgslice_lg (the taps sit beside the slice's VM bank leaves on pg_clk).
