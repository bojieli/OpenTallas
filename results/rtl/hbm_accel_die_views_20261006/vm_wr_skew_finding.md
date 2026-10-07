# Finding: the monolithic hfd_vm die-view wrapper skewed wr_v against wr_data (CLAUDE HBM-ABSTRACTS coordinator, 2026-10-07)

Reported by the views agent; checked here.

- What the SU side does: the VM's real writer is `physical/hbm_die_abstracts_20261006/integration/ot_hbm_vm_publication_parent.sv`.
  It drives the multicast root's `wr_v` (`awv`, a combinational qualification of `activation_wr_v`) and `wr_data`
  (`activation_wr_data`) in the SAME cycle: an ordinary valid/ready port, data launched with its valid.
- What the old die view did: `physical/hbm_accel_die_views/vm/rtl/hfd_vm.sv` (the thin registered wrapper,
  spec.json) packs `wr_v` / `wr_bank` / `wr_addr` / `wr_owner` / `wr_data[2062:2048]` onto die port f_su_NW (4 input
  register stages) and `wr_data[2047:0]` onto f_su_SW (5 input register stages: its face is farther). A sender that
  launches data with wr_v (the real parent does) therefore had 2,048 of the 2,063 data bits latched one cycle STALE.
- Verdict: the monolithic VM die-view wrapper was WRONG for a same-cycle sender (a wrapper artefact: one logical port
  split over two die faces with different stage depths). It is superseded by the r19 quadrant tiles, whose ports keep
  each logical bus on one face with one depth (the views agent's tile RTL must keep wr_v / addr / data on the same
  stage count; bench requirement).
- Token-level benches: NOT affected. The die-view wrapper is default-off and is instantiated only by its own die-view
  route and its own wrapper bench (tb_hfd_vm / tb_mroot_equiv, which drive the wrapper ports and compare a reference
  with the same mapping, so they could not see the skew). No token, layer or composition bench instantiates hfd_vm
  (grep: only physical/hbm_accel_die_views/vm and the generator / view tools reference it); the token path uses the
  integrated RTL (ot_hbm_vm_publication_parent + ot_hbm_die_vm_multicast_root), which is same-cycle and correct.
