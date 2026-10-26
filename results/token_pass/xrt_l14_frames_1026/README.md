# Actual L14 frame images and split configuration-bank identities

Generated real checkpoint frame images using `tools/s81_dv/layer_prog/lower_xs.py gen` at 9d0d3e726, with its as-built manifest source selector and explicit hard-leaf child files. Source LP schedules are current; placement is the legacy tree_fc31 compiler vehicle, so whole-bound placement/calendar adoption remains held.

- u_f_6R01 / u_s_6S: slice index12, fixture output rows1296..1299; faults0, ret_words12, beats80, ot-run unit1943538 exit0.
- u_f_4R01 / u_s_4S: slice index8, fixture output rows224..227; faults0, ret_words12, beats80, ot-run unit1943540 exit0.

Each frame has 53 MB of actual element/config/XS maps, not blank payloads. Runtime images are on intel1 under /srv/opentallas-scratch2/claude/xrt-l14-1026/frames/<frame>.

The two JSON records map all84 bound r0 configuration macros to image keys. `frame_cfg_identity.py` proves each split macro's CE, clock, address and data pin expressions match the monolithic source macro exactly, then uses that source macro's explicit INSTANCE suffix. No pair/bank index is inferred or renumbered. All42 per frame pass; changed CE-pin mutant is caught. Image SHA256 and real512x576 packed via-map shape (the4096x72 physical macro) checked. The initial4096-text-line checker assumption failed and was corrected; no images changed.

No native bound simulation, whole token or physical sign-off claim. Remaining frame groups and full512-row production operations still need actual placement/calendars.
