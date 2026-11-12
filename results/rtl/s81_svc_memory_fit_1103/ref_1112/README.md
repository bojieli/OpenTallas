# Regenerated svc closure reference ref_1112 (VL3-S81-SVCSTN, 2026-11-12, COORD ruling 2)

**Why.** After 11-05 the svc source changed in 38 svc and hdc files (+3040/-372). The changes include provider form A
918b7b1c60, the att flop form 98c68364e5, the SRX relay stages ee5e3f606f, NSTAGE 3 51a96435d0 and the H8 fold
series. Since then every svc kit_rtl stopped in `s81_svc_memory_closure.py` with `reference net N_Y not structurally
mapped`: the bound numbered nets no longer matched ref_1105.

**Option (b) does not apply, [CHECKED].** Form A (dsdv_svc_mem_lr/la/ar) covers the sw, wq and qmem memories, and only
under `ifdef OT_SVC_ATT_MEM_MACRO`, which the S81 bind does not set. The four memories this closure handles are pmem
512x512, pvq 8x2120, land 640x256 and attn_staging. All four are still native helpers in every current bound, so the
closure stays in place for all four.

**What changed in the tools.**
- The proof logic of the four T7 transforms and of `s81_svc_ref_regen.py` is unchanged.
- `s81_svc_memory_closure.py`:
  - `CUR_REF` now points to ref_1112.
  - New `canon_h8`, applied first in `close_type`. P2 = 0 types bind the H8 P.V header (`pv_header_flags = P2 ? {hb_p,
    flags} : flags`) as a pure alias of the P.V queue read word bits [63:0]. `canon_h8` inlines that alias. It is a
    renaming of a net onto a bit range of another, so semantics do not change. It is idempotent and does nothing when
    the alias is absent. A P2 = 1 type (a real mux) is left alone, and the pvq port then refuses it.
- `s81_svc_ref_regen2.py` changes only how the net pairing is found:
  - an exact difflib line map for `dsdv_svc_att.sv` and `dsdv_svc_rs.sv`, from the 61c902f1-era source (1ec013265f^)
    to the current source;
  - `--drop-loc ot_hdc_v41x_attn_s.sv`: the old structural text of that file is not in git, so on both sides its
    locations keep the column only;
  - register and native-cell anchors;
  - a second pass seeded from the pass-1 register and cell pairs;
  - a statement-shape unify pass.
  The original tool's proofs then decide.

**Proof (this directory, `ref_map.json`).**
- Pairing: 5785 nets.
- Residual: 880 / 1528 lines, and `tokens_in_residual` is empty, so no net any transform names lies in the source change.
- T7 self-check: PASS 12605dc2.
- The ported chain on the current T7 leaves exactly the same residual as its preimage (`same_as_preimage: true`,
  closure b7cf72bf).
- Reference: the canonical form of the current svc_lo_dsdv_svc_rs__t7 bound (sha 7fa74b19), from the r11r strict bind
  (DIE-S81-87 `out_r11r`, rc 0, source main c6c0f5cf65d2; the svc/hdc RTL is identical on main d09b378900). The
  plan-only G4r form gives a byte-identical bound.

**Per-type check** (`s81_svc_memory_closure.py --bound ... --out`, epyc8):
- SELF-CHECK PASS 12605dc2.
- CLOSED: T7 (lo t7), svc_hi_dsdv_svc_rs__t2, svc_lo_dsdv_svc_rs__t2, svc_lo_dsdv_svc_rs__t5, svc_hi_dsdv_svc_rs__t6.
- In every case all structural obligations held: port and capture identity, the 2158-bit struct with three readers,
  per-lane RD_ADDR rows, the removal counts, an identical header, and the untouched lines identical and in order.
- The other svc types are checked as each kit reaches the step.

**EQ basis.** The same basis as the 11-03 class port:
- the native helpers keep their content-hash names (193c9 / 9c281 / 4c805), so they are byte-identical to T7's;
- the MEM v2 children are unchanged and gated (`../gate.out`, positive plus 5/5 mutants);
- the bound integration is proved by the structural obligations, re-checked per type.

**Reproduce.**

    git show 1ec013265f^:rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv > old/dsdv_svc_att.sv   # and dsdv_svc_rs.sv
    cp rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_{att,rs}.sv new/
    python3 -I tools/die_plan/s81_svc_ref_regen2.py <T7 bound from kit_rtl> OUT --old-src old --new-src new \
        --drop-loc ot_hdc_v41x_attn_s.sv
