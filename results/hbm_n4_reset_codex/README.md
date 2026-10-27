# Native FUSED delivered reset candidate

The physical profile explicitly selects DELIVERED_RESET=1 on the central native wrapper and external N4 nodes. The input is the die's delivered synchronous reset. Each region uses three kept synchronous relay stages, preserving the legacy three-edge release date while removing local synchronizers. Assertion also takes three local edges, so boot/START must wait for all actual delivered offsets, six central nested local edges and active pad warm-up. Default0 preserves legacy behavior.

The primitive reset test compares all release edges across16reset phases (112checks); an early-release mutant must fail. The real native extraction compares unchanged legacy gold against delivered-mode root and N4 components, with original zero and4/4/2 SRAM pad calendars and pair-order mutants. No arithmetic, data pipeline, clock conversion or extra face registers were added.

This candidate does not supply the missing actual four-role boot/START calendar. Physical generation must preserve declared launch/reset register copies using the existing ot_keep_regs canonicalization hook, then export native boundary anchors. Bare source census can merge copies and cannot set the final physical FF count. No placement, route or STA is authorized by this package.
