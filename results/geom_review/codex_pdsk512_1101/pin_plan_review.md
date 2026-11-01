XRT1 candidate pin-plan review, 2026-11-01

Personally LOOK-viewed xrt1_pin_plan.png before fresh placement. PASS-CONDITIONAL for synth/place only: unchanged311.04x395.28 outline; dense but ordered face pin bands and open interior; no macros or macro walls. Data pins retain canonical face coordinates. Clock/reset enter E-face as before. PDN remains canonical generated kit. Actual placed geometry and clock reach are unresolved until3_place; CTS/GRT/route requires a new placed LOOK review.

XRT3 generation FAIL preserved: current plan M6 core-pins conflict with bound legacy LEF M4. No plan or production recipe edited.

XRT3 resolution and pre-placement LOOK: canonical recipe rtl_dirs:true is required; it obtains directions from actual RTL and accepts the current plan pin layers. Cohort owner confirmed canonical working ck10 uses this exact adapter. Restored flag; generated own fresh kit on intel2 with fleet Yosys0.68,9122pins,207.36x164.16. Personally LOOK-viewed xrt3_pin_plan.png: PASS-CONDITIONAL synth/place only. All faces densely occupied; no macros or interior obstructions. Frozen actual outline and pin positions retained. Dense M6 bands need actual placement/routing evidence. No route authorised by this pin-only image. Source RTL SHA59a53960b2c66851b14fbfcc615e451d380774ac483f2987a5f806abeb0cffa9 matches f6db9345e lockstep.
