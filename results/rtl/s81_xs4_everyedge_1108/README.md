# S81-TYPES-7-LEC J3 bench evidence (2026-11-08)

Change: ot_s81sl_xs4_ctl payload + stream-head copies load every edge (were held under the rh/rx reset enables);
ot_s81sl_rstopt_xo train capture enables are also 1 in reset. Fixes dsdv_slice_lepe_mu_C__t1 kit LEC KEEP FAIL /
NOT EQUIVALENT (no-reset bits fixed only after the first load, folded by synthesis).

xs4 sha256 0e49aefd... -> 2710712dd9d163b93f222e09db23ae89fb675e25454d2fc45981d149d97aa75c.

- xs4_equiv_new.log: tools/s81_slice/xs4_equiv.sh, new xs4 vs main xs (with the every-edge xs_ctl b28dc6669c0),
  verilator 5.032: 21/21 PASS (incl. L0/L2 in-flight reset).
- xs4_equiv_oldboth.log: old xs4 vs old xs_ctl: 21/21 PASS (baseline).
- xs4_equiv_{mhq,mb,mhe}.log: mutants (g_hq h half swap, r3_b0 <- r2_b1, he top slice <- r2_w): fail 20/19/9 cases.
- xs4_equiv_new_wcopy.log: existing WCOPY negative control: fails as expected.
- rstopt_xo_vtc_*.log: rtl/test/tb_s81sl_rstopt_xo_vtc.sv old vs new: new 0 errors; mutants m1 (vtc always 1),
  m2 (vtc on sp), m3 (vph slot 2 from slot 0) 9623 / 9623 / 10068 errors.
