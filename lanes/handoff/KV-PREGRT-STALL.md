# KV-PREGRT-STALL handoff (11-23 PST): STOOD DOWN, goal done
- Cause: pregrt_ff_hold rr pass (OT_PREGRT_HOLD_R2R_MARGIN=40) was one uncapped single-thread repair_timing run after the base pass closed hold. It covered 35k-88k endpoints at 500k-700k insts and ran 6-10 h with no output.
- Cancelled: oth-ubuntu-915540-1795434191 (kv3_pv_v3 E10), oth-ubuntu-2029835-1795446419 (kv3_hg_v3 E8), oth-ubuntu-2822186-1795440396 (kv3_pv_v6 E8). Pre-repair TT setup -738/-439/-548.
- Fix: main c40acd92e6 (pregrt_ff_hold.py: rr chunk default max(500, 0.5% insts), 3 chunks, setup guard). Accepted by COORD. FLOW-OPS rolls rt/current.
- HOLD: kv3_pv_v3 hold_items key (kit_wave eb9e50a) handed to KV-PV-CAP (af7c0e10d864ca1d2) per COORD. It is not lifted on the rt roll. KV-PV-CAP releases it after its structural row (703k > 400k cap, setup -738).
- Lane clones: epyc10 and epyc11 /srv/opentallas-scratch2/claude/kv-pregrt-stall/wt (idle, may be removed with ot-delete).
