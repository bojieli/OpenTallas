# Current native RSTD→VN/VQ publication timing

PASS unit oth-ubuntu-2981776-1793566632 epyc2, native_leaf_ece_v5, current t48+PG actual flattened leaf profile s_0S_L0. Extends native_leaf_current proof; no DUT RTL change. Actual595-bit public leafdn packet rb_v bit67 and rb_d66:35 traced directly to native VN_a/b rb pins is driven once with RSTD40ca3c85 after the native NORMR partial. Clock833ps.

Native leaf RSTD-input register event→VQ first fragment: K0 Q46edges, BF1666edges. q-only yields4fragments/1header index0, HEAD BF-only4/1 index128, combined8/2 index0 with families20edges apart. VP,VNa,VNb,VS,VQ,clocklanding faults0 and landingready1 each. Input payload mutant changes the already checked native partial and faults VNa, caughtRC1. Other K0..4 add4K as qualified independently by actual same-input VQ transaction gate.

This measures the actual common native producer/publication source age missing the old scalar145 calibration. Full composed XFIN-root→RSTD82edges + actual per-leaf XR→VN RSTD boundaries +46/66 +4K + actual VQ→XG boundaries can now produce source-relative publication events. Unknown common upstream NORMR cohort term remains fixture-component only; all80source-clock phases/global allgather are not qualified here.

The publication fragment payload is literal DUT output; this timing/count/family/flag proof does not independently golden-check all5120normalized values or establish final POST residency/final HEAD inputs. The native partial remains numerically checked3fc9a62e. No synthetic HEAD START/HOST programme dates are produced.
