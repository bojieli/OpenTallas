# SF7W2 immutable CLOSED collection

Source job qfd_d2d_static_sf7w-sf7w-c3baef180, RTL source c3baef18051e, closure-record 371a905574f6070be8394553060e49077a7b449d. Only the record commit's 30 immutable view/receipt files are imported; main helpers, kit and RTL are unchanged.

TT setup +140.30 ps, FF hold +11.64 ps, DRC 0; SS setup -185.73 ps sensitivity. Later owner option B (signoff-corner-tt-option-b memory) accepts TT>=0 / FF>=0, 833.333 ps, 60/25 ps uncertainty. This is TT/FF qualification, with SS sensitivity reported.

Read-only native PG audit on the original 6_final.odb: PASS, 512698 terminals checked, failure_count 0. ODB SHA256 verified against corner_sta.json: ca690ee2a3576a871246cf1940eec47d92d6f47ddcfd213c97da87b61a305808. Audit tool is main physical/common_flow/audit_native_pg.tcl + native_pg_binding.tcl, run via unpinned ot-run on the data-local ep7. No ECO, no saved-ODB mutation.

Native own-reference PASS: launch 168.7 ps, capture 105.9 ps, 0 over, 0 comb, pin-flop spreads TT50.0/FF46.4 ps. Candidate parent compensation TT318.9/FF262.0 yields boundary mismatch TT27.3/FF25.5 ps and native PASS. This is an explicit proposed parent compensation, not evidence that a generated parent has adopted it. GEN/GRT owner must adopt these references or re-audit against its actual neighbour before release binding.

Final floorplan/density PNGs inspected: four SRAMs in a single aligned row, full-face pins, clock N-centre; dense logic along pin faces, open continuous std-cell region. Outline 388.8x172.8 (aspect2.25): inherited coordinator-approved pin-bound outline, not a fresh safe-square claim. Child lint PASS, VDD/VSS M5 stripes 99% spread/100% coverage; face pins blocked0, pockets0. Existing coordinator review geometry remains the authorization. Final fill .272 is pin-bound; no squeezing was performed.

The source-pinned route passed all 11 daemon benches including 8 causal negative controls. Immutable original failures and witnesses remain intact. No route or behavioural rerun was needed for this view/evidence import.

Final actual-Lib all-driver audit: 57777 drivers; 56245 data/control drivers max32, 1532 constants max1, no over32. Max transformed native pin-bbox L1 upper365.976 um, no over405. 759 clock drivers counted separately (max11975 clock terminals); 207 floating load-only outputs all have corresponding actual-Lib clock-role input proof in open_clock_loads (asserted by instance, no name-only waiver). OriginalODB hash matches. All 512698 PG terminals bound. Audit script/actualLib hashes and native summary retained; complete rows remain immutable remote at /srv/opentallas-scratch/codex/qw-leaf-closure-1020/pg/native/rows.json.
