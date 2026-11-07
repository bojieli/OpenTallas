# Prompt vJ2 channel redesign

CLASS: CHANNEL. GEOMETRY: vJ failed DPL on exactly one BUFx6 wire37556 at (177.926,62.306), inside the large SRAM. No placement regions/blockages remained. The SRAM top is75.54um; program row begins81.036um: gap5.496um, less combined4.32um macro halos. That channel has no legal cells. East-side landing is about41um away; the central column above the SRAM also needs about34um horizontal displacement after halos. Both exceed DPL's500sites horizontal search reach of27um. The new gap offers a landing about18um north at the same x.

REDESIGN: move all four program SRAMs +11.52um north (240 M4 tracks). The large SRAM/program gap becomes17.016um with about8.376um of legal standard-cell channel. Preserve macro orientation/pin track phase, RTL, outline, core IO, clocks and constraints. Fresh placement redistributes logic around moved macros. This is a macro geometry change, not a DPL search knob retry.

SMELLS: 3 addressed by new legal channel. Northern logic remains dense but spread0.4-0.5 over its active area; pin faces have inherited edge concentration. SRAMs remain south away from clock entry and top-face host logic. The program rows now end at133.43um; placement must demonstrate they do not create a new clump in the northern logic before route. Other narrow program-row channels remain inherited routing-only corridors; no new buffer landing relies on them. No route authorization until placement image review.

Viewed vJ_failed.png (actual failed DB) and vJ2_plan.png (proposed macros over actual vJ logic; logic is shown as context and will be re-placed). Planned legal channel highlighted. Target first pilot PLACE only.

RTL byte-identical to vJ. Added PIN CYCLES vs vJ:0. Inherited +1 read response cycle and +3 reset-release cycles retained. Existing B8 read-decode/reset exact proof and mutant controls remain applicable; new kit synth LEC is still required.
