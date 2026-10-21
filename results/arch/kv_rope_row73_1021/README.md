# Actual RoPE HBM and73-record source packet

Base8ad0401af. Source implementation only; no new tests/audits launched under owner closure-first steering.

The accepted O61 owner supplies realposition13,embeddingtoken18,epoch16 (user retained inepoch). A second fixed HBM sweep starts1024edges after the first, with pseudoID151936+position//8. The existing128PC code sweep returns all64words; eight withword_index[5:3]==position[2:0] enter a separate real64x512 SRAM (only8rowsused). This deliberate fullrow overfetch reuses actual controller issue/return/train reservations; no reference values enter runtime RTL.

Existing code/scale logicalsectors and physical locations are preserved. Appended RoPE E19457304..19588375 maps rowoffset149,p=pseudoID-151936. This avoids both logicalscale and physicalrow148scale collision. tools/qwen_embedding_hbm/rope_image.py exports exact4MiB table using canonical dv_lower_vec.rope_words@6ff5be90f; emit_boot.py --rope DIR appends131072sectors before singlecombinedcount/checksum marker. Actual HOST boot dispatch/ingress plus package map are extended together.

New rowTX requires64code+scale+8RoPE resident atheader, verifies both trueepoch and expectedpseudoID, retainsactualembeddingtoken in all73payloads, sendsheader then64code then8flaggedRoPE. Bit512=1 onlyforRoPE,index529:524=0..7,reserved523:513zero. No wait/credit/admission workaround.

ONE generated pairimage: rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew1627_r16_rope.svh. Compile inputs MU1,EW1627,ROPE1,R16TX_SHIFT1,STATUS_DELAY213,KV_CODEC2,canonicalseam2,2,2,3,2,2/11,11,9,9,9,9,9. EW grows1032=1024actualtraversalreservation+8TX; rowheader/code shifts1024 andL0shifts1032. Programme rejects first actual traversal+PIPE_JOIN+8>=1024 or insufficient actualheaderdeadline. It must use actual O61context paths supplied by KVlead, not old RESULT baseline. Physicalviews/schedule/OVL-MU composition still require actualsuccessor; old595andoldviews do not qualifythissource.
