# rg1 terminal gate failure (original pinned work retained)

Recovered original ep5 run smh_xs_ring_1019-20261019-080125 execution.log through recover_gate_result + the same live layout parser; archive/source/script/executed-helper hash verification PASS. No physical rerun. Original signoff regeneration delta is committed e6b26a86e.

- TT setup+17.844ps / FF hold+34.786ps at placement RC; GRT overflow0. No SS-only rejection.
- TT/FF pin-flop spread270.0/225.6ps FAIL; insertion596.8/481.7ps. Largest root14863sinks,14855flops,8SRAMmacros.
- Cell area8629um2 + hard31133um2; totalfill27.2% (coordinator accepts lowfill due lattice/macro channels; automated fill checker stillFAIL pending explicitspec reason).
- Pins4543 alltrackaccessible,0outside; reset rawrst_a reaches1flop before explicit2stage landing; logicdepth281.7ps/7levels. Staticstrapcopies still512loads, so safe item3needs replication.
- PNG density inspection: standardcell mass is at Sface and around macro channels, with sparse Nface output cells; this is one contiguous region, not isolated power islands. Macros all43.2lattice with34.776/45.36um channels; N/S/W/E totalface densities below6/um.

Clock source bug classified: ot_sv_build stops early at singleton subtrees but ot_sv_stages counts wire repeaters only, not each recursive node/leaf buffer. Emit never deducts node buffers. Equal-stage claim therefore fails on unbalanced sparse bands. Successor must count and pad actual node+wire stages and prove it on an unbalanced tree. Add opt-inCK4 keptstrapcopies (old64) so~512loads becomes~32; same3startup/dataedges. Root authorized both structural changes before rg2.

SAFE8 status:1fixed/resetPASS;2tile<=432x345.6 and placedreachstillneedsactualtimedendpointreview;3FAIL512staticstraploads;4PASS281.7ps;5FIXEDSRAM;6lattice/channelsPASS,lowfillwaived;7FAILspread;8PASSzeroaddeddataedges. Do not REVIEW or submit rg1.
