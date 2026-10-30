# Corrected collar native exactness

D34e2 current collar659f33ab1d51 (sole W c_done input) generates1559 pins, face/port guards PASS. Original LEC remains UNPROVEN9367/9380: thirteen low rec output bits depend on frontend spellings `u_payload.rec[3..15]` versus `u_payload.rec#t[3..15]` in bank2.

Thirteen untrusted equality hints are independently checked by native induction; no assumption/waiver is added. Fresh actual native LEC EQUIVALENT12058/12058,13hints applied,0skipped,0dropped. Wrong-bit control maps gate rec#t[3] to gold rec[4]: that hypothesis is dropped and final remains UNPROVEN1, so it cannot qualify the wrong mapping.

The recipe change adds only those hints to the existing FAN32=1 collar recipe. Source, parameters, pins and cycles are unchanged. Actual source/RTL identity and tools are in native lec.json; original failure preserved remotely. No placement/route or SIGNED claim. Parent event adoption still held.

Intel1 run root: `/srv/opentallas-scratch2/claude/codex-hbm-cores-1030/event34`; proofs `lec_hint13` / `lec_hint13_wrong`; original kit `kits/ot_hbm_static_cfg_collar_idx256r_659f33ab1d51-_codex1030e34`.
