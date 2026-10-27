Native macro channel demand diagnostics, 2026-10-27

The exporter reads every signal net and every placed endpoint from the native
OpenDB view. The cut census counts nets crossing each macro column/row centre,
using M2/M4 free horizontal spans and M3 free vertical spans plus M5 over SRAMs
whose obstruction is M1-M4. Capacity uses the existing channel shares (M2/M3 0.5,
M4 1.0, M5 0.93 for PG). It also checks one track of clear outward geometric
escape from every native macro signal pin.

R7 vmdel: two SRAMs, 8,889 nets; H use 0.469604, V use 0.180141.
Programme pslice: 100 SRAMs, 161,081 nets; H 0.327458, V 0.549502.
Both satisfy this necessary cut model; neither result is routing qualification.
Vmdel already has a separate successful GRT50 probe. Pslice needs its live GRT.

Negative control: the old EP route1 view passes the same necessary cut test
(H 0.248162, V 0.295184, four SRAMs, 36,079 nets), despite its retained GRT failure
(64,245 overflow). Thus global cuts and immediate escape cannot certify local
pin access, fanout congestion or a zero-crossing internal-seam assumption. The
new mirrored EP macro plan must still be placed and globally routed.

The source ODB paths and SHA256 values are in each summary. Raw native net
exports and complete net-name cut lists stay on intel2 under
/srv/opentallas-scratch2/claude/codex-hbm-channels-0812. Summaries omit those long
lists. No zero-crossing declaration, pin-access PASS, sign-off or freeze is
claimed. These diagnostics explain why the old blanket 10.8-um rule cannot
stand alone; the demand-aware check and real router gate remain separate.
