# Qwen stage37 open-items ledger (TOK-QW-3 / TOK-QW-4, 2026-11-02/03)

The OWNER adopted Codex's native stage37 design. It stays default-off until a composed token run matches the golden (`hdc_golden.py` / `qwen_tp8_token_oracle.py`) bit-exactly. This ledger lists each open item, the values already measured for it, and the values still missing. It adopts no dates; `ledger.json` gives the sources.

| Item | Measured so far | Still unmeasured | Smallest vehicle |
|---|---|---|---|
| a. gain/PROG lease | Gain CROM 1088.. (+2048 per user). pidx 16/144/272/400. No reuse of any live transformer row. 106 rows. Genuine rank0 payload exact through the main loader. **Install window (TOK-QW-4):** loader occupancy is 90 edges between range starts, and 89 faults all 12 slices. CTLM start to stage37 writes is E+15..E+94. The 148-range boot install at spacing 90 is clean. The native image has no TLOAD entries, so the stream window is vacuous. Ruling: install at BOOT after stage 36 and keep resident (`qwen_head37_install_window_1102`). | T_die in the bound front (a constant shift). The held production TREQ schedule must keep the 90-edge rule. | Whole-QC bound front. |
| b. ROOT PSUM lifetime | cfg-to-write 208 edges (external-PSUM fixture). Causal RES2→ROOT→H PASS. Selected ROOT cfg at edge 5057. | Arrival of the 32nd PSUM. RSTD publication up to the last apply-H read. No other writers to the PSUM slots. | Live-calendar native FDN/RP/CTL/SU vehicle (about 16 GB). |
| c. issue / H publication | SU command ages 49..120 (structural). H beats +70..+110 (component). STREAM 17/18 split. Tail result_age 106..113. | `HEAD_APPLY_S*_ISSUE`. Bound SU→STREAM path. headtap/Xfill. S8 per-chunk dates. | The same vehicle plus the bound HEAD producer cut. |
| d. calendar | nent1021 / HEAD326 / LOCAL4 1020 layout (relocatable). CTLM37 PASS at nent1013 and at nent1021. | The three remaining relocations (apply issue, RSTD publication through the last H read, headtap/Xfill). CTLM37 at nent1021 PASSED (`qwen_head_ctlm37_1021_1102`), but its 65-edge range spacing is not a valid load schedule (see a). | Link the relocations, then emit masks. |

Edges measured in a component are not global calendar dates.
