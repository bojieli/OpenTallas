# Native source qualification HOLD

Exact pre-layout mapped netlists from the six preserved gate runs all violate the binding <=32-load driver rule. pc/host maxima2187 (read-pointer/control decode), peer2113, prompt1519 (1515flop loads), order1184. The old gate checker reported PASS/WARN with hf_max=3000. Current qualification remains FAIL independently of the eventual clock/timing/GRT verdict.

PG pc/host source auto-submitted as pg1-506d8829a and pg1-12d9ecc9e before this pickup; preserve evidence but do not bind. Prompt/peer submit wrappers4067087/4109221 are SIGSTOPped under explicit coordinator authorization; gate descendants4072747/4118185 continue. Resume semantics: resolve source qualification/submit intent before SIGCONT; do not blindly restart them.

CDC also has zero macros with 21644/13163flops; its runtime-indexed 4x546 receive queues and 8x546 crossing queues exceed2kb and must become real SRAM. The dedicated successor preserves effective capacities and transfer/credit timing while padding addresses into existing32x546 macros.
