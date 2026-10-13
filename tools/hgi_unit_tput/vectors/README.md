# Committed bench vectors

`qdqvec/`: the eight DS-V4.1 per-die FUSED.QDQ records (3,328 output words, price 168 cycles) made by
`tools/hgi_unit_tput/qdq_vectors.py --vm-final ds_L0_vm_final.bin` (record 0 is the real L0 kv row of the exported
simulator run, so the generator needs that export). Copied byte-for-byte from the fleet set every quant_wide gate has
used since 10-10 (`ot-epyc1tb:/srv/opentallas-scratch/claude/hgi-tput-1010/vec/qdqvec`) so the composition gates
`quant_wide` / `quant_wide_ov` (tools/ref_tile/composition_gates.json) run in any job snapshot.
