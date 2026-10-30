# HEAD exact HB4 input-ring pin fix proposal

Independent Codex GEOM2026-10-30: viewed pre_pinfix.png and original hb4_geom rules. **FAIL baseline**, not fill-only: pinmax337.98/clockrootreach625.2/channelH.811, r2r403.06. The36 k_lo ring-slot FF moving into existing bottom y10..25um capture strip is a sensible non-plan placement diagnostic, no source/pins/outline/cycles changed. Actual DPL must keep all36 distinct and ensure newly moved ring read/capture fanout stays within reach; bottom strip already dense.

Later actual4CTS reported by collector GRT50zero,1894clockcells,depth15spread1,ownleafreach99.41,clocknetHPWL160.87. Existing checker ignores PLACEDclockcells for fixed-island entryreach so rootdistance625 persists. This is a plan/measurement-scope issue, not authorization to fakeFIRM clockcells or waive clock gate. HEADowner notified. Actual pinfix reGPL underway; no CTS/route authorized before actual review.
