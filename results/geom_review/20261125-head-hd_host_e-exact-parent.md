# HEAD hd_host_e exact parent

- Exact signed parent render: epyc10:/srv/opentallas-scratch2/claude/abstract-exact/gdsdrc/reroute_he4_incremental_1125/review/review.png.
- The large eastern he_epc macro leaves a narrow southern path, with the hottest cells on the path and a dense strip along its west side. Eight smaller SRAMs face away from their logic. In the gb bank these are 0, 1, 2, 5 and 9. In the ski head bank these are 0, 1 and 2. Cell fill is 4.7% of free area and 82% of the block is empty. Pin-to-register median and p90 are 6.24 and 7.74 µm. The existing abstract-class route failure is at gb SRAM bank 0. The revised layout needs a southern bypass and the SRAM faces aligned with their logic.
- Verdict FIX-FIRST for a new physical dispatch. Incremental abstract impact covers 2,446 of 84,808 nets, including clk_c0. The failed whole-reroute SRAM net18876 falls outside it. PG continuity after the 914-via cut is a separate measured property.
