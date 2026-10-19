# Named observations, thermal and telemetry inventory

The selected canonical interfaces of all 68 old219 direct die masters were parsed from the exact RTL files named by the strict receipt. Every selected interface resolved uniquely without port parse errors. No port name matches `therm|temp|telemetr|sensor`. This records the absence of separately named thermal/temperature/telemetry/sensor endpoints in this selected interface set; it makes no claim about fields encoded in opaque physical bundles and requests no invented feature.

All output observations remain functional or unresolved until their individual source roles and primary consumers are proven. Fault, abort, readiness, permission, authority, consensus, interrupt and acknowledgement outputs are explicitly marked functional safety/control and receive no unused declaration. Counters, status and other names receive no diagnostic waiver. The receipt counts 73 open output types; its per-master example lists are capped and show only 70, so this table is not a complete enumeration of all missing outputs.

`inventory.json` pins the receipt and every inspected source file by SHA256, records the interface count, unresolved list, named matches and open-output examples. `inventory_named_ports.py` reproduces this read-only inventory on the fleet. This artifact changes no design or pad contract.
