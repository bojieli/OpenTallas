WIP — NOT READY; actual kit equivalence pending.

CAP_RT keeps existing functionality and fault visibility edge. Default-off OT_S81_CAP_RT_FACE_REGS keeps all86 reserved cfg_d[159:74] bits as real raw pin-capture FFs and isolates the existing fault copy in a kept leaf. Zero data/fault cycles added;86additional capture FFs. No arithmetic/state-machine logic changed.

Actual complete RT+native behavioral SRAM lockstep12000cycles at833ps,517resetedges,632configwrites,8984wordedges,10616faultedges: zero mismatches on every451outputbits; reserved-bit fault poison mutant caught5937mismatches. Native candidate synthesis+raw/post FACE_GUARD746/746PASS. NativeLEC stillLIVE intel1 unit3164892-1793340977/session25360, /srv/opentallas-scratch2/claude/codex-s81-capchildren-2300/kits/ot_s81sl_cap_rt_face1/lec/lec.json. Do NOT adopt until its own real equivalence qualifies.

This WIP also saves the genuinely missing ED/RT child recipes. ED native generation PASS but actual FACE fails i_f pre-OR, sticky o_f self-feedback, and o_v post-mask. Owner question on one extra fault-visibility edge versus measured physical pin contract is plain text in CODEX-LOG23:10; no ED RTL change adopted. All ED/LD/RT native clock pins currentlyM3, so no parent P&R before die-owner contract. Signed-child parent hosting remains separate and is being implemented by the hard-core helper; no parent closure claim. Originalfailed runs retained.

Qualified LD commit017829a6426 is the previous independent commit; only it was submitted READY. This WIP is a distinct branch so root merge cannot accidentally intake pending RT.
