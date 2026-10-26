# Current VP local storage mechanism

The current VP with two actual `ot_sram_1r1w_512x128_m4_r0c0` models passes all49 genuine entry-row commits,16 HLOAD HW beats,8 GAIN WL beats and one RDOUT low128 read. The original bound entry image supplies H rows0..31, gain64..79 and delayed pre1008 of sid0/leaf0. Row1009 is not initialized by this input, so RDOUT upper128 is deliberately outside this receipt. The selected input preserves its original image hash and input provenance. Flipping row13 bit5 at the actual VP input causes commit and HLOAD mismatches and a failing verdict.

An input changes5ps after rising edgeN. Commit/output ages count rising edges fromN; the exact clock period is833ps (416ps high transition,417ps return). All49 row commits are atN+2. Last HLOAD HW isN+20; last GAIN WL isN+12; RDOUT low128 isN+5. These are local pin events: no ring, XRT, bound transport or consumer stages are included. The fixture uses actual numerical input rows and real storage/VP arithmetic RTL; it does not execute NORM or establish model-token numerical correctness.

Effective parameters are explicit: ML7,AL6,HPL33,HI/HO stations0,CS_H_G4,HQX0. The canonical read_slang JSON omits full-body parameter metadata, so `vp_params.source_audit.json` separately audits the exact structural input and every leaf caller; no historical timing/default guess is used. Result stamps both source graph and bound top hashes. Build took133.8seconds through ot-run8GB/2threads; positive and payload-mutant are finite simulations. Neither this receipt nor the parameter audit qualifies physical timing or adopts a token rate.

Reproduce on a fleet host from this repository root via ot-run (choose a fresh output path):

```sh
python3 tools/s81_dv/vp_local_1026/gate.py \
  --entry-rows results/token_pass/vp_local_1026/genuine49.json \
  --params results/token_pass/vp_local_1026/vp_params.source_audit.json \
  --out /srv/opentallas-scratch2/claude/vp-local-replay-new
```
