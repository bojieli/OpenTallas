# qfd_native59_dv_service_safe3b
Parallel fallback of qfd_native59_dv_service_safe3 (identical RTL, top, outline, macros, reset forest, one root).
Only difference: recipe 4 "hold_budget": "die" (flop-first pins, no inhold/outhold pads; FLOW-HOLD rule).
Checklist: see ../qfd_native59_dv_service_safe3/README.md (item 7: boundary hold is the die budget).
