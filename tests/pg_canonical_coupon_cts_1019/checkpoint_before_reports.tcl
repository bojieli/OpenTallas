# Persist the actual state before each canonical report; forward every original call.
# No PG binding, constraints, repair, or stage-order change occurs here.
if {[info commands report_metrics] eq ""} {error COUPON_REPORT_METRICS_UNAVAILABLE}
rename report_metrics coupon_original_report_metrics
set ::coupon_report_index 0
proc report_metrics {args} {
 incr ::coupon_report_index
 set stem [file join $::env(RESULTS_DIR) coupon_before_report_$::coupon_report_index]
 write_db ${stem}.odb
 write_sdc ${stem}.sdc
 puts "COUPON_CHECKPOINT_BEFORE_REPORT $stem $args"
 return [coupon_original_report_metrics {*}$args]
}
