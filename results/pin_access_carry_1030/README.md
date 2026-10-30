GRT-only preferred access-point position carry — source PREP

This optional helper is not integrated into a runner or candidate. ROOT must approve its narrow scope before applying it to PC's existing GRT-only vehicle. No PC original/candidate, placement, STA, GRT or DRT was run or modified here.

Pinned OpenROAD 6cb3f2b704 dbInst::swapMaster clears preferred access points and resets pin_access_idx. Supported resize_cell reaches that same operation and may additionally move the cell during legalization. Merely using resize_cell cannot preserve this frozen geometry vehicle.

The installed SWIG interface cannot iterate MPin.getPinAccess, ITerm.getAccessPoints, AP.getVias or AP.getSegments; native metadata probes return opaque SwigPyObject values. A full AP payload/catalog copy is therefore not claimed. No old-master AP is attached to a new-master MPin.

GlobalRouter::findPinAccessPointPositions uses preferred APs for CORE pins when all_access_points is false and reads only point plus routing layer, translated by the unchanged instance location. The helper explicitly accepts only this scope. It copies those positions into APs actually owned by shape-matched NEW MPins, restores the same valid pin_access_idx, then checks preferred positions, ownership, pose and nets. Vias, segment payload, AP types and unselected catalog entries are NOT carried or qualified; DRT, non-core/all-access-point routing and already-routed selected nets are outside scope. Do not use the resulting DB for those workflows. The receipt declares full_AP_catalog_preserved=false and detailed_route_qualified=false.

All pin/PG/OBS rectangles, footprint, site, directions and signal types must match. Only explicitly reviewed nonrouting implant/mask layers may differ. Existing target AP catalogs are rejected. A single exclusive helper session reuses only its own exact selected-position clones. Use a private candidate database and discard it on any exception; this is not an in-place transaction on a shared design.

Native synthetic metadata-only coupon unit oth-ubuntu-2433315-1793378792 passes on the exact pinned image, reading real ASAP7 R/L LEFs. Two distinct source instances preserve index, all preferred positions, nets, pose and actual new-MPin ownership; the second reuses only the first session's clones. Wrong footprint, routing-layer exception, DRT scope and foreign pre-existing target catalog controls reject. Synthetic original APs also contain tech/block vias and segment flags deliberately not claimed by the GRT-only result. This validates the executable metadata path, not actual GRT reconstruction or a physical gate.

Usage after explicit scope approval:

    carry = GlobalRouteAccessPointCarry(db, variant_layers={"RVTN", "RVTP", "LVTN", "LVTP"},
                                       scope="core_preferred_global_routing_only")
    receipt = carry.swap(inst, exact_shape_replacement)

Create the session before any master swap, use only a reviewed explicit allowlist, preserve the complete original native route map, and let the physical owner separately qualify exact all-net/pin-grid reconstruction. No RC, SDC, thresholds, clock identity, topology or library-function authorization is supplied by this helper.
