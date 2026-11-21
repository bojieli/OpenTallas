# S81 retained J5 placement review before pre-CTS remeasurement

Viewed layout.png and density.png from these exact attempt directories in the J5 kit wave (event 224567138ab).

- epyc9 col_h10_r2__t1__cl1f5d6c2a__pvec003743 attempt 6. Separate east-west seams and central channels remain around the banked ROM halves. 0 opposite-face pins, max sliding face window track demand 16.3%, local peak 79.4%. The two fanout areas are at the collector spine and S stubs. PASS to the corrected ideal-clock place read and diagnostic CTS when the existing setup guard passes. GRT and DRT are separate work.
- intel1 slice_station__t45 attempt 3. Eight N-face status inputs (strap_ca_k_dn_s_2N_L0x5_i, strap_ca_efall and strap_ca_pad) land near the opposite S quadrant, with fanout spread 1792.7 µm and 77% peak at narrow edge banks. FAIL retained J5 form. Revisit J6 monitor/START placement and give the actual opposite-face status legs their own relay rows before route.
- epyc7 ot_s81sl_leaf__t28 attempt 10. VP/VN and adjacent core banks form a crowded wall across the west and lower third, 98.5% peak local density; the northeast is mostly empty. FAIL retained J5 form. Continue the FT-aware per-lane regrid from leaf lever2 before route.

Exact image roots are /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/224567138ab/items/<type>/attempt_<n>/gen/<type>/run/layout_review/place on the named hosts.
