# TKM reset-form proof control

The native __ctlrst source at61589dc694 and the private tk mrst kit source have identical SHA2562214efc605dac6ac80efbb29fe03a38486a272fde801af7e27ad1f48d27c62ff. Existing smallest-vehicle benches are summarized in existing_positive_summaries.txt: control always, payload only under its valid; raw invalid payload differences are informational. All final v1 runs pass200kcycles with random starts and mid-run resets. The kit synth LEC proves14591points.

Missing negative control was added2026-11-06. An otherwise identical DUT gets its exported busy output inverted at the wrapper binding; original-source old root remains unmodified. Common synchronous1r1w SRAM model is sram.v. mutant2.log records199993 qualified mismatches/200000cycles,130resets,82done,350write cycles: mutant caught. The control tests observation sensitivity; it introduces no source or pin cycles.

Inputs were built from committed native old and __ctlrst source, with old module names prefixed OLD_. TB is tools/hbm_b2/tkm_l74/tb_tkm_root_ctlrst.sv. Wrapper mutation changes .\\u.busy(busy) to a private wire and assigns busy=~private_wire. First16GB build MEMCG-OOM is retained in intel2~/hbm-gaps-5/codex_tkm_mut.otrun.log. The retry used-O1/output-split20000 and48GB admission after the measured OOM; actualVerilator allocation17.99GB, build462sec, ot-run unit2029477 exit0. No wall-time limit was used.

Run data: epyc2:/srv/opentallas-scratch2/claude/codex-hbm-tkm-proof. Physical closure remains pending; prior kit stopped only at overlapping clock-pin access, fixed by p35.
