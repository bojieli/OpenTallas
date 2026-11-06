# Native physical peer qualification

The corrected generic external peer uses GFMT1,EPPIPE2,LCR0,CH_BOARD700,chb1 to match the production safe8 link. This smallest component includes four real PMAs, the safe8 pair, reset-origin5/3 landing, and the production-option S7N LEP. No DUT force is used. Twelve arbitrary514-bit HOST payloads and reconstructed valid are compared exactly, followed by an arbitrary53-bit KS command.

Positive PASS: actual returned HOST_ALIVE331, HOST words449..505, KS receipt625, faults0. A legal0→alive status transition after warmup is required; tying alive1 from reset consumed the initial status event and produced the preserved earlier TIMEOUT. The corrected run uses the real source behavior.

Vehicle: epyc6 `/srv/opentallas-scratch2/claude/codex-ds-pma-peer-1106`, unit13481-1793965130, run_a2.py. The old-profile control (GFMT0/historical pipeline/chb0) is still compiling; collect it before reporting the combined result. Source and positive log are retained here; source closure paths are in sources_a2.f.

The full HOST vehicle uses this exact helper and is separately bounded to first dispatch on the frozen11-01 source. These are test stimulus changes: zero DUT pin cycles added.
