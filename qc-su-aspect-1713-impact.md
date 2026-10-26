## 7.11 impact request — QC SU core short-axis successor, 2026-10-25 17:23 PDT

Preferred change: genuine new R0 physical views for prog/btab,259.2x354.24 ->354.24x259.2 (91819.008um2 each unchanged), no R90/PG/orientation waiver. Existing SIGNED prog_s8b view remains immutable and valid for the old plan. No candidate outline/pin edits made before approval.

Affected parent types sle_su_c and slw_su_c,12 E/W slice instances;24 pg/bt replicas. Upperrow proposal in each type: pg(17.28,380.16)354.24x259.2; ch(388.8,380.16)259.2x276.48; bt(665.28,380.16)354.24x259.2; su8(1036.8,380.16)172.8x129.6. Same1226.88x1339.2 parent outline,17.28edge/gaps. Lowerrow unchanged. Geometry/pin track/clock keepout and native macro/PDN fit need actual render+review. Physical BTAB owner agrees this can be its fresh structural successor; PROGRAMME new physical variant requires root assignment.

Pins/neighbours: partition boundary names,widths,windows,faces and allneighbour contracts unchanged. Direct neighbours per slice: bn_00/bn_10, sc,stm,su_l0,su_l1. Internal prog/btab physical LEF pin positions and coreclock/reset placement necessarily regenerate from actual same RTL ports;ch andsu8 internal placement moves. Preserve physicalnames and allIDstraps. No oldSIGNEDabstract is rescaled/relabelled. Parent core-pin tables and core clock offsets require matching actual newviews; early insertion numbers must be measured fresh.

Latency table/compiler: preferredaspect adds0registers/0data or tokencycles; existing static lane stages and compilercalendar unchanged, exact source binding must remain equivalent. Alternative existing-view channel detour for cws1/cws2 requires estimated5->7stations (+2cycles each across SU row), to be recomputed against full per-bit path before adoption; no free detourclaim. Preferred retains same boundarybits/cycle andmacroarea. No throughputgain claimed before physicalclosure.

Re-sign list: NEWprog aspect andbtab aspect physical masters, then sle/slw_su_c parentkits andtheir dieSTA seam obligations. Oldprog_s8b staysSIGNED; existingbtab_s8 isUNSIGNED FF−0.18/1EP andpair77.1/73.4. Actualparentpartitions0SIGNED, so parentre-kit doesnotwithdrawaSIGNEDpartition. CoreLEC unchangedRTL plus newphysicalview binding/faceguard; freshG0/G0C, actualG2+independentGEOM beforeP&R, thenTTsetup/FFhold60/25/833 SIGNED gates. No rulechange.

Approval requested ROOT/coordinator for preferredgeometry and programme re-sign assignment. Meanwhile CBN/CBX channel diagnosis continues independently. OWNER? None beyond coordinator7.11 approval.
