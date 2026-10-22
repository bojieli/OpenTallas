# Selected one-beat pin-channel observer correction

Attempt2 reached actual prompt rawdone339/POST344 and second allocation776/rawdone860, then the prior generic checker failed OFFERED_AW_CHANGED at1286. Preserve that exact failed source/log as history. No pin-channel RTL changed.

Actual qkd_host_pin_channel captures one request, returns registered acknowledgement and enters WAIT_DROP until source VALID falls. VALID may remain high after its first actual ready acceptance. The observer now captures the first offered payload, requires VALID and payload stability only through the first independent ready acceptance, then waits for VALID drop before recognizing another request. AW, W and AR have separate state. Accepted requests remain counted even when VALID stays high through ACK.

To prevent the observer from hiding duplicated capture, independently compare first accepted AR/AW/W counts against actual bridge0x12/0x14 packet counts at the host environment. The exact healthy descriptor needs5 reads (4 descriptor+1 packed prompt) and6 writes (3 CQ entries, word1 thenword0), with no MSI. Real CSR reply transaction IDs must be consecutive and unique. Existing real CQ ordering and all rank credits/releases remain separately checked.

This is qualification of the selected one-beat pin-channel endpoint protocol only. It is not generic AXI compliance or a relaxation of payload stability before acceptance. No source timeout, readiness, binding or ownership predicate was changed.
