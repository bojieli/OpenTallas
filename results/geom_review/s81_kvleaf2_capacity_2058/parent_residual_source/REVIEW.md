# Parent residual source sizing

Normal RTL_LINT passed and actual Yosys mapping completed on the exact staged native GEN source with 24 unique abstract boundaries: the 23 common matched direct children plus whole KV. Mapped result: 500,877 ASAP7 standard-cell instances, all 24 cuts retained once, four remaining SRAM instances, no unknown leaf types. Counts recursively weight retained design hierarchy and stop at physical standard-cell/memory masters; behavioral library implementations are not counted as logic.

Outer ORFS make synth failed at physical synth_odb because these deliberately source-only aliases lack LEF masters. The failure remains exit 2. No placeholder physical model or pipeline PASS is fabricated. Mapped native metadata and original logs remain at the exact remote runtime; collection did not rerun synthesis.

Kept landing rings account for 161,793 std cells, FT stations 83,927, total 245,720. Actual FF count is 125,510, including 29,953 named VN_b and 10,288 VQ FFs. Flat ABC logic has 206,803 cells and cannot be assigned honestly to one leaf by names. This old GEN wrapper is not a current canonical model; 24 cuts do not by themselves demonstrate current G0C closure.

Source-profile lookup found existing HW_STAGE0 VN_b sizing and a SIGNED view, but that view used OT_S81_VN_CONST_ZERO while this native GEN count uses only SYNTHESIS. The primary source hash matches; the compile profile does not. Existing VQ AQ_XMEM2 evidence also needs full context/ABI/source joins. No view/proof/count adoption is granted from those candidates. Source owners are resolving the exact cohort, without a duplicate sizing job.
