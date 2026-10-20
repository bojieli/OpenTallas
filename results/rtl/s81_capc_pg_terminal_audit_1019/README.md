# CAPC final native PG terminal audit — PG_HOLD

Selected source `267b35821`, CLOSED timing record `dfcfb2a7b`, electrical artifact `598ecfcb2`. This additive audit preserves those historical results and finds missing power binding in their exact final ODB. Parent adoption must remain on hold.

Final ODB SHA256: `d0186f1e664156ea82197d65321763c7b3a38613ca6bb65fb86e24d5b03fa7d0`.

The native master-terminal universe contains **240,376 instances**, **29 masters**, and **480,752 POWER/GROUND terminals**. Every master declares its PG terminals. **477,020 terminals connect to the expected VDD/VSS net; 3,732 terminals on 1,866 instances are unbound.** There are no wrong-net bindings or missing ITerms. Every affected instance has both VDD and VSS unbound.

| Affected instance name prefix | Instances |
| --- | ---: |
| clkbuf_sp_L | 1,468 |
| clkbuf_sp_N | 165 |
| wire | 161 |
| place | 72 |

| Affected master | Instances |
| --- | ---: |
| HB4xp67_ASAP7_75t_R | 836 |
| BUFx2_ASAP7_75t_R | 467 |
| BUFx24_ASAP7_75t_R | 330 |
| BUFx16f_ASAP7_75t_R | 233 |

This explains how the earlier `check_power_grid -net VDD/VSS` could report all shapes connected: a net-centric query does not establish membership of every expected master PG terminal. Most affected instances have CTS names; wire/place buffers are affected as well. This audit does not assign the creation-stage cause solely from names.

`collect.py` loads the ODB read-only and enumerates every instance's master POWER/GROUND MTerms before asking for its corresponding ITerm and connected net. Expected VDD/VSS derives from the master signal type, independently of existing net membership. `terminals.tsv.gz` records every expected terminal, including unbound ones; `census.json` contains all failing rows and the complete master inventory. The final database was mounted read-only; no global_connect, repair, connect, reroute, design write or constraint change occurred.

Fleet run: unpinned `ot-run --mem 4 --threads 1`, data-local selection ot-epyc7, unit `oth-ubuntu-69274-1792442111`, OpenROAD `26Q3-1510-g6cb3f2b704`, exit 0. `run.log` records the actual native result. `setup_failure.log` preserves the initial missing executable PATH failure; it is not audit evidence. Source remote directory: `/srv/opentallas-scratch/claude/closure-loop/s81sl_capc_p1_die_slew-s81capc_die_slew-267b35821`; audit outputs are in `pg_terminal_audit_codex`.

Scope is terminal binding, not PG geometry contact, parent PG completeness, or renewed timing qualification. After a structural binding fix, an exact successor needs this same all-terminal audit plus physical power-grid checks. Existing CLOSED timing numbers remain history; the selected view has **PG_HOLD**, and the prior electrical packet's PG-complete interpretation is superseded.
