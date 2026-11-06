PREPARED ONLY. No GEN/P&R job launched.

Full top: ot_pdie_serdes_tx, ELA=2, EFF=1, PMA_LAT=4, EMUT=0.
EFF is trailing default0 and explicitly routes FF(EFF) to the LA2 encoder.
Dormant recipe ot_pdie_serdes_tx__ff pins all RTL/header inputs to implementation
commit dc98564b80a (full SHA in recipe), adding only the FF matrix header to the
canonical TX file closure. Canonical ot_pdie_serdes_tx remains ELA2/EFF0, pinned
at f163a41643581ede8cb1337b44cbd7f6adfef513; no POR/plan source activation.

Use the approved current clean factory checkout after root adoption. Invoke:
  bash gen_full_tx_ff.sh CLEAN_REPO APPROVED_TX_VIEWS_JSON FRESH_PRIVATE_OUT

Known same-slot views template (intel2; root may provide a newer identical slot):
  /srv/opentallas-scratch2/claude/codex-hbm-tx/views.json
It references approved prior tall plan:
  /srv/opentallas-scratch2/claude/codex-hbm-wave/d44v35/die_plan.json
View ot_pdie_serdes_tx@c77a41179db8. Outline285.12x207.36 um. Plan pin SHA256
c77a41179db8d42df9aff5ccbe509375cdd8ff847abb46ece500cbdd92e42408.
1059 plan pins; one clk at[142.584,103.68] M5; rst; no macros.
Preserve ordinary one-edge input/output face registers, same clock/reset model,
833ps clock,250/202.5ps TT/FF IO budget, M6 maximum SIGNAL routing and M5 PG.
This does not opt into M6 PG. No parent pin/outline or reset-stage change.

Before P&R: verify generated freeze params ELA2/EFF1, no dropped pins, macro-none,
same outline/pins/clock/period; render and review the ACTUAL generated image;
root owns source/geometry adoption, stand-alone netlist LEC and physical trial.
Run any real GEN/physical work through normal ot-run admission on verified
DEDICATED filesystem. This script intentionally performs no ot-run submission.

TOK HBM-48 final conditional ACK: one encoder/native common-clock PMA544-bit
cohort edge (.833ns per traversal),544bits/edge unchanged,fault0. No per-word
accumulation. Full native PMA top comparison:3914 full544-bit words incl frame
boundaries after warmup; same clk/rst/tx. Excludes initial<=40 and reset/drain
1800..1845. Encoder stall/reset separately4952words/494parity/2epochs. Neither
bench instantiates arbitrary serializer/gearbox phase or physicalpin arrival.
Common-clock face registers preserve relative one-edge shift algebraically;
the3914bench itself does not separately instantiate generated face shells.
