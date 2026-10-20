# PVM distributed source -- edge and cost model (PVMD 2026-10-19; supersedes the fae1ece6e pre-build sizing)
Edges: inputs 2 (first capture at the pin, kept second copies), outputs 1 (unchanged): +1 steady input/result edge vs the
SAFE2 kit (flow pin reg 1 + 1). Reset: rst_n -> 2 first (D=1) -> 8 second -> 54 third flops, async assert / sync release;
input captures release 2 edges after rst_n (as the reference landing), the core 3 (+1 cold edge, aligns the +1 input edge
with the original barrel entry; bp start value is not observable). Semantics unchanged: 8-edge barrel, LAT7 adders, stack,
fold/publication calendars (bench equality every edge). Census flops 15,381 (SAFE2 reference + flow landing ~14.2k).
