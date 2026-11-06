New distinct masters only. OpsA0/1 add one complete stage-write input cohort per measured physical bank column before existing bank decode/BREG. PIN CYCLES: write visibility+1; reads/scalar latency unchanged. The exact reference is the captured primitive driven by stage-write inputs delayed one edge; read/write hazards and faults compare at the same physical edge. No-reset distribution keeps issued writes in flight across reset. Four columns each carry2240raw FFbits (8960total); three packed storage partitions remain one simultaneous cohort. Small disjoint guides fit existing interrow channels after4.32um macro halos (conservative FF+inverter density below45percent), rather than covering whole columns and starving ordinary placement.

OpsB registers each bank32bit read locally before the existing network; per-lane/sector bank select and sector-valid delayed together. PIN CYCLES: readresponse+1, write/fault unchanged. Added512data+104select/valid=616raw FFbits. Before:412ps SRAM clkQ plus760um network. After:local SRAM→capture within one833ps edge, then about60ps register clkQ→network; no arithmetic change.

Proof actual16banks/LWB15/AW24/NS8/BREG1/FREG1, behavioral bank with same read-first word semantics:1509continuous/reset checks,217296datawords,3018faultchecks, write-stage bypass46diffs/read-stage bypass1476diffs. Original source and proof baseline captured from E2 hbm-reform-b12/k27c immutable kits; native macro implementation remains the ordinary bank primitive. Full mapped survival and physical gate results pending; no recipe/profile/POR activation.

ConservativeB variants combine both local stages. OpsA B also delays scalar data and its selection tag together, so every read response gains exactly one edge. OpsB B keeps the same read+1 and also delays stage-write visibility+1. Full captured OpsA G0/G1 integration (including scalar selection)1144cycles/73216wordcompares PASS; wrong sampled-output edge877diff. Original programme/profile activation remains off.

The first component log reported217296 datawords conservatively; the literal two512+2048-bit comparisons contain24144032-bit word comparisons. The full-G0/G1 log73216 counts its four512-bit comparisons exactly. No result is inferred from an unexecuted physical variant.

ConservativeB also uses existing empty ADDER_MAP_FILE mapping, as in measured rb_vB/s3_q_vC: the original OPS setup paths include slow FA/HA carry cells. A keeps the original mapping. No arithmetic/clock/gate change or sweep.


Actual native maps: OPSB A54692std/6531.45um2, B99454std/12144.8um2; both16SRAM+512readFF, B8960writeFF. OPSA1 A109005std/13009um2, B103109std/12714.4um2; both8704dynamicwriteFF (exactly64constant-one maskbits/column removed), B512readFF.

The native233.28um floorplan has3520ROWsegments/23807.3904um2 legal post4.32um-halo site area. DREG variants require parent-reviewed250.56um height and actual new pin/clock-entry event before PLACE. Captured old slot is not qualified for these variants.

OPSB A first PLACE failed GPL0307 with331.2percent routability inflation and16 overflowing read-guide regions. Read guides now cover the actual full256-pin native M4 read field (localY1.728..26.232): guideY+.54..+27.54,27um tall, same west channel. Actual whole-site guide areas137..139um2 support the observed resized-region18.896um2 at~14percent; measured global4.4357x initialFF area is~30percent. Original failure retained. Same-outline A2 may PLACE after reviewed image/model; taller variants remain held for parent geometry. No GPL parameter change or density waiver.
