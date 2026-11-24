# KV-HUB-EPZO handoff (Opus 5.5, split from FAM-KV-HUBWO-S1, 11-23 21:2x PST)
Job: hub landing-ring ep_zo "setup" class (-323 cland_i_astk_ES ep_zo -> bin, -182 ft16_i dch) on sealed hub_Eo 1122231141 / hub_Wo 1122231157.
- Census posted 21:2x (lanes/posts/KV-HUB-EPZO.md). Both paths are HOLD (Path Type min), not setup.
  - -323 is an internal cland->bin seam with 357 ps insertion skew. GRT hold repair already removed it.
  - -182 is port->FF landing hold on the deep dch fclk tree (266 ps). It is a die-seam item, not a kit sign-off gate.
- ep_zo/ring setup is at most -35. The SETUP_TRIAGE stop is entirely the astk station chains (FAM-KV-HUBWO-S1).
- Result: ROW-REBASED NONE on A3g b258e3e34f22, since no setup row is needed. No jobs launched, no units.
- Open, unowned follow-up for FABLE-RC-KV / COORD: an optional structural hold row (cap the dch landing-ring fclk insertion below about 80 ps, and put bin_i_astk_* on the cland ring tap).
- Scripts: localhost scratchpad epzo/{paths.py,hold.py} parse post-hook CTS reports.
