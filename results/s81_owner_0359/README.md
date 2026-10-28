# S81 owner — native M5 PG stub repair

Die-local PG geometry fix only; no RTL, cycles, signal pins, outlines or OBS change.
The service hcore and leaf re-pin generators now emit M5 VDD/VSS ports from the existing standard core PDN recipe. Eight existing plan-stub LEFs are updated: hcore, sx_hrow_c and six leaf templates. Signed/write_abstract geometry is never rewritten; existing PG rectangles cause refusal. BF column M7-only PG is retained and still needs its own physical re-signing work.

Native basis: CORE_AREA inset4.32um; M5 width0.12/spacing0.072/pitch4.32/offset2.064. Real ORFS PG is vertical with VSS centres6.384+n4.32 and VDD6.576+n4.32, not half-pitch alternating stripes. Conservative pin Yspan4.32..H-4.32 is contained in the real rail extent. All309 proposed rectangles match own-net native M5 shapes in completed ve_m/vn_a/ve_s CTS ODBs. Actual hcore config/pdn has the same recipe. This is plan-stub geometry, not a signed physical view or an IR result. Parent core_pg_connect adoption and actual parent connectivity remain required.

Four focused tests pass: native pair phase/extent, all signal geometry preserved, refusal of existing M5/M7 PG, undersized core refusal. Exact before/after comparison confirms all eight LEFs retain their signal pins/outline/OBS. Measured geometry/images and runtime are intel2 codex-s81-owner-0359/core_means; no new P&R for this fix.

Owner intake: complete105107-character S81 handoff extract read in bounded chunks. Locality is MAIN under METH12.13–15; regional150ps includes OCV/droop/SPICE, crossing CA>=100ps. No new gate added.
