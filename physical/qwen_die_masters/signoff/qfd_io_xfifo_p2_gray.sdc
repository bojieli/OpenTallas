# I12 opt-in wrapper: original p2 postCTS/currentbudget unchanged, then Gray-only overlay.
set ot_xfifo_sdc_dir [file dirname [info script]]
source [file join $ot_xfifo_sdc_dir qfd_io_xfifo_p2.sdc]
source [file join $ot_xfifo_sdc_dir qfd_io_xfifo_gray_cdc.tcl]
unset ot_xfifo_sdc_dir
