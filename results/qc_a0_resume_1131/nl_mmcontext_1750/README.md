NL combined-clock GRT diagnostic: preserved context failure and staged correction

The sole owned approved12GB2T run from actual retained post-MM finalGRT input failed before FF hold repair: OT_HOLD_STRUCTURAL synchronized FF scene BC unavailable. This is MM context failure, not DUT FF hold failure. Normal bootstrap had actual TT/FF Libs and TC/BC scenes, but orfs_hold_mm dispatch keys SDC basename: final_grt.sdc suppresses FF sync and adds FF hold false-path. Failed run also omitted original runner HOLD_SLACK_MARGIN=10 and inherited default15. Hold uncertainty remains25.

Preserved failed unit1924234-1793577088, intel2/epyc2 codex-qc-nl-clock50-1504/final50.log. Foreign inherited DRT untouched. No final50/census/outputDB claim.

Pure Tcl fixture reproduces exact filename dispatch with actual helper: final_grt fails sync; same-byte4_cts APIalias selects globalRC;3_place negativecontrol selects placementRC and is rejected. This is dispatch mechanism, not STA/corner timing credit. Source+alias hashes identical and3149 parsed commands/2105 timing directives unchanged.

Separate correction is STAGED ONLY under intel2:/srv/opentallas-scratch2/claude/codex-qc-nl-clock50-mmrole-1715, not launched. Changes only same-byte APIalias, configured margin10, and pre-GRT actual-mode guard. True input remains15:02post-MMGRT checkpoint; alias grants no CTS identity/proof/geometry credit. Original normalbootstrap/options/hooks/MM/PG retained, final full>=50capacity andnativeCLOCK+SIGNAL/PG/exportcensus unchanged. Root must review new diagnostic scope before launch; no extraSTA/DRT/foreign edits.
