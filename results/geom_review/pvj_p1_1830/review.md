# Actual PV P1 independent LOOK

Image actual_p1.png personally viewed. Source is the newer17:22 actual5_route.odb from Intel2 codex-kv-pvj-1131/prd_b10_s40; exactSHA in input_odb.sha256. One4GB1CPU read-only OpenDB dump completed exit0; no DBwrite, repair, P&R, STA or new qualification.

172.8square,0macros: coherent perimeter FF ring remains, central/NW logic islands and SE reserve. No macro/channel wall. New actual cells are present, but this image does not compute pin/r2r/clock/timing/legality gates. P2 native legalization6overlap/6padding FAIL remains unchanged.

PASS-COND recommendation only for ROOT's exactsame-input repair-only failure-capture diagnostic; no DRT or timing release. Actual P1 contains46819FILL+65960DECAP allPLACED and3046TAP LOCKED. Check ordinary ECO filler/decap removal before legalizing newcells; this is a concrete lifecycle hypothesis, not an asserted cause. The six actual offending cells require the instrumented failedcheckpoint/legality report; baseline geometry cannot identify them. Bp2 job untouched.
