HEAD SerDes warm-reset sequencer (DIE-HEAD-54, OWNER 2026-11-02 17:55 decision 1, final).

Change: new rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link_ls.sv = the released ot_s81hd_serdes_link (kept
byte-identical) + the shared gated ot_pdie_pma_reset_hold (codex/serdes-locksafe-2047, on main) on a new
pma_lock input. Core instance stays u_link, so the counted hard child u_phy.u_link.u_dec.u_chn
(ot_s81_kp4_dchn) is untouched. Plan delta tools/s81_head/head_serdes_locksafe_delta.py (hd_serdes only:
module swap, LOCKSAFE=1 HOLD_EDGES=64, +pad pma_lock in 1 bit, +2 sources). Reset contract:
physical/die_plan/s81_head/reset_contract.json serdes_warm_reset. Cost 9 FF/link, 0 mission cycles,
+66 recovered boot edges.

Gate (run_gate.sh REPO OUT; Icarus, actual unchanged KP4 codec + FIFO, ot-run epyc2 10 GB):
  base       PASS: 1011 per-edge lockstep checks HEAD == shared mechanism and LOCKSAFE=0 == released
             adapter; 3 epochs (cold / pma_lock loss with PMA clock stopped / warm rst_n with PMA clock
             stopped): core held while stopped, guard release at recovered edge 66, native reset 68.
  hold63     caught (differs from shared mechanism, epoch 0)
  ignorelock caught (unsafe core reset at the lock-loss epoch)
  dmut       caught (LOCKSAFE default not identity)
Not yet: hd_serdes kit regeneration + G0C/strict bind on the canonical plan, P&R.
