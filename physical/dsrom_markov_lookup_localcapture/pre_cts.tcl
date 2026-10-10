# Release only capture instance protection during clock construction.
# electrical_env retains all512 direct D/q net protections and FIRM placement.
set ::ot_capture_allow_clock_reconnect 1
source /src/physical/dsrom_markov_lookup_localcapture/pre_repair.tcl
unset ::ot_capture_allow_clock_reconnect
