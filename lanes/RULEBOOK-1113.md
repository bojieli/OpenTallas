# RULEBOOK 11-13: family design rules set by Fable expert lanes

The owner (11-13 03:4x) asked Fable expert lanes to set the few family-level physical design rules that keep recurring, once, up front. COORD and every lane follow these rules. Each rule has an ID, the rule, why, the implementation (tool and sha), its proof kits, and the dies and types it touches. Only the owning Fable lane edits its own section.

Expert review evidence: ~/coord/lanes/EXPERT-REVIEW-1.md

## R-CLOCK (HOLD-TAP-1): cross-tap insertion balance for zero-logic and low-logic pairs
## R-RTL (HARD-S81-SERDES-1): pipelining depth for paths over budget
## R-STREET (RULES-STREET-1): macro and pin-face streets, congestion escape
## R-REACH (RULES-REACH-1): fanout and reach locality, face-net buffering
## R-CAP (RULES-CAP-1): partition size, cell cap, outline sizing
## R-FLOW (RULES-FLOW-1): ORFS flow settings for slew, DRV and early buffering
