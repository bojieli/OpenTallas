Verdict: PASS-COND for DISABLED model proposal only; no physical release.
Picture: candidate_look.png, rendered with the existing plan_review.draw_base,
then inspected directly. Die coordinates include the actual MY orientation.

The new magenta277-cell CB bank lies on the existing horizontal CB data-flow
corridor between its first two internal banks. Existing banks, pins, type
outline, neighbours and clock entries stay fixed. T48 is a singleton bridge
with no placed macros; no macro halos, walls or notches are introduced. The
extra bank has clear space between existing station columns. Input/output pin
windows and bus ordering are unchanged. No new seam/channel demand is added.

The midpoint proposal fails the existing150um clock radius; those failed model
attempts remain in report.json. The selected allocator result is near local
(955.835285,579.865939), using existing clk_t8. Its longest new data neighbour
hop is265.95um (<405). clk_t8 load rises554→831 (<1500), radius143.0142um
(<150); all20 clock ports and their coordinates stay fixed. Reset/START and
clock-driver envelopes, every existing planned station cell and macro halos
were reserved through the existing RowAllocator. No existing bank was moved.

PDN geometry and routing layer budgets are unchanged; continuity/IR was not
re-measured. This is a planner-site review, not a placed/routed design. GEN,
actual cell footprints, complete clock/reset native counts, hold/setup and
independent review are required after the die-owner plan event. No STA/P&R,
bind or adoption was launched from this proposal.
