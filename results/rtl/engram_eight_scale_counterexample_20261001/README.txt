Source-pinned unchanged-RTL counterexample, synthetic payload only.

witness.json reports two distinct verdicts:
PASS_COUNTEREXAMPLE_REPRODUCED means the bench successfully demonstrated the defect.
FAIL is the unchanged gather's actual eight-block-scale codec verdict.

The bench uses NL=1, NC=2, 8 beats, 32 lanes, 264-bit responses.
Column0 has eight heterogeneous scales; column1 is a uniform-scale control.
It checks every lane, all16 writes, and slot completion. An independent direct
instance of the unchanged decoder correctly distinguishes scales127 and128.
The runner derives expected BF16 values by executing only extracted, pinned
representation/Engram decode functions on small synthetic NumPy arrays.
No checkpoint, tokenizer or model initialization is executed.

Existing shipped campaign results remain byte-identical. Its synthetic
row_bytes returns one scalar scale per row; that verdict remains scoped to
one-scale rows and does not qualify actual eight-scale checkpoint rows.

Mandatory baseline correction: each beat's side byte belongs to that beat's
32-code block. The transfer remains eight264-bit beats per row, or192 beats
per24-column layer. This is a transfer-count contract, not physical timing
or area/route qualification. Engine correction remains gated on Ram's full
port/area/route budget admission. The optional1% performance gate does not
apply to baseline numerical correctness.

Do not overwrite this recorded failing verdict. Replays must use a fresh
result directory (change OUT in a separate runner revision) and keep this pin.
