# I12 opt-in wrapper: unchanged current route clocks/budget, Gray only.
set ot_xfifo_sdc_dir [file dirname [info script]]
source [file join $ot_xfifo_sdc_dir plain.sdc]
source [file join $ot_xfifo_sdc_dir .. .. signoff qfd_io_xfifo_gray_cdc.tcl]
unset ot_xfifo_sdc_dir
