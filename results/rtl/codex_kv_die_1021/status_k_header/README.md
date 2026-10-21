# Actual K STATUS header and RX integration

New explicit qkd_d2d_static_ovl_sfm3_obs1 source derives the actual slot ctl/link/end/Kcore/top chain. The actual rf-to-hk header predicate calls the v1 validator plus strict reserved148-bit gap; all24 header/event/slot/epoch capture groups are real, and the RX records the full208-bit extension. Output observation225-bit pin bundle has the same PR edge as originalsvc. Originalsource/top/defaultunchanged; no oldclosedview alias.

Full new Ktop elaboration with actual dependency manifest passes (diagnostic parametersNTX3/TXDP22/SRAMV2). Oldkit contains one missing generated legacy ot_qwen_d2d_dies_sfo.sv reference; the manifest records it explicitly, newtop has no unresolvedcells without it. No physical binding/coverage claimed.

Admitted ep5unit851709-1792606570 minimum actual slot_ctl_obs1+RX_obs1 causal bench passes extension208, true native operation epoch66/owner2 within receipt64, unknownversion rejection and reservedgap rejection. Reinstating old356-zero header mask fails first valid extension with K_STATUS_EXTENSION_REJECTED. This is actual header/RX integration, not complete PHYR/calendar/fullMU or HOSTreader coverage. HOST225bus/atomicCSR reader, exactphysicalview/nativecensus and finalGEN remain pending.
