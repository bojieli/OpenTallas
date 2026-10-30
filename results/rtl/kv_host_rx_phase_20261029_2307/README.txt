TOK-KV-7 conditional calendar-offset repair, 2026-10-29 23:07 PDT.
Base5fa3362df2c. Production script now exposes existing compiler --ofs through
D2D_CAL_OFS; boot recipe forwards OT_KV_CAL_OFS through flags/compile.env.
Unset/zero retains original image exactly. No current bind/boot image adopted.

Native source anchor coupon: exact bc4_rom64 tile (EP_SKEW3), normal compute
sequencer (EP_SKEW0), same forwarded epoch through actual5 regs, profile72/1253.
Verilator unit2860221 intel1: Kcal203/Ccal205, C+2 measured. ROM profile supplied
from existing dcal_h153 actualmap; original source files named by run_anchor.sh.

Actual HOST typed producer + native SFM SRAM link sender + registered pair of
UCIe macro models + normal compute link receiver, clock833ps:
unit2906294 intel1 /srv/opentallas-scratch2/claude/codex-kvtok-2249 terminal0.
Aligned calendars, arrival172: exact548 payload PASS nofault.
Compute calendar +2, old arrival172: actual unexpectedRX08 abort CAUGHT.
Compute calendar +2, corrected arrival170 (--ofs=-2): exact548 PASS nofault.
Only route registers/interface stimuli are modeled, no force/backdoor.

Candidate production-image compile unit2989592 terminal0 on bindWc stages
90,90,88,88,88,77,77/HRT153, MU/rope/emb1627/head12/attentionpad86:
zero is byte-identical to TOK-KV-7 mu833_B3b image (cmp PASS).
Zero seg2 K HOST RX C172/173; C WITNESS RX K1247.
Offset -2 seg2 K HOST RX C170/171; C WITNESS RX K1249.
TXDP unchanged C8,3,1,10/K169,157,3,3.

Full inherited FAROBS still live. First actual far new_fault/anchor values must
confirm this source-measured mechanism before choosing/adopting a signed offset.
No full token, G5, timing, signoff or measured-rate claim. No production RTL edit.
