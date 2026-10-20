# HBM-VMG7-5 10-20: mapped native32 census of the live VM-glue g7/g7d gates and of WBK hbm_wbk_ql_1019

Tool: tools/ref_tile/native_census.py + tools/textbook_lint.py from origin/main (tool.sha256), run by census.sh in
openroad/orfs:asap7lock on the data host (ot-run), on each gate's actual mapped 1_2_yosys.v with the Liberty files of
its own 1_1_yosys_canonicalize.log. Summaries keep everything except the per-root driver_counts table.

| netlist | status | roots | max dynamic loads | >32 |
|---|---|---|---|---|
| hfd_hgi_vms_glue_sw_g7 (ep9 ref_gate/..._sw_g7-20261019-223044) | PASS | 162,611 | 32 | 0 |
| hfd_hgi_vms_glue_e_g7 | PASS | 116,363 | 32 | 0 |
| hfd_hgi_vms_glue_nw_g7 (ep7) | PASS | 116,330 | 32 | 0 |
| hfd_hgi_vms_glue_sw_g7d | PASS | 162,611 | 32 | 0 |
| hfd_hgi_vms_glue_e_g7d | PASS | 116,363 | 32 | 0 |
| hfd_hgi_vms_glue_nw_g7d | PASS | 116,330 | 32 | 0 |
| ot_hbm_svc_wb_kport_q, job hbm_wbk_ql_1019-ql1-6c8ab57d1 | FAIL | 327,519 | 1,696 | 1,411 |

WBK violations by class: 1,319 combinational (K-side 32-way storage-dependent select / skid enables, 1,206-1,696),
64 FIFO rbin[] (1,156-1,160: 288-b x 4 read mux), reset_pipe of u_stream_reset/u_hbm_reset 667/630, root resets 129,
srst_l1 205, hrst_l1 112, copy_bank 191, fb_q 156, fill_bank 126, ordinal[] 60, meta/ack rbin ~120. The job was cancelled.
This is mapped fanout/role evidence only (no functional, pin-registration or storage claim).
