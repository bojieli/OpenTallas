# qkd_d2d_static_ovl_sfm3_cf4

Actual qkd_d2d_static_ovl_sfm3 selected9ee754c2d. NTX3/TXDP0x03030416/SAFE_RC1/SRAMV2/FEG1. Same ports and functional edges. No scalar alias or timing waiver.

SAFE DESIGN: pins PR1; por_n/rst_n two-stage landing. Fanout: kept control copies; mandatory exact mapped native census must pass before placement. Storage: four64x137 SRAMs,1kb calendar flops per controller. Reach and logic depth: source same stages; measure actual mapped/placed path reach in gate. Floorplan: 561.6x345.6; 43.2-lattice macro origins and full-width standard-cell bands. MAIN literal pin density S4.758/W4.339per um; fallback spreads all pins. Clock: ck, route770ps/signoff833.333ps,60/25ps uncertainties,166.667ps IO budgets,30ps hold margins; actual TT/FF pin-flop spread required. Schedule: zero added edges, token owner notified. All measured obligations remain OPEN until current gate, old receipts are not authority.

Source repair removes one absent predecessor source-list file; complete current OVL hierarchy/native census must prove no missing reachable body, with no stub introduced.

Measured predecessor failure: max33 on TX/RX high pointer advance (32 paired loads plus phase bit). Kept run_p has the same D/reset as running and feeds only phase advance. No new data/control edge. Existing FO-copy assertion includes run_p; real miter and causal negative required. Native32 not yet claimed.

Pin successor cf4 explicitly aligns each preferred coordinate to the actual cf3 DEF track grid (M4 horizontal/M5 vertical origin0.012 pitch0.048 width0.024). All4896 identities, directions and clock/reset ports remain. Outline and endpoint edge law unchanged. Actual placed-IO check still required; see pin_track_recipe.json.
