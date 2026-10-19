Fresh current-rule column-station component packet

Gate source cbb09ff421a1381fc8fa83e1ac07214f95aba842. Runtime refreshed to main874031d582698f79a854d91db3e0866f49e247c1 including ck_insertion76b086619 structural-clock-boundary-membership tightening. Both gate-consumed source/current gate overlays validate, with only unconsumed parent placement script change reported. current_bindings.json preserves exact archive/manifest and geometry hashes. RTL and geometry match ROOT-reviewed source2f1a966bb and packet9daac6a4b.

Both gates WARN, zero failures, two explicit low-utilization warnings; trial global routing overflow0. Native immutable5_1_grt.odb replay with unchanged signoff SDC/global-routing RC: E TTsetup305.345ps/FFhold29.832ps; W TTsetup327.616ps/FFhold28.298ps. This is GRT RC evidence, not detailed-route final signoff. TT-placement path_classes hold is diagnostic only. TT/FF spreads E34.4/34.6ps,W31.9/31.5ps.

Checklist, all four current PNGs personally viewed: (1)90.72x129.6 on required lattice, (2)continuous standard rows/no macros or channels consumed, (3)full-face signal spread<=5.94pins/um, (4)ck at planned S-edge landing with one699sink root, (5)aspect1.43 and explicit ROOT-scoped lowutil component geometry approval, (6)all mapped nonclock drivers<=32 and reset fanout verified below, (7)io_hold0.03ns and ordinary native timing retained, (8)complete source/state/calendar and two-stage reset cost explicit.

qfd_c_xstn_safe:699FF, maximumFFdriver5, ALL nonclockdriver23, rawresetloads{'0': 1}
qfd_c_xstnw_safe:699FF, maximumFFdriver5, ALL nonclockdriver23, rawresetloads{'0': 1}

Admission: committed bench_safe_xstn/mut0.log primary PASS and mut1.log mutant FAIL5994. Explicit standalone commands verified again in standalone_pass.log/standalone_mut.log at cbb09ff42. Job registers separate expect=pass and expect=fail cases with matching regex/witnesses.

Proposed exact components qfd_c_xstn_safe and qfd_c_xstnw_safe only. No coordinator REVIEW or submit has occurred. Parent will check final concrete specs/binding packet before delegating submission. Parent placement405reach/reset+2/compiler/clockrefs/absolute ages/windows remain open; detailed route/native final remain required for components.
