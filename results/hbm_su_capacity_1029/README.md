All 114 actual native two-quarter producer images census, 2026-10-29

94 matrix images (47 minimal4_4_0 +47 alternate5_4_1), plus20 finish images (BF16 projection and explicit softmax row phases). All114 lower_root5(parts2,line_bits4940,resident_edges7111) succeed. Max edges minimal1090 / alternate1091, below7111. The two profiles share aggregate per-column required dictionary capacities [5,9,5,3,3,1,1,1,1,1]. Generated candidate class profile is L,L,L,S,S,S,S,S,S,S.

Six images exceed the current default: qw_bf16_p needs column0=5 (both profiles); qw_softmax_max qpr1/qpr2 needs column0=4 (both profiles). Current column0 is S (3 dictionary SRAMs); it cannot hold these images. Column4 needs3 vs declared default2, but actual S hardware already has3, so column4 needs no hardware growth. Default physical installability is false for all6; each precise failure is recorded in capacity.json.

Current default caps [3,10,9,13,2,1,1,1,1,1] choose S,L,L,L,S,S,S,S,S,S. Candidate caps explicitly move the L class from column3 to column0; this preserves the count of three L leaves per part, not physical placement/timing qualification. Four resident index banks +S3/L13 dictionary banks give100SRAMs per part/200 for both, under both profiles. SB2470 outputs remain48bits/part wider than legacy2422.

Explicit optional candidate wrapper instantiates the unchanged generic c5 with SB2470,NC10 and the aggregate capacities. Its intended caller is pgp_NW/pgp_NE; it is not substituted into the production graph or signed inventory. The source must be requalified after the column class move. Existing source default is unchanged. No new simulation/P&R launched for this census.

Reproduce: python3 tools/hbm_static/su_programme_capacity.py INPUT_ROOT OUT_JSON --candidate-wrapper OWN_CANDIDATE.sv. INPUT_ROOT is a copy of intel1:/srv/opentallas-scratch2/claude/codex-hbm-token-0330/{su_matrix,su_finish}, native_prog.mem files only. The tool independently counts unique column words and compares them against actual lower_root5 output, checks each image against current physical classes and7111edges, and refuses candidate emission on S/L/resident capacity excess.
