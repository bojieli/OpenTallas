Qwen v1.4.3 ECTL binding uses HXK13 (head8 + G3S2 five stages). Full native attention numerical evidence is source-pinned at 22ff95ba0, receipt g3s2_composition: 53/53 contexts exact; HXK5 silently wrong512/512; numerical and timing mutants reject.

The new production control bench uses real mapped SRAM at RL21 and checks every one of256 requests, row consumes, score tags and80-edge score ages. Positive passes; HXK5 mutant fails first score at109 instead of117. These are control/component checks, not a whole-die qualification.

A/B actual synthesized netlists at h5 and h13 are byte-identical. Reuse is source-proven; B CLOSED+nativePASS. A is CLOSED but native capture221.0ps fails190ps on913 inputs, so A reuse remains HOLD and needs a structural pin-capture successor. C changes the score-delay state and needs a new source-bound route/native audit. No closed h5 C view may be used for HXK13.

C saved-CTS GRT trial at exact d54d27c2d has zero overflow,15.81% total track usage. The congestion PNG was rendered from that actual zero-overflow log and inspected. Fresh source guard53efc860b CTS gate repeats the same positive clock/timing figures; this lint-only correction does not modify RTL, geometry or mapped netlist. Old gate receipts remain in source_binding_history. Final TT/FF/DRC and native gates remain required.
