# QF fallback independent frozen critical-review packet — approval pending

This packet requests **independent ROOT review** of fallbackdsdv_idx_qf_f only. MAINapproval does not apply. No regate/newaudit/RTL/geometrychange was performed. ROOT must personallyview this fallback's own2PNGs/rawJSON before anyREVIEW/submit.

GeometrymanifestSHA`d1102458c638e0cb2c77682e785a13840faafdd5ca65e7af6594d856cfb09905`, canonicalsubmitgeometrySHA`3009b36b32939fff7cb9e57262d668cc08dd0821c7e85ee2186e2d3c5728fb89`. Exact2PNGs: physical/ref_tile/dsdv_idx_qf_f/gate_layout/{floorplan,density}.png. geometry_manifest.json binds those images, sourcekit outline/faces/clockfiles, actualfloorplan/placedJSON andgatepin dump. Actualpin dumpSHA`67671249133b97e42e32825367824f9453919822f9476171cfa427d6d9ca700e`; rawJSONs gzipretained with uncompressedSHAs. Counts2579signal+clock vs2675including supplies.

Exactrawgate: physical/ref_tile/dsdv_idx_qf_f/gate_result.json SHA`049c7539a4c6b68d2bbebf321af57503f826f1fbf3ab5eca1cf1413f4f1620ff`. gate_summary.json SHA`f7ccc723ac7197a587ea14c90d3b7cbedb6240be22300a90715f9e9e9a4369b6`; source_snapshot.json fileSHA`eeadefeb03d7de6406bf360aa9c9e5d3eb330d38a08840409a7140350fd784f8`; internalmanifestcontentSHA`34ab46d08e0818962bece79cbe450e63d3930a8322716124ea89e1b0350fe669`; archiveSHA`b0b91ac8d4c391cb61fb9fe51ce698409c6b2c3d356478cb09630fac6b9166c2`. Source startcommit`ed9c179a2fbee72e877ca8595f1eae9368a6de45`, logicf7412b6c2, RTL SHAfe754d62b5ef2030c3fac28f479792bc2a1287a60b00942fdedf06a90374b283. Exact-content binding includes named10daemon helper overlays at`85fcc1f96936d9da9298c648cc6a48c6deacf1a2`, fully listed in source_snapshot.json; no plain-commit-onlyrun claim.

## Eight points and measured cost

1. **Pins/profile:** actualpincheckPASS2579,0offtrack/outside/inaccessible/missing. AlternatefaceS isqc0+qc1=1026contacts/259.2=3.958/um; Wql+uid/st/ck/rst527/432=1.220; Nqs513/259.2=1.979; Eqr513/432=1.188, all<=4. This differsfromMAINfaces; parent pin/landing placement must use actualfallbackfaceprofile.
2. **Hops:** original3edge registeredpin-to-pin behavior,0newsourceedges. Textbookreach0 is not a proof of actual405um route/parentlanding; that sourcebinding remainsowed.
3. **Fanout:** independentfallbackactualnative8007roots/max30/0violations/roles. Native netlistSHA61f30610f1bc5d4344b5ab4a5fbdd3fac8199360a02554447e0dcbc3f6cfa707; sameRTLmath asMAIN, independentphysicalview. Alloriginalnativefailures retained.
4. **Depth/timing:** textbookdepth280.1ps; TTplacementdiagnostic setup+25.139ps/hold+34.4999ps. TrialGRT0overflow, peakM3usage12.41%. Gate evidence, no SS/FFdetailedrouteCLOSEDclaim.
5. **Storage:**0macros/no runtimepersistentarrays;107bitspec+boundedscalar/datapathFF/control, no ECCchange.
6. **Fit:** exact259.2x432/core109007um2,std1713um2(~1706stage-specifictextbook),1.57%logicfill. Viewedactual2PNGs: mostlybluerowfield,mildgreencentralverticalclockspine/perimeter, no macrochannels/hotstripe. Thelowfillwarning is explicit, not a waiveduniversalutiltarget. See pin-boundarithmetic below.
7. **Clock:** one root3618sinks; TT/FFpinspread37.1/34.9ps, insertion465/388ps. Differentactualclock tree fromMAIN66.1/62.6; parentboundarymatching/STA remainsowed.
8. **Reset/protocol:** control-only8keptleaves original2edge release, allactualnativecontacts<=30. Sourcef741 existingbasePASS/MUT1+2caught andindependent6seedG8referenceall0mismatch;0addedprotocolcycles, no newarrivalrestriction.

Measuredsourcecost vs original1d: sequentialoutputroots3323->3618(+295),comb/macro2589->3353(+764),inputroots1035unchanged. These are mappedrootcounts, not physicalarea. Currentstd1713um2/macros0 measured; no newwhole-tokenrate/powerclaim.

## Alternateface pin-bound footprint justification

This candidate retains exactexisting259.2x432 release-slot outline, but itsown alternatefaces require independentreview. South1026contacts alone needs>=256.5um at4/um, so259.2width is within2.7um of that barefacebound. West527 requiresheight>=131.75um; idealizedface-onlyrectanglearea>=33793.875um2 permits<=5.07%fill even beforeclock/routingaccess. A52%logic-area target3294um2 cannot accommodate thisfacecontract. Thefull432height is retainedexistingdie-slot/profile, not claimedminimumheight or proofthatnocompactionispossible. Changingdieprofile/faceplacement would be separatework, not anunchangedsourcephysicalapproval. No inheritedMAINreview or selfapproval. ROOT may approve only this exactfrozenhash/alternateprofile; normalqualifiedsubmission followsapproval andnever touchesrunningMAIN.
