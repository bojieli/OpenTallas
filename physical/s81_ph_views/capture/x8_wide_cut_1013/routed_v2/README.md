# Frozen wide v2 routed evidence

This source-scoped physical run is unqualified: detailed routing produced one M5 spacing violation between CK and f_w248. The actual final ODB/SPEF hashes, individual core/serial TT/FF/SS R, exact compensated path logs/scripts and actual PG rectangles are preserved here. Physical source is bc2c93f9283e5099cb77b06de663d27cfd5a3ff3.

Compensated nominal periods833.333/1111.110667 ps, unchanged setup/hold uncertainty60/25 ps, both directions and max/min paths: all eight TT/FF checks pass; minimum FF hold6.396352 ps. SS forward setup is -72.318459 ps sensitivity under the established TT-setup/FF-hold policy, not a TT/FF qualification waiver. Core boundary R is TT173.8/FF142.4/SS227.1; serial TT208.9/FF167.2/SS273.4 ps.

Actual44 M5 PG rectangles do not intersect either pin-face interval. Vacant scalar-control candidate centres114.012/114.204/114.396 lie between x110.4..110.712 and115.8..116.112 stripe bands. The nearest right edge114.408 has1.392 um clearance to VSS115.8. Die lead reviewed the actual data and made6e20fb09c authoritative (PG reviewda5faf138). That pin change requires a fresh gate and physical route; none of these old clock measurements qualify the successor.

After collecting the corrected supplemental exact+actual mutant verdict, the original frozen defective mutant sim was verified and terminated as superseded. Its process/source guard is retained. The termination is not a caught mutant and its wrapper-generated failure is invalid evidence. The fresh pin-repair successor carries the corrected testbench and normal exact/observed-mutant tracking.
