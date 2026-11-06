# Body control multiplier timing experiment

Current routed B failed TT -261.52ps /610 and FF -58.33ps /1286, DRC0. Critical issuer uop_d1[1360] feeds u_mul.pc[6][7], exactly iteration[23:16] times delivery-step[15:8]. The generated target next-state cone is one original8x8 multiplication, not a counter.

Rowwise CSA/prefix is rejected: full16 arrival437.27vs374.22ps; low8 arrival271.91vs237.29ps. Dadda/prefix is rejected: full16386.42ps; low8235.57ps saves only1.72ps. These failed candidates and mapping records remain here and have no production selection.

The optional OT_Q3CTL_MUL4_RT profile retimes ten low8-observed products: pa1/pa2,pv1/pv2,pb3/pc3/pd3,pb6/pc6/pd6. Four4x4 nibble products capture the exact D inputs of the original factor flops, and the original product-register edge combines them. Existing always blocks/reset/interfaces stay unchanged. Default-off token identity passes. Original full16 product bits remain bit-exact. Added protocol cycles0; no issuer delay or TOK latency change.

The two-edge vehicle covers all65536 pairs on consecutive edges, mismatch0; wrong-edge mutant65279 and droppedpartial mutant57599 are caught. Mapping uses the actual ORFS ASAP7 TT abc_speed script/dont_use rules. Retimed low8 downstream233.82→134.49ps; new upstream4x4 capture209.95ps. These figures exclude routed wires and sequential clock-to-Q/setup. Query of the actual routed baseline upstream capture is queued; no physical build authorized by this record. Full optional parser is pending. The new FFs need physical homes close to issuer SRAM/iteration sources before P&R. Preserve normal external face guard and parent signoff.

Retiming source reconstruction lives in retime/selected.json: both factor expressions, exact rewound original captureD expressions, selected register and semantic product name. Private branch codex/bodyctl-csa-1106; canonical recipe remains unchanged. Select dormant recipe ot_hfd_coll_q3_body_ctl__mul4rt only after source and upstream budget review.
