M8/M9 clock-wire successor to the M6-port mechanism vehicle.

Actual clock BTERMs clk/o0..o3 are on canonical M9 tracks and M8 cross-grid positions. Access islands were published BEFORE routing from actual BUF24 bounding boxes: 4x1.4um per standard clock cell. Port regions are exactly the native M9 BPIN boxes; no port halos or wire-derived waiver regions. Green island boundaries appear in the viewed review image.

Reproduction: copy shared tools/die_plan/{infra_mesh_connect,infra_clock_route,infra_clock_audit,infra_connectivity,infra_replay}.py beside the fixture. Run generate.py and prepare_straps.py; through ot-run run_build.sh builds a bare-straps ODB. publish_access.py writes the pre-route access contract. run_connect_sharedfit.sh invokes the shared connector: native first-via enclosures must fit inside actual pin metal; it adds 60 native vias without access jogs and checks actual connectivity and nominal fixed-metal clearance. Through ot-run run_shared_audited.sh invokes GRT50 + actual DRT + mandatory decoded-layer audit. run_exact_audit.sh reruns only the corrected point-delta audit against the existing routed ODB.

Result: connected clock/PG, DRC0, lower clock metal only in each net's own endpoint cell islands/native pin boxes, exact regular M8=85.016um and M9=153.680um. Post-route nominal metal clearance for all eight infrastructure nets also passes. No timing, skew, IR or physical-freeze claim.

The original clock_layer_audit.json is retained as raw first-run evidence. It used dbShape.getLength(), which is 20nm shorter than the decoded centerline at each of five zero-endcap BTERM endpoints. exact_centerline_audit.json uses dbWirePathItr path.point/entry.point deltas and reports the corrected 100nm total; geometry audit remains PASS. The independent point decoder and post-route clearance results are under ../clock_wire_audit/m9_successor.

Negative controls are under ../clock_wire_audit/old_m6: old DRC0 M6-port candidate fails clock access audit at clk/o0/o1 ports (all cell-local paths passed). The old 68-via largest-pin landing candidate fails eight fixed-metal M1 clearance checks; proper enclosure-contained vertical Y pin landings fix the source.
