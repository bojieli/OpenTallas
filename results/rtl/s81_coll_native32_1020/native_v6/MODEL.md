# Native32 v6 arithmetic-before-launch source model

Source35c2bd90e restructures all three replay skip cones so late launch/pace
selects only ONE BIT. Arithmetic starts directly from the current sender,
UNA and registered ACK difference. No added register/edge/age/storage in RTL.

Let D=(sender-UNA) mod 2^W and L=d_ack. The no-launch predicate is L>D.
For launch, L>((D+1) mod 2^W) is EXACTLY

    (L != 0) && ((D == 2^W-1) || ((L-1) > D)).

For D=allones, the increment wraps to0 and any nonzero L wins. Otherwise,
nonzero L permits decrementing the threshold; `(L-1)>D` equals `L>D+1`.
Threshold decrement executes IN PARALLEL with the modular difference, and
launch then selects the already-computed result. This removes the serial
increment -> launch mux -> subtract -> compare path without a range premise.
The complete W10 a/b/L/inc 31-input relation is SAT proven in
predicate_equiv.log (Yosys0.68+post SUCCESS, no assumptions).

V5 explicit carry-prefix experiment remains REJECTED at733.5ps; no v5 logic
is reused. V6 does not alter v4's rewind/equality functions or share the
readiness comparator cone. Three kept independent modules isolate consumers;
all copies remain fully visible to the native BUF/INV-collapsed32 census.

Actual ORFS native source scout preserves the canonical keep-reg hook, TT
library, CH_BOARD700/770ps, and explicitly keeps the new helper module.
Native load/depth and full production source receipts are pending. No
physical gate or packing qualification. V3 depth621.8 remains historical
blocker until a source successor actually proves <=600 and native32.
