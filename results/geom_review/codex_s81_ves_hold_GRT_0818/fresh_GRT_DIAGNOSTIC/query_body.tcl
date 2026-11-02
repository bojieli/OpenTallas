foreach kind {max min} {
 puts "VES_STD_PATH_BEGIN $kind"
 report_checks -path_delay $kind -format full_clock_expanded -fields {slew cap fanout} -digits 4
 puts "VES_STD_PATH_END $kind"
}
puts "VES_DIAGNOSTIC_PATHS_DONE"
