# idle-sweep-1010 (main ruling 10-10): hold-side IO of the pin-register attn bank by rule H1, NOT the flat 0.2 T.
# A flat 0.2 T (~167 ps) input min assumes 167 ps of upstream minimum delay; the real sender is a pin flop
# (clk->q + a short wire), so 0.2 T hid real hold risk (masking).  H1: the receiver's input min = the sender's
# MEASURED link minimum (clk->q min + min wire to the bank pin, from routed quad / tile sender views), the hold term
# carried once.  No routed sender view measures it yet, so the conservative stand-in is the sender's clk->q min with
# 0 wire and 0 sender insertion: 30 ps (ASAP7 DFF clk->q min, the repo H1 default of
# physical/hbm_ha2_owner_banked_20261006/make_sdc.py --clkq-min-ps).  Replace with the measured link min when the
# routed quad / tile sender views exist.  Output min 0 (the downstream bank pin flop, no wire credit) instead of
# 0.2 T for the same reason.  Setup stays at 0.2 T (set_input_delay / set_output_delay -max are untouched).
# Appended to the route SDC (hold repair at the bank's input pin-flop D sees it) and to the 833 sign-off SDC.
set_input_delay -min 30 -clock core_clk [all_inputs -no_clocks]
set_output_delay -min 0 -clock core_clk [all_outputs]
