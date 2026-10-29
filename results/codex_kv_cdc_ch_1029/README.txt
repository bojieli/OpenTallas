CDC_CH private control preservation, zero cycles; opt-in source helper.

Exact root causes in baseline actual synthesized fixture (source70c0af856f):
- u_done/u_ing i_cr are kept boundary FFs. Internal SAMECLK FIFO swv FFs
  have identical D/reset/clock and were unkept, so synth merged them INTO
  those kept output FFs. Their internal consumers then loaded the faces.
- u_done/u_ing o_v are already private FFs, but kept dead g_ops2.ovp aliases
  caused real BUFx2 loads on those faces.

cdc_control_preserve.py adds keep only to the two internal swv FFs and
removes keep only from the two otherwise-unused o_v aliases. Actual output
FFs/ports remain kept. Attribute-stripped original/fixed RTL is byte-identical
(receipt attribute_identity.json). No clock, data, reset, interface or cycle
change. Extra two physical FF copies; remove two unwanted alias buffers.
Nothing is waived and no constants are classified as valid faces.

Actual full-shape synthesis: mapped-netlist AND synth-ODB CORE_PREFLIGHT
PASS0 failures,1205/1205pins. Original shared4 verdict stays in its original
fixture and baseline_face_guard.json. Fixed fresh diagnostic output is at
intel2:.../codex-kv-phy-pad-1028/cdc_ch/kits/qkd_hr_cdc_ch__319.68x319.68.
ot-run unit2020445-1793258396 exit0. Yosys canonical hook kept14 scalar
register cells vs baseline12. Tiny control-replica coupon PASS128edges,
wrong internal-state MUT1 caught; existing full face post/mut/emitted
functional proof stays applicable because only attributes changed.
No full proof rerun was needed.

Usage after normal hr_face_ports emits and proves its source:
  python3 physical/die_plan/qwen_kvsys/cores/harden/cdc_control_preserve.py \
    INPUT/qkd_hr_cdc_ch.v OUTPUT/qkd_hr_cdc_ch.v OUTPUT/attribute_identity.json
Optional member argument u_rx,u_tx applies the same control preservation
to CDC_PC. It does not remove CDC_PC's18 reserved constant output pins;
CDC_PC_DELTA.txt is a proposal only and current event23 is untouched.

For a signable successor: reproduce the normal current-plan extraction,
keep its proof receipts and the attribute-identity receipt beside the
patched source, then gen_core_kit_kv --hr-face-ports OUTPUT with a fresh
clock sink census/master slice and bundled plan_pins.json. Review placement
before route. The cloned diagnostic kit is NOT SIGNABLE (its freeze still
names the old source) and no timing/sign-off claim is made here.
