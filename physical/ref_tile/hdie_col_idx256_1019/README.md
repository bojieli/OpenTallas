IDX256 configuration collar successor

This separate master rejects programme row>=256, nonzero pages, and full32-bit need>256; an invalid update concurrent with launch cannot write or start. The canonical collar is unchanged. FAN32 defaults to0; the physical candidate enables FAN32=1 and preserves every successful configuration/data edge while distributing the inherited wide controls.

The source458299321 proof compares actual default and FAN32 modes against the original collar:9cases,3356 identity edges,1026 writes,4 launches,32 real record events, two resets/reloads and count carries at255/256/511. Bounds mutants9/10/11, record-selection mutant12 and lost-carry mutant13 all fail. Actuallegacy row aliases remain witnessed.

The FAN32 mechanism has16 protected16-bit record/operand/programme banks, registered next-onehot copies, private counter/state controls and25 parallel copies of the existing reset second stage. Logical record and operand capacities remain2048/1536 bits. Estimated added distributed state958 bits; actual mapped total5420FF versus4460 on590 (+960), including retained implementation artifacts. Zero successful install/launch/record/data edges are added.

Pre-CTS checklist:
1. Boundary PASS: no combinational in-to-out path, input-to-register and register-to-output depth0; raw rst_n reaches one stage1 FF. Reset assertion/release remain the existing2clk edges, with same-stage kept local copies.
2. Reach placed outline bound:129.6square gives259.2um opposite-corner Manhattan span, below405; placed density centroid47.94/49.88um; actual source/reset/native reach remains to measure.
3. Fanout PASS actualASAP7map:16834 nonclock roots, zero above32, including FF/comb/reset with BUF/INVcollapsed. Previous807/261/165/87/69load failures are preserved separately.
4. Depth PASS mapped model:376.7ps/10levels worst; no external combinational path. Actualpostplacement/TT timing remains required.
5. Storage PASS: heldrecord2048bits and sixoperand1536bits, each within2kb. No >=3deep delay chain. Added control copies are finite retained FFs, not another data queue.
6. Geometry ROOT-APPROVED component exception: no macros; one full-core standardcell region, square129.6. Exactactual2330pins (583/583/582/582) all trackaccessible and insideboundary. Maximumfullface4.50pins/um; nominalpitch0.216. Std3100.8um2/core15695 gives19.76% fill. ROOT personally reviewed placed floorplan/density and approved exact129.6sq pin-bound~20.4%fill component characterization. Placed mass SW-biased; no shrink, submit or die adoption.
7. Clock PENDING:5420actualFF sinks on clk, clk at west-centre. CTS/native characterization authorized; measured spread pending. Use833.333ps, TTsetup/FFhold,60/25ps uncertainties, IOholdmargin0.03; native pin spread<=80 and parent boundary match required.
8. Schedule PASS component: fixed timing, no credits/backpressure,0 added successful edges; sourceguard depth/page/need behavior intentionally rejects invalid programming.

ROOT review packet: results/arch/hbm_idx_collar256_1019/fan32_458299321/{record.json,fanout_all.json,textbook_preflight.json,pin_geometry_preflight.json,png}. No REVIEW.json, submission, native view or die adoption is authorized. The old59.4estimate and NF4 hardview do not qualify this actual NF5 master; final homes/lanes/native source-bound die must regenerate.
