# clk is the actual common streaming root. Never insert measured2ns as ideal latency.
set_clock_latency -source 0 [get_clocks core_clk]
# Only clock/POR ports exist in this minimum physical endpoint fixture.
# Root POR assertion is asynchronous; its release/recovery/removal paths remain timed.
# No payload IO exceptions, generic20% delays or macro arcs are removed.
