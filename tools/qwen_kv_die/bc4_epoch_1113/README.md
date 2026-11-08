# Current pair profile and R8 BC4 epoch join

This private source packet makes ROM content explicit for the actual selected R8 BC4 controller. It changes no RTL default, physical view or plan. The R8 physical registry points to a default position2144b19/content via map that is absent from its referenced source tree; it does not prove which functional payload a future token run selects. Every committed old profile has ADM_LEN1100/FIRST1176. The current pair image carrying TXDP_K03949da9 instead declares ADM_LEN1270/FIRST1346.

prepare.py extracts all36 starts and8 scalars from the actual pair image and generates a64x32m2 ROM payload with the existing macro compiler. The payload and actual66 boot writes come from the same image. epoch_calendar.bind_image_profile refuses a stale or mismatched profile. No SRAM/ROM protection or physical timing assumption is changed.

The focused test uses the selected ROM64 alias, actual synchronous ROM model and frozen native BC4 core. A literal BC4 loaded with the same pair image supplies the independent public-output comparison. Three real epochs cover initial boot, halt/recovery, reload/reboot; all66 boot records are delivered. All53 public outputs match. The stale-duration control produces522 differences and starts a token170edges early even though its BASE indices match. The actual native MUT1 dropping runtime BASE switches is caught at all3 token starts.

At833ps, for an actual sampling edgeN at the original D2D public fwd_epoch pin:

| Actual R8 BC4 event | Native source sampling edge |
|---|---:|
| u_dcal epoch input | N |
| Admission cal_start | N+76 |
| Runtime TX BASE switch | N+1346 |
| Runtime RX BASE switch | N+1347 |
| First token cal_start | N+1349 |

These dates are specific to the bound1270/1346 profile and EP_SKEW3/GO_OFS0. The tool derives them from profile values, not from reset timing.

The current R8 SYS_C source directly wires u_dcal epoch_go/halt to D2D fwd_epoch/epoch_abort. RF adds one output capture before BC4 and one input capture on the returned CFG/cal_start cohort. The extended native vehicle measures the controller input atN+1, admission atN+78 and first token atN+1351 at the D2D control input. Both captures must be priced. CFG and cal_start move together; the runtime RX BASE retains exactly2edges of settle lead. This local law supersedes using the old fixed-external-start +1 projection for this feedback path.

The original D2D fwd_epoch event's date relative to a package epoch and the C endpoint remains an explicit unresolved caller/clock input. No global K-minus-C offset, token-period charge, full HOST admission or G5 pass is inferred. The current physical RF form is still a private proposal.

Actual records: E4 /srv/opentallas-scratch2/claude/codex-token-1113-bc4-feedback2, unit4053578-1794166866; results/token_pass/bc4_epoch_1113 contains the log, profile, inputs and source/receiver calendar. The first epoch-only run also passed (unit3677858); an intermediate feedback build had an escaped macro syntax error and is retained in codex-token-1113-bc4-feedback (unit4014565, terminal1). The fixed successor is the recorded pass. Initial I1 request was cancelled only while unstarted/load-held; it never ran. No healthy job was restarted.
