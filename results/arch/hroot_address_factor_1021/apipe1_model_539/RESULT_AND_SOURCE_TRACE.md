# APIPE1 model complete; no production/native/cold/physical admission

Pinned source539e8df61/b491, actualparameterAPIPE1 as PARAMETERS.json. ActualmappedSHA4b9b216227a513ad9b5c8159e1a0e0207dd56054e977acc740861f9d14ef2405. One canonical unpinned map/model admittedoth-ubuntu-4113434-1792625100 onagidock,8GB4CPUdisk20, no wallcap; RANexit0. Map208.46s peak3221.02MB. Full source/libs/tool/mapwarnings/logs/netlist retained;14-file portable prebuild manifestb0523d63 pinned. Existing-map/source traversal separately approved and admittedoth-ubuntu-4121889-1792625546,4GB1CPUdisk20, no wallcap, RANexit0; no EDA/map/proof in that trace. Full source_trace.json and admission log retained. Parent/ROOT immediately notified of results before further work.

| actual graph model | APIPE0 qualifiedprefix | APIPE1 |
|---|---:|---:|
| worst all-output/address |1238.6ps/37levels|1051.9ps/32levels|
| worst internal FF/macro-input stage |1148.6ps|1183.6ps|
| physical mapped FF count (before nativecopy) |16330|16427|
| raw SRAM macros |32|32|

Output improves15.1%, internal worsens3.0%. These are unchanged textbook scalar cellweights with sourceFFQ=0 and macrooutputsopaque, not STA, actual cell/slew/load/wire/clock or timing qualification. Logical98 sourcebits become live; actual97FF delta reflects mapping/sharing/removal, not an assumed native load census.

## Exact output source: RAW bypass, not registered streamaddress

Worst output _169625_ DFFHQN -> w_addr[30], 1051.9ps/32logic levels. FF capture ancestry includes descriptorpayload d_data16 only (plus shared command bits0..3). The exact carry path successively adds paired base17..46 and row144..167 through OR2/MAJ/MAJI/AOI/OAI gates; ring/stride/pitch do NOT enter before the final source-output mux. Detailed path_growth in source_trace.json pins each physical master/pin/net and FF-leaf field ancestry. This identifies M_RAW `st_wa=(AW==32)?af_add32(st_d[47:16],st_row):(st_d[47:16]+st_row)` and then unchanged qk_wv/outputmux. It is neither ap_raddr+sector nor ap_kcode+phase. This is static mapped source-family ancestry, not a transaction sensitization proof.

The source has `ap_go=(APIPE==0)||ap_ok||st_mode==M_RAW`, so APIPE1 intentionally bypasses this RAW path. APIPE>=2/3 also retain that RAW bypass; no unrequested parameter build is implied. The previous APIPE0 worst path was descriptor ring113 through IKEY arithmetic. Changing the worst branch means no same-path physical speedup is measured by comparing headline1238.6/1051.9.

## Internal source conditional and precise remaining identity limit

Worst internal _169695_ DFFHQN -> _166477_/D DFFHQN,1183.6ps. Both ordinary unreset data FFs, endpinD; this is NOT reset/control pin or SRAM-clock/address pin. Launch capture ancestry is ring descriptor113. EndD fanin contains base16..46,stride48..78,ring112..143,row144..167 anddie/namespace216/217/232/233, with feedback from its ownQ; no pitch80..84, no macrooutputs. The source conditional is the APIPE1 capture path `always @(posedge clk) if(!ap_ok) ... else begin ap_raddr<=s_raddr;ap_kcode<=k_code;ap_kscal<=k_scal;ap_mine<=s_mine;end`. Base/stride/ring and nopitch exclude ap_mine and genericROWS ap_raddr; this is the enabled IKEY ap_kcode/ap_kscal address-capture family, fed by ring-controlled s_rbase/k_blk andIKEY sums. ap_ok control itself imports rowlow4 through IKEY invalidation, so presenceofrowlow4 in the complete Dcone does not uniquely distinguish codefromscale. Public sourcealiases were stripped from the actualmap. Exact code-vs-scale bit identity remains OPEN; no guessedFF alias is asserted. Both candidateequations are exact sourcebranches in539: k_code=k_blk+qgroupoffset+qlowoffset+rowlowoffset; k_scal=k_blk+(q<<1), withk_blk=rbase+sb<<11+sb<<7 andrbase=base+(ring!=0?0:stack*stride). This limitation does not alter the direct fact that the output worst is the RAW bypass.

## Actual physicalbudget remains unqualified

Oldactual real1666.667ps TT placement diagnostic setup−810.5ps remains. Detailed tightened1540ps TT-overlay path is Q600.06 +cell1737.71+wire~227.66 =arrival2565.43 vsrequired1633.45. Holding that context fixed gives cell805.73 budget,~53.6%requiredcellreduction. Illustratively shifting only period to1666.667 gives cell932.397,~46.3%reduction, but actual realperiod report context differs; neither is reconstructed STA. APIPE1 graph1051.9 is a DIFFERENT RAW path and cannot be plugged into the old IKEY physical path or treated as a measured15.1%cell/wire improvement. The new internal1183.6 data stage needs its own setup/skew/wire budget. This model establishes no recovery of−810.5 and no physicaladmission.

Source dispatch/ROWS/IKEY/RAW/QKV/reset/state/retirement/calendar price remains MODEL_BEFORE_MAP.md. Temporalarchitecture changes explicitly; no old-frame equivalence/adoption. No nativecopy/selectedwrapper/cold proof/gate hasrunforAPIPE1. Native wrapper35 and539 coldcertificates remain oldAPIPE0 source-bound artifacts, not reusableadoption receipts. No new zeroedge or parameter variant was launched.
