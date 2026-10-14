# No reset multicycle exception. Each child has a local two-stage reset
# conditioner on its actual clock branch. All synchronous reset propagation,
# stage-to-stage timing and final stage-to-macro checks keep the normal budget.
# Owner H1 budget for related inter-tile paths. Keep this through route and
# three-corner replay; source/reset clocks still need their actual die binding.
set_clock_uncertainty -hold 100 [all_clocks]
