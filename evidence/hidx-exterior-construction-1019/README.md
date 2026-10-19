# HIDX fixed-site exterior construction: terminal FAIL

Finite source-only construction on exact site_plan SHA0c7ca2c997ea6198b149a9fe7007efdadff19264f6966847c8ef7e8997020075. All11449 native driver nets and31384 real contact access points retain their source graph/order; no cell, row, fixedpin,PG,outline,or functional edge moves. All504rows,104-row Y56.16..84.24 sourceband and140.4um outline retained. Existing source density80.8/67.05/61.625% remains HOLD. No physical authorization or engine run.

The finite attempt assigns one concrete Hinterval pernet.5465 actual short edges (root RMSTpath<=3um,Yspan<=1.08um,allcontacts inband) stay inband;5984 nonlocal/boundary nets select north/south exterior Hbelts by total actual contact vertical length. Longer intervals allocate first. Hcoordinates come only from the prior conservative actual-PG-clear ledger, with128 concrete Hclock-source coordinates reserved; M4 receives priority at equal verticalcost and M2 provides overflow. Each real contact then seeks the nearest PG-clear M3 coordinate whose expanded vertical interval is not owned by another net. Hintervals are rechecked after those actual M3columns extend the trunk.100nm endguards are explicit conservative source construction bounds, not an exact native DRC rule.

Terminal results:

| Check | Result |
|---|---:|
| Htrunks assigned |11449/11449|
| Native-contact M3leads assigned |21548/31384|
| Unassigned M3contact leads |9836 across2963nets|
| Hextensions colliding after M3ownership |574nets|
| Native cap exceeded with only assigned wire |TT278 /FF280nets|

3501 unique nets have an explicit construction failure. The assigned partial geometry inventories63385 base native vias; fulllegal via access is OPEN. Every unassigned contact/collision is preserved in output/verdict.json, with per-net coordinates, actualnative driver, ownership, source/output cap, length and defaultvia inventory in output/per_net_geometry.json.gz. No missing contact is silently dropped from the verdict. This is a FAILURE OF THE FINITE GREEDY CONSTRUCTION, not a proof that every alternative routing is impossible. Partial wire/cap rows are explicitly marked incomplete and undercount missing wires/viafringingcap; they cannot qualify any net.

First vertical failure: native BUFx8 wrapper_output_quad_select_137/Y, net9842, source contact(130.718,69.084)um to M4belt y7.992um, vertical interval7.992..69.084um has no free M3column under existing ownership. First extension failure: net11128 H M4y4.968um, native span104.906..129.624um extends to104.184..129.624um after native M3ownership and collides with an earlier owned Hinterval.

The all-PG conservative projection supplies M3 2627coordinates; M5 2575 were counted independently but are NOT used as signal-owned leads in this finite attempt. No M3+M5 success is inferred. The native PG collector and routing/cut/PGcontact shapes are unchanged; the exact geometry/hashes are a dependency of input/pg_ledger.json. Base native vias distinguish internal M1(VIA12/23), fixedW/E M4(VIA34), fixedN/S M5(VIA45/34), then VIA23 orVIA34 into the chosen M2/M4trunk. Real source-loaded cap uses tree.corner_cap.native_plus_external_fF, preserving80fF on every actual output; loaded_caps.json.gz is retained as pinned upstream evidence. Added assigned wire uses native setRC C M2 .174942, M3 .155554, M4 .178475 perum in the loaded toolunits. Viafringingcap is OPEN, never treated as a provedzero.

Sourcepin legal M1via landing, exact localM2/M4jog ownership, port boundary extension access, signalvia cut staggering/DRC, actual clock structure/phases, source native Dcalc, setup/hold, all-PG conductor connectivity and physical timing remain OPEN. No new iterate, placement,CTS orrouting is requested by this packet. Structural changes require later coordinator direction.

Resource receipt: source/invocation/inputhashes recorded BEFORElaunch in PRE_RUN.json. Identical assets staged ep4/5/6/7/8; unpinned ot-run16GB/2threads admitted ep7 as oth-ubuntu-185973-1792450191, actual RAN exit0, measured maximumRSS114992KB. Exit0 means the model finished; its verdict is FAIL. Source script construct.py, every consumed input and complete failure/geometry outputs preserved.
