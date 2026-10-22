# SPIPE6 source qualification during the 20:00 takeover

The coordinator reviewed PREBUILD_PACKET.md at d106596d6 and selected its existing bounded source qualification work. The architecture remains opt-in. The old mapped native32 image, reset-copy certificate, physical views and programme ages do not apply to SPIPE6.

The inherited engine source is unchanged (engine SHA starts999bf9c2); the shell has the explicit IKEY guard from d106596d6. Qualification fixtures are committed in tools/qwen_kv_die/hroot_registered_stream_1021, with exact SHA256 inputs in qualification_inputs.json.

- The engine job independently feeds the same legal RAW, ROWS and IKEY descriptors/payload to SPIPE6=0 and1, with different randomized stalls. It compares ordered accepted writes/completion tags, accounting, stable stalled outputs, and an independent Python sector image. It covers two ROWS ring/stack cases and a cross-superblock IKEY case. It does not establish universal arithmetic equivalence, four-state knownness, mapped native equivalence, full reset convergence, or QKV interlock coverage.
- The shell guard job uses the actual unchanged descriptor path, asynchronous FIFOs, SRAM behavioural model and reset bank. It exercises malformed first/count/beat fields, sticky fault8, no engine acceptance, drain, and a legal descriptor. The engine-face inputs are a bench environment, not replacement product logic. This does not qualify engine writes or full boot.
- Both jobs are queued through unpinned ot-run, stream24GB/8threads (client1344948/session63351), guard8GB/4threads (session6372), under /srv/opentallas-scratch2/claude/codex-qk-hroot-spipe6-2000. No build or simulation result exists yet at this checkpoint.
- Existing P1/P2/P7/P8 and the remaining P3-P6 interlock/reset obligations stay open. After functional source results, run one canonical map, regenerate native32/copy contracts and measure exact stage depths. Physical MAIN plus alternate floorplans follow only actual source/native admission.

D+3 issue / D+9 first write, six inflight slots and the held-word invalid ABI remain explicit unadopted programme costs. No old calendar or source/view alias is permitted. The owner-approved quiescent-reset ASR architecture and raw6/die boot debt remain separate.
