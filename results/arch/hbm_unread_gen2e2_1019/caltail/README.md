# Held class universal_calendar_capacity_tail_review (1,045 bits) -- LH-UNREAD fork F-C, 10-19

Instances epcal_{NE,NW,SE} (W19), epcal_SW (W38), vmfc_{NE,NW,SE,SW} (W89): universal hfd_hgi_vm_calendar_f20 (closed view
hv16_vm_cal_f20_ww) exports calendar[186:0]; die clients read only the dense prefix calendar[W-1:0]. Held bits = calendar[186:W].

## 1. Certificate (tools/hbm_die_v16/caltail_certificate_1019.py -> caltail_certificate.json, certificate.log)
- Structure PASS: all 90 held entries / 1,045 bits map exactly to calendar[186:W] (8 instances, 187-W each); no held bit has a consumer.
- Compiler tail-zero: the ONLY in-tree generators of these rows are the epcal RX calendars of xdie_hbm_step_compile.py
  (ag/rs, frames 1..64, guard/release/K sweeps) and xdie_hbm_coll_compile.py; 53,016 rows checked, all < 2^19 -> PASS.
  They are vehicle generators for epcal_NE (19-bit RX ABI shared by NE/NW/SE): compiler evidence covers 504 bits at most.
- NO generator exists for vmfc_<q> (targets 56-59) or the two-endpoint epcal_SW (W38): 541 bits can NOT get a compiler
  certificate. => a certificate alone cannot admit this class; the hardware fix below is the real fix.
- Negatives PASS: N1 a row with tail bit 19 set is DETECTED; N2 certifying consumed epcal_SW bank_client[4:0] REFUSED;
  N3 range widened into the payload (epcal_NE response_seq[3]) REFUSED.
- Hardware fact (bench phase B): the universal master ACCEPTS and EXPORTS a nonzero tail with no fault (word check is [223:187] only).

## 2. Hardware fix (implemented, source-only): hfd_hgi_vm_calendar_f20_role #(W)
- rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_f20_role.sv: same target fold / reset sync / SRAM / capture rung,
  core ot_vms_calendar_static_xcap #(.W(W)) -> existing word check rejects any nonzero calendar[223:W] with the EXISTING
  sticky fault and emits 0; payload[W-1:0] one packed port (= universal calendar[W-1:0], same edge). Tail ports/flops gone.
- Bench run_calendar_f20_role.sh (Icarus 12, fleet ot-epyc7, bench_role.log): W 19/38/89 x 2 seeds: phase A every edge equal to
  the universal master (payload/v/active/done/fault/ordinal/tgt_*; universal tail 0); phase B one random tail bit -> universal
  exports it without fault, role faults and zeroes the row. MUT1 (tail accepted = universal behaviour) FAIL 6/6, MUT2 (payload
  bit flip) FAIL 6/6; witnesses bench_witness/run_w*m{1,2}*.log. GATE PASS.
- Layer tools/hbm_die_v16/d4g_layers/l20_caltail_role.py (on GEN2e2 pre_relay fd7492f2): 8 instances re-mastered, 476 edges
  remapped bit-exactly to payload[off+lo,off+hi), 89 whole-tail open_outputs records dropped, straps master renamed.
  Strict bind (l20_strict_bind.log): all structural 0, unread 70,320 -> 69,275 (exactly the 1,045 held bits; every other
  unread net identical). Functional bind PASS 1284 paths / 289,940 bits (LAT warn as the chain), unchanged.
- Manifest note: the approved entries for these 8 instances (ordinal etc.) keep port/range but their master becomes
  hfd_hgi_vm_calendar_f20_role -> renewed review re-points master/source (as col_idx in the GEN2e2 candidate).

## 3. Closure cost (not gated here)
- New tile(s) for hfd_hgi_vm_calendar_f20_role: params W19, W38, W89 = 3 variants (or one kit per W). Kit = copy of
  hv16_vm_cal_f20_ww spec (same W face, same 1024x256 SRAM, clk/clk_cap/clk_mem/clk_tgt roots), E face shrinks 187 -> W
  payload pins (+ calendar_v/done/fault/ordinal/tgt_*), so pin density only improves. Body flops drop 187-W output regs.
- SAFE checklist must be written into the kit README before the gate (pins registered as universal; reach unchanged;
  fanout/depth unchanged; storage SRAM; floorplan from the universal kit; clock as universal; schedule +0 edges).
- Until closed, GEN uses the role master as SYNTH soft cells (no hard view admitted). Universal view stays for calendar_<q>.
