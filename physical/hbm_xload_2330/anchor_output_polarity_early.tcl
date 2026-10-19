# Run BEFORE global resize can insert repeaters for a polarity INV misplaced
# on the opposite face. Global placement is intentionally not legalized yet;
# reserve only free legal sites, keep INV FIRM, and let normal DPL verify all.
set ::ap_require_legal 0
set ::ap_refresh_rc 1
source /src/physical/hbm_xload_2330/anchor_output_polarity.tcl
unset ::ap_require_legal
unset ::ap_refresh_rc
