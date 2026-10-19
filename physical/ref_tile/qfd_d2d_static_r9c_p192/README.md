# qfd_d2d_static_r9c_p192 (QW-SRAM3 10-19, DIAGNOSTIC; critical prefix qfd_d2d_static: PNG + facts only, NO REVIEW/submit)

r9c RTL/pins unchanged; the four 64x512 stores bind `ot_sram_1r1w_64x512_m1_r2c2_p192_mir` (5.21 pins/um vs 10.2)
via `rtl/lib/sram_p192_1019/ot_sram_1r1w_64x512_m1_r2c2__p192.sv`. Two abutted N-S stacks at x=43.2 / 259.2,
y=43.2 / 197.136; outline 475.2 x 280.8 -> 475.2 x 388.8. Purpose: measure macro pin escape (GRT overflow at the
pin faces) in the real D2D parent. Known r9c source issues (221 unsafe roots, reset) are QW-D2D3 scope and are
NOT fixed here; checklist items 1/3/7 inherit r9c state. Item 6: 43.2 lattice, faces <=5.21/um, aspect 1.22.
