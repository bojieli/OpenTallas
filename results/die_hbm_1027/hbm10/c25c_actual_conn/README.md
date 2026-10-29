SELECTED RTL CONNECTIVITY IS THE PHYSICAL SOURCE

C25b core_conns targets45 virtual legacybase instances while physicalservicecores are __q0/__q1 at different centres. Actualhubgraph frombindlane f50be423... supplies3267 intra-hub directpin groups; replacing3852unverifiedlinks yields184badportgroups/72723awaypins on aPARTIALsourcegraph, not the old134/31848. Missing77sourceproviders and4glue-onlyports remainOPEN, so no completeness claim. vmm_* are actualsoftwritequeue mergers, NOT mu1banks. VMSq0roleS connectsactualmu1banks; VMSq1roleN connectsprimarybanks.

The earlier86face-repair result876f36a2d is againstSTALEmetadata and is UNADOPTED. Regenerate the actual graph and run c25c_actual_conns.py then c25c_face_diagnose.py before choosing pins. An opt-in --calendar-only restricts c25c_shared_face_repair.py to11VMSclock-calendar controlfamilies with explicitq0/q1 targets; oldmetadata134->90(44portsfixed), but recheck currentplan/source before adopting. NoRTL/cycle changes.
