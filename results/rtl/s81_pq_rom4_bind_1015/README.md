# PQ ROM4 die port-bind fix (S-ELEM-B, 2026-10-15)
S-BIND strict port-bind: die net ra2 was 12 bits (ot_rom_4096x72_m8) vs RTL 14 (16,384-row stream ROM).
`+define+DSFD_PQ_ROM4` on dsfd_sp_pq_n / dsfd_sp_pq_produced: ra2[11:0] shared address, rc2[3:0] per-macro enable,
rq2[191:0] = four macro rd_out[47:0] (bank b at [48b+:48]); the select is the benched ot_s81_pq_stream_rom4_sel
(ce decode before the macro pins, bank index registered on the macro sample edge, 0 added cycles).
- tools/s81/pq_canonical_pins_gate.py --produced --calcap --rom4: PASS (prod_rom4.txt); PHW mutant FAIL (prod_rom4_mut.txt); non-ROM4 unchanged PASS (prod_base.txt)
- tools/s81/pq_stream_rom4_gate.sh: PASS 19,999 checks / 16,384 rows (rom4.txt); select-alignment mutant FAIL (rom4m.txt)
Die (S-DIE): add +define+DSFD_PQ_ROM4 to physical/s81_die_rtl/layer1.f together with 4 stream macros pqrom2a..d.
