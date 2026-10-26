"""Shared die-flow safety checks (ROOT14 10-20, owner: reduce die closure risk).

gen_check  GEN/plan hard checks: landing ring on every region crossing, a clock root on both sides of every crossing,
           a relay/repeater site within the 405-um planning reach on every die-level wire.  FAIL = no die run.
kit_pins   stand-in pins of an OPEN tile taken from its kit's real pin plan (face / order / layer).
m8         die RC model when M8 carries die signals (STA wire RC + repeater RC layer).
corners    die STA corner set: TT setup + FF hold always present (every die build, diagnostic ones included).
ir_drop    die IR-drop check (OpenROAD analyze_power_grid on a die-grid window case, M8 signal demand applied).
"""
