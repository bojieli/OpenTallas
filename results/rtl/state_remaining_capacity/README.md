# Retained remaining-capacity candidate

Each allocated non-saturating slot retains the 33-bit unsigned difference
`capacity - cursor`. Bit 32 indicates underflow. Admission rejects underflow,
then compares requested span against the low 32 bits; unstaged policy compares
only underflow. Saturating policy bypasses this metadata entirely.

Allocation initializes metadata even if the first operation is refused, matching
existing slot allocation behavior. Existing apply capture/product stages compute
the difference using the next **32-bit stored cursor**, preserving cursor wrap.
Retirement updates cursor and metadata together. Reset/clear invalidate slot_used;
metadata payload requires no reset. Discard without retirement preserves both.
Multiple staged commits still check the committed cursor, as required by the
existing interface. The tests probe admission again after repeated retirement.

The baseline is state_apply_counter. Production RTL remains unchanged. See
comparison.json for synthesis/STA and test evidence; no clock closure is claimed.
