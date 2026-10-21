# QHUB registered-decode successor

c1r/c1s native census failed before layout: max191, 71 fanout violations. Binary return selectors were folded into wide masks despite kept decode wires; npos-minus-one mask controls similarly folded. Two additional accept cones reached33/57. No previous failures were overwritten.

SAFE checklist before gate:
1 PASS: same pin/control stages and crossing rings as c1r; zero new schedule edges.
2 PASS: unchanged734.4um regional geometry with existing registered stages; all same-region paths judged by timing.
3 FIXED pending mapped census: gather selection is registered one-hot, two copies per chunk, each bit drives16 data loads plus one feedback; sector update control per16bits; launch/rq split; npos masks captured beside payload; scan load controls use distinct kept capture registers. Gate must refuse any residual >32.
4 PASS: capture-time decode removes binary-selector fanout from output cone, no new serial stage.
5 PASS: programme in SRAM, landing array unchanged, select state456bits.
6 PASS: inherited macro lattice, full connected cell channels and parent outline. PNG check owed after gate.
7 PASS pending CTS: inherited regional entries/child clock refs, within-region TT/FF <=80ps required, hold margin.03ns.
8 PASS: static schedule, port-identical, zero added latency.

Native census and PNG review remain mandatory before submit. Bounded MAIN c2r + FALLBACK c2s, same structures and c1r/s placement recipes.

C2 mapped census refused at max33 (192 one-hot selectors at32 data loads+feedback); no floorplan ran. C3 keeps two selector registers per32-bit chunk, sixteen data loads plus one feedback each, and independent load copies for sixteen state flops. No RTL edge or port changes. All other C2 census drivers met32.

C3 mapped census refused six combinational nets, max48: common base/next-sector decode drove the D inputs of48 kept selector registers. C4 restores72 kept binary sector flops and makes the384 one-hot select flops unconditional decode rungs from their local binary copies. The internal decode updates one edge after sector state and is ready before the fixed response phase23; the next response is24 edges away. No output/interface edge is added. A kept loop-limit copy also splits the pc-wrap compare fanout33. Exact lockstep must pass before submit; mapped census must pass before layout.

C4 native census fixed all selectors/decoder-D/loop-compare violations; one launch accept g_la[14] remained33 (is_c1 sixteen-bit priority mux). C5 uses two independent kept launch copies, one per eight-bit half; same arithmetic next state and all interface edges unchanged.
