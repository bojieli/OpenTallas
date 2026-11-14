# TL-SST27 (s81 slice_station__t27) 11-14
- Cause: wave GEN_LINT FAIL ot_dp_clk_landing.sv:10 defparam LOCAL (same as t36/t14/colh9r0p5): B3v/src rtl/common predates CLAND-RING-LOCALITY ef145cfb0d0 while bind emits .LOCAL(1).
- Fix: TL-LEAFT14 patched epyc9 B3v/src (4 rtl/common files = origin/main). 04:5x I copied the same 4 files (sha 80f7e8c3.. landing) to intel1, epyc10, epyc7 (epyc2 has no B3v/src); hardlinks broken, originals in each host /tmp/sst27/bak.
- Next: KIT-OPS-3 retry key slice_station__t27@2 (asked). Then follow wave a2 gen_lint -> preflight -> place -> route -> sign-off; on pass add AUTO-RESIGN row.
