# KV-AHUB5 (10-19): the attention hub re-floorplanned from a per-flop clock census (g4a / g4b / g4c)

Lane KV-AHUB5 (LEAD3-KV, tree K.STA.AHUB). Input: KV-AHUB4 `1f9ccdca3` (g3a / g3b gates FAIL clock_rule).
Branch `claude/kv-ahub5-g4-1019`. The RTL is NOT changed. The kits are `physical/ref_tile/qkd_ahub_g4{a,b,c}`,
written by `tools/qwen_kv_die/ahub5/mk_kits.py`.

## Census: where the g3a spread came from
`g3a_clock_census_tt.txt` holds the TT clock arrival of every register, with its location. It comes from the g3a gate's
4_1_cts.odb with placement parasitics. The script is `ck_insertion_with_xy.py`: the gate's own ck_insertion.py plus one
line that prints each register's x / y.

- **ck_c (154 ps TT): the core band itself is tight.** The band is 500 x 110 um and holds 10.4k flops: u_core, the four
  c->z write rings and the w / e landing halves. They all arrive between 474 and 526 ps.
  - The late tail is the N-face pin flops: u_io hs / hf, plus u_lpr_root at rst_n. They sit 240 um above the band, at the
    pins, and arrive between 549 and 598 ps.
  - The u_recip flops arrive at 444..463 ps (pin 221 + 238.7).
  - So splitting the core root would not help: its register mass already sits in one 50 ps tree. The core region has to
    contain its own pins.
- **ck_z0 (217 ps TT): the soft region is tight too.** It is 110 x 40 um (the c->z read ring, the z->c write ring and the
  reset forest) and arrives between 408 and 434 ps.
  - Seven u_lprc_u_zh0 reset pads sat in the second fence strip, 170 um away, and arrive at 544..546 ps.
  - The macro clock pin is next to the S entry (92 ps), so the u_zh0 flops arrive at 326..355 ps.
  - At CTS time the root balanced to a mean of 357 ps. The soft trunk around the macro was repaired afterwards and moved
    the soft flops 60 ps later.

## Fix (same RTL, three kits gated in parallel)
- **Core**: one fence box, x 194.4..518.4 and y 388.8..537.84, directly under the core region's N pins.
  - The N pins are hs_*, hf, rst_n and ck_c, now at x 216..443 on the same face.
  - u_recip is R0 at (259.2, 172.8), directly below the box, with its x inputs facing the box.
- **Z trees**: one fence strip per tree, with its reset pads inside. The right-column trees are mirrored (MY / R180) so
  their clock pins face E.

| Kit | Z inputs face | Fence strip | z clock entries |
|---|---|---|---|
| g4a | the centre (as g3) | inner | W / E face, at mid height between the strip and the macro clock pin |
| g4b | the outline | outer | W / E face, at mid height between the strip and the macro clock pin |
| g4c | the outline (g4b geometry) | outer | S / N under the strip centres (the g3b positions) |

## Die / compiler deltas
- **No change vs g3**: HUB_RECIP / HUB_PUB +6, am +3 at the ASTK pins, AP_OFS / FR_OFS / fr edge unchanged, reset
  release +10 once (results/arch/kv_ahub4_1019/README.md).
- **Port positions move on their own faces**:
  - The core N pins are now at x 216..443.
  - In g4a / g4b, the ck_z0 / ck_z2 entries move to the W face and ck_z1 / ck_z3 to the E face (y 130 / 408 in g4a,
    y 106 / 432 in g4b).
  - g4c keeps the g3b clock faces and positions.

## AHUB_DW AML=6 (49 errors) vs AML=3 (PASS)
This is expected; it is a negative control, not a bug.
- AML is the bench's assumption of the compiler am lag: am reaches the ASTK pins D_HS+1+AML edges after its source.
- g3 lands am through the c->face landing (+3; AM_RLY 0 in the landed form). So AML=3 is the only correct value.
- AML=6 would count the +3 twice: the flat-reference AM_RLY 3 plus the landing 3.
- The mutant m19 (AML 0) fails for the same reason in the other direction. **The die must take am +3, not +6.**
