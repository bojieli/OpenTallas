# Placed aHub replacement children

Viewed the actual `layout.png` and `density.png` for the exact private RECIP and ZH checkpoints. Both have clear core access to the original pin banks. The placed OpenDB pin audit found all 69 RECIP signal ports and 70 rectangles, all 338 ZH signal ports and rectangles, and zero shape or BPin mismatches. Both RECIP rectangles at `x[31]` are in one BPin. VDD and VSS also match the retained old LEF coordinates exactly, with 20 M6 stripes per rail for RECIP and 28 M5 stripes per rail for ZH.

- ZH. Unit 2331910, kit `f9647d34cb7da40f`, 3_5 place SHA-1 prefix `2f999072c320cbf8f7e6`. Uniform cell coverage, localized lower-edge density at the signal entry groups, raw worst setup −111.96 ps and mapped LEC EQUIVALENT. PASS for the private route. Clock entry distance 159.79 µm will be assessed in CTS.
- RECIP. Unit 2331902, kit `11200a12e7ec789a`, 3_5 place SHA-1 prefix `f94294eb4c2dd4636829`. Data follows the northwest input to southeast output diagonal, with room alongside the logic. Raw worst setup +186.39 ps. Fanout spread 413.3 µm merits inspection in CTS and route. Geometry passes, and the private route still requires the mapped LEC result.

Actual views and exact database audit: `intel2:/srv/opentallas-scratch2/claude/fable-fix-kv-hub/r4/selected_child_place`. Within each kit see `run/layout_review/place/{layout,density}.png`. This review applies to the two private recovery kits. The installed aHub parent remains on its old child model pair.
