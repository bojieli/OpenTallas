PHY-up receiving synchronizers, source-only successor (2026-10-21).

The actual UCIe-up producer runs on clk_ucie while the two consumers are face0
and face1 codec controllers, normally on clk_coll. The previous SAFE controller
had one up_q sample; PLAND first wrote raw p_tx_up into its PHY-side ring.

UP_SYNC=1 supplies two kept ASYNC_REG flops independently in every face:

* Ordinary codec: p_tx_up -> up_meta -> up_sync, clocked on that controller's
  codec_ck[0], then its existing diagnostic sample and fault logic.
* PLAND codec: p_tx_up -> up_meta -> up_sync on that face's codec_phy_ck
  (codec0p), then the existing u_rx_land ring to codec_ck[0]. The receiving
  controller does not add a second redundant synchronizer.

The parameter is threaded through production parent, five-face parent, face,
and codec wrapper. It defaults to zero. The two UCIe consumers have distinct
local capture registers, as do the three SerDes consumers. There is no global
clock copy or new credit/issue gate. Keep/dont_touch preserve the local copies.

Status observation/loss diagnostics gain two local sampling edges; packet issue,
TX/RX latency and the fixed data calendar gain zero edges. The new status flops
are unreset, like the existing up_q. They initialize after two sampling edges;
no new ready signal or invented boot-ready time is asserted. Existing reset
validity and actual startup scheduling still govern when traffic is observed.

Source base is 3210325f8 plus the current-main parent context. SAFE/PLAND/PLD/PLK
pass-through and codec_phy_ck wiring are included because those wrapper updates
were not yet in the committed 321 source. This is a future source variant;
paused source worktrees and progressing PLAND kits/gates were not edited.

source_intent.json records exact source hashes and per-face producer/pin/root
identity. It is explicitly unqualified source intent, not proof that a successor
is bound or closed. Current GEN ucie_up C1 remains a failure until UP_SYNC=1 is
actually bound with these source hashes and the two receiving FFs are observed
by the existing native binding/closure flow. No blanket fact suppression or SDC
exception is added here.

No new gates, tests or audit campaign was launched. Parent coordination is
required before producing successor face kits/gates. New face kit parameters
must include UP_SYNC=1 (alongside SAFE/TOK_REG and PLAND where used); old
UP_SYNC=0 closed views are not interchangeable. Place the PLAND synchronizer
flops in the real codec0p PHY row band and preserve its existing ring boundary.
