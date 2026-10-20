proc expect_fail {label expression pattern} {
  if {![catch {uplevel 1 $expression} msg] || ![string match $pattern $msg]} {error "WITNESS_MISSING $label: $msg"}
  puts "EXPECTED_FAIL $label $msg"
}
