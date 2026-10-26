# Current VS candidate status

Latest measured RTL source2f0cb6f94, default-off OT_S81SL_VS_SRAM. Still NOT ADMISSIBLE.
All run objects remain under ot-epyc5:/srv/opentallas-scratch/claude/codex-s81-vs-bankmux-1021.
No VS layout gate or route has been launched by this owner.

| Source | Structural step | Actual native maximum / violating drivers | Existing functional proof |
|---|---|---|---|
|474637070|8SRAM parity/copy banks, predicted read, write bypass|768 /297|ENG159/73 PASS; MUT7 catches16; VSallops PASS; MUT9 catches33|
|4dfd957fa|byte write-decode, flush and pending selectors|512 /305|same ENG/MUT7 and VS/MUT9 results|
|5de57c716|QR byte capture/phase, kept control identities|521 /306|VSallops PASS; MUT9 catches33|
|11ed229e0|32regional reset leaves; each FP pipeline owns reset; unused old stash counters removed|521 /305; raw reset input1, zero role errors|ENG159/73 PASS; MUT7 catches16; VSallops PASS|

No measured external latency changed. Native admission remains a real blocker.
The latest circuit still has broad command/counter/operand-select controls and
shared FP cut-bundle payload fanout. The original 431-load reset node was
removed; retained source mappings place other high drivers at ka, captured
command fields, input-valid and shared ot_hdc_f12_cut payload registers.
Native JSON, mapped Verilog and mapped_attr JSON are retained remotely. Each
committed summary contains its full violating-driver list and raw report hash.
No constraint waiver, false path, multicycle or native-check change was used.

Source2f0cb6f94 operand-nibble hierarchy: existing ENG159/73 PASS, VS allops PASS, MUT4 catches22MOE errors; native5 FAIL654/307 (231seq), rst1, roles0. All raw logs committed. Next candidate adds regional arrival counters for ENG halfword selects and byte captures for RA/K/W; no added edges and no layout gate.

Source91891ec62 native6 max433/320violations (246seq), rst1/roles0. ENG159/73 PASS/MUT8caught4, VSallopsPASS. Regional ENG arrival and RA/K/W capture removes prior654/512/451 controls; broad result mux is next repair, no layout.

Source58f946148 byte result mux native7 max257/338violations (276seq), rst1/roles0; existing VSallops and ENG159/73 PASS. Former433/364 resultmux controls removed. New257 root traces command wsel[0] into64bit eight-way weight mux, next201 RA result capture; next source byte-local weight selectors + predicted RA byte write enables. No layout.

Sourcee8072e473 weights/returnedRA native8 max257/345violations(289seq), rst1/roles0; VSallopsPASS/MUT9caught33. Highweightselector257 and RAreturnedcapture201 removed; remaining257 traces ENG gate128b capture, next181 arithmeticresultmux. Next localgatebytes/reduce-copy selectors/resultbytes source partition; still not admissible.

Sourceab0a9f5f1 native9 max172/350violations(300seq), rst1/roles0. Gatecapture257/resultmux181 removed. VSallopsPASS; ENG159/73PASS/MUT7caught16. Largest172 globalcommandaccept,133SWinputvalid; next source byte commandcapture + independent kept same-edge busy/valid regional state + SWpreviousbytecaptures. Shared ot_hdc_f12_cut FP payload136 remains scoped to existing peer after XG terminal collection. No new layout.

Sourcefbe323bfd native10 max170/361violations(305seq), rst1/roles0; VSallops/ENG159/73PASS. Broad commandaccept172 removed; current170 c_bad fans region decode/state cones. Next same-edge packet capture+command validation in8kept regions; sharedFP source scope assigned existingworker, no defaultFP change.

Sourceebe5885e3 native11 max136/357violations(305seq), rst1/roles0; VSallops/ENG159/73PASS. c_bad170 removed; 205 sequential violations trace sharedFPcut payload, 56 regionalop/ka state,16weightselector,13resetleaves,15other top controls. Next source real op/counter consumer copies with local capture/counter scopes, byte ENGreadmux and weightnibble selectors; FP hook defaultoff awaits peer module. No layout.

Sourcec99a344fc native12 max138/359violations(300seq), rst1/roles0; VSallops/ENG159/73PASS. FPtop138 remains, newlysplitstate op/ka consumers decreased but c_bad region now111. Next controls predict sameacceptanceat existinginputcapture edge (busy/gmask afteredge), real registered acceptcopies in4regions; runtime equivalence assertion against original acc_cmd. No addededge. FP128 independent resetleaf hook behindpaireddefine supplied for peer, FPfile notadopted yet.

Source3065e4018 predicted localaccept copies: legacyFP native13 max134/310(258seq), existingVSallops/ENG159/73PASS, runtime128-bit accept equivalenceclean. Sourcee7630911e integratesFP070 +128actualsame-depth resetleaves: fullnative14 max73/101violations(52seq), rst1/roles0; VSallops/ENG159/73PASS/MUT3caught64QR. ExactFP070 standalone2Madd/mul zero. PeerFP2a94f398f now bothleafnativePASS28/0/0+same2M proofzero; next exactintegration, no layout/adoption.

Sourcedbc5da527 exactFP2a fullnative15 max75/53violations(39seq), rst1/roles0; VSallops/ENG159/73PASS. FPleaf28/0/0+2M each zero. Remaining top control/input111? actualmax75 globalcmd; primaryopcode43/35, pending44, localreadselect38,weight33. Next sharedincomingopdecode, boundedreadstateacceptflags, localpendingpredicates, nibble/bit consumers; no layout.

Sourcec57368e62 fullnative16 only11violations, max128 (w_arr),84sharedQB,RA64/QR64,small37/35/33; only2seq33,rst1/roles0. ExistingVSallops/ENG159/73PASS/MUT9caught33. Next source localweightarrival/QBcountdecode/RAoutputbyte/QRholdbytes/SRAMbankdecoders/SWweightbytes, real consumers on existingedge. FPsource2a unchanged andqualified28/0/0 at leaf. LEPA r6v true routeFAIL identified separately, personalstructuralsource ownership aftercurrentVS; no helperdelegated.
