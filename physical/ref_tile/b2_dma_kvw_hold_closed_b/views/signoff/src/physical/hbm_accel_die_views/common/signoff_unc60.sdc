# sign-off clock uncertainty (AGENTS.md: SS setup 60 ps): restores the 60 ps setup uncertainty after a view routed
# over-constrained with io_vclk_m_<L>.sdc (setup 123 ps = 770 ps effective); read by corner_sta.py --post-sdc.
set_clock_uncertainty -setup 60 [all_clocks]
