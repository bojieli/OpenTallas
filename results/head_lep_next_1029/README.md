HEAD LEP successor — original-netlist retained matches

The old functional residual was a correspondence mismatch: synthesis folded
s2v into ok_f, whereas the discovered gold relation used its other p_take
copy. The untrusted equality between the two matched copies proves
inductively. The four physically retained alias FFs were matched against
interchangeable replica names instead of their exact kept demand. Explicit
one-to-one matches fix retention without changing RTL, cells or cycles.

retained_alias_receipt.json: all 49,078 obligations proved; no differences;
all 5,160 declared kept bits present, none constant. The deliberately inverted
ready match is rejected (127 differences), including the wrong hint itself.
This diagnostic uses the actual original kit gold/gate AIGs; input hashes are
in the receipt. It is not a physical signoff or canonical kit receipt.

head_collective_lec_hints.py emits nine ordinary untrusted hints, now written
by the LEP kit driver. Existing lec.py proves/drops them normally. The same
helper accepts explicit lane prefixes for other HEAD collective instances.
No source arithmetic, pins, reset timing, latency or clock constraint changes.

Original failed formal/geometry evidence remains intact. Trial7 fixed DPL and
registered reach but fails channel estimates (H1.022/V1.595/column1.102), so no
route was submitted. See the actual image and results/geom_review record.
A wider W-margin macro proposal is being planned separately.
