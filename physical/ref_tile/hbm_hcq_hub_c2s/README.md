# QHUB registered-decode successor

c1r/c1s native census failed before layout: max191, 71 fanout violations. Binary return selectors were folded into wide masks despite kept decode wires; npos-minus-one mask controls similarly folded. Two additional accept cones reached33/57. No previous failures were overwritten.

SAFE checklist before gate:
1 PASS: same pin/control stages and crossing rings as c1r; zero new schedule edges.
2 PASS: unchanged734.4um regional geometry with existing registered stages; all same-region paths judged by timing.
3 FIXED pending mapped census: gather selection is registered one-hot, each bit drives32 data loads; sector update control per24bits; launch/rq split; npos masks captured beside payload; scan load controls use distinct kept capture registers. Gate must refuse any residual >32.
4 PASS: capture-time decode removes binary-selector fanout from output cone, no new serial stage.
5 PASS: programme in SRAM, landing array unchanged, select state192bits.
6 PASS: inherited macro lattice, full connected cell channels and parent outline. PNG check owed after gate.
7 PASS pending CTS: inherited regional entries/child clock refs, within-region TT/FF <=80ps required, hold margin.03ns.
8 PASS: static schedule, port-identical, zero added latency.

Native census and PNG review remain mandatory before submit. Bounded MAIN c2r + FALLBACK c2s, same structures and c1r/s placement recipes.
