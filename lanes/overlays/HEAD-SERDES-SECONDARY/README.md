# HEAD-SERDES-SECONDARY overlay (TYPE-HDSERDES, 2026-11-14)
Problem: hd_serdes (HEAD, source pma_rck[0], 13524 sinks) needs the explicit secondary-clock density tree
(secondary_clock.install) and max sink radius 202.449 um; the wave src (src_head_rp21z_pgcap1d724b73) has no
secondary-clock code, so wave hd_serdes builds a plain CTS.
Overlay = (1) tools/die_plan/secondary_clock.py (radius cap 200 -> 250), secondary_clock_taps.tcl (BUFx24 density, driver print);
(2) gen_phys_secondary.patch: at the end of write_type_kit, if env OT_GEN_SECONDARY_CLOCK="<type>:<port>:<clock>:<target>:<dmax>:<radius>"
names this type, call secondary_clock.install(kit, spec). Unset = kits unchanged.
Wave setting (kit_wave.json dies.s81_head.item_env.hd_serdes):
  "OT_GEN_SECONDARY_CLOCK": "hd_serdes:pma_rck[0]:pma_rck:1000:80:210"   (radius 220 / target 950 is the fallback form)
Apply: bash apply.sh <src tree> on each gen host (epyc7, intel1, epyc10), then a changed-input relaunch of hd_serdes.
Tested: install() on a fake kit gives the same files as the pd3 kit; py_compile OK. Reference: epyc7 head-97/kitsserdespd3 (pd3).
