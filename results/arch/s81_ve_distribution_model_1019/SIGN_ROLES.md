# Literal sign-port source roles and pin-register qualification

These are **sum** output sign pins, not direct square output pins. Exact `78ad1399f` source roles:

- `p_hh <= thh` / `p_kk <= tkk` in `ot_s81sl_ve` output capture.
- `thh`/`tkk` are `tree_hh.y`/`tree_kk.y`; each tree captures its third-level pairwise qadd `s3`, preserving `((s0+s1)+(s2+s3))+((s4+s5)+(s6+s7))`.
- Their chunk inputs are `chunk_hh.sum`/`chunk_kk.sum`. Each chunk starts `acc[0]=0` and performs the actual eight sequential `ot_dsrom_qadd` operations.
- The chunk payload is packed from `mhh`/`mkk`, which are the mul4 `mh(hr,hr)` and `mk(kr,kr)` outputs, passed through the real OLD hold rings and existing captured stages.
- LM5 selects `ot_hdc_qmul_lat.g_l5 → ot_hdc_fp32_mul_f12_l5 → ot_hdc_fp32_mul_f12 CUTS8'b01101010`, not the generic legacy mul_lat model.
- LA4 selects `ot_dsrom_qadd.gq → ot_hdc_qadd_lat KEEP1/LAT4.g_keep4 → ot_hdc_fp32_add_f12_l4 → ot_hdc_fp32_add_f12 CUTS6'b101010`.

The selected arithmetic's sign invariant on **initialized, qualified data** is structural: multiplier q0 receives `a[31]^b[31]`, so a square's sign is zero. Its normal/subnormal encode carries only that sign; bypass/nonfinite/overflow/zero results encode32'd0. The add's normal/subnormal sign is selected from an input sign; with two zero signs it stays zero. The bypass returns an unchanged operand or zero, while cancellation/overflow produce zero. All arithmetic reset outputs are zero. Starting chunk accumulation at zero and retaining the actual stream/reduction association preserves zero sign through both reductions. This exact source role chain agrees with the saved native TIELO roots at `PORT/p_hh[31]` and `PORT/p_kk[31]`.

This argument does **not** prove arbitrary stale ring rows or pre-initialization datapath registers equal zero before their qualified first use. It does not establish an all-times constant assertion on unspecified output cycles, or qualify the production reset/valid contract. Those traces and a causal sign/source-role mutant remain required before constant pin-register adoption. No existing test masks, tied inputs, numerical operations or faults change.

The separately priced130 DFFHQNx1 output pin-register variant is **unreset**. Existing local ties would feed D, Q would drive each actual port; source must retain those physical FF instead of letting synthesis restore constant ties. It costs37.908um², TT61.71568fF/FF67.8613fF clock, no additional tie cells, no reset loads. Cold Q is unknown until the first edge, whereas an ideal literal is already zero: qualification must establish when those bits first become observable, including reset assertion, release and occupied restart. A reset-on-pin variant is not priced or granted; its ASR cells and all new upstream reset loads require another fixed point. Neither variant currently earns a registered-pins PASS.
