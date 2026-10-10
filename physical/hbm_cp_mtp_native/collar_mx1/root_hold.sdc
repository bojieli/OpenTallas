# H1's sender owns50ps hold uncertainty on each face leaf just as on core_clk.
# All roots remain related and propagated. No path exceptions or delay credits.
if {[llength [get_clocks -quiet vclk]]} {
    foreach name {mx1_s mx1_n mx1_e0 mx1_e1 mx1_w0 mx1_w1} {
        if {[llength [get_clocks -quiet $name]]} {
            set_clock_uncertainty -hold 25 -from [get_clocks vclk] -to [get_clocks $name]
            set_clock_uncertainty -hold 50 -from [get_clocks $name] -to [get_clocks vclk]
        }
    }
}
