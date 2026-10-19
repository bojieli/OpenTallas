HWIN NEV16 true SRAM structural successor

Each event has independent1R1W registered SRAM reads for63bit{due,pos,user} and2bit attributes;4+1 tiny64x16banks per event. Gap24 and retire timestamp32 add4banks,84total. Due is computed once from original start timestamp+D at record. Registered compare uses due==tm+1 for the next edge. SRAM registered write ports and preceding-write forwarding preserve original read/freshness cycles; there is no serialized head prefetch and no changed minimumD or slot gap.

Binary address shadows advance with original one-hot pointers, driving5bank-read pins per event. Parallel RX identity table is1457bits; reset-distinct source payload copies feed <=16entries. Event pointer/freshness reset in independent regions. Offset configuration explicitly enables a row, so NEV16 die master supports programs with fewer active rows.

Full16event bench (every index0..15booted/checked):32starts,432/432 expected windows/replays,K2 unchanged, allfaults0. Bad RXtag raisesfault. MUT3 droppedab ->176mismatches; MUT4 ignored replayenable ->80mismatches. Verilator5.050. Integrationcalendar and synthgate pending.

Safe-design checklist before gate:
1 Source registeredpins/reset2 and registeredSRAMwriteports.
2 Outline475.2x432: macro/eventclusters local on43.2grid, highfanout global time/payload should be placed central; actual wire-reach pending gate.
3 Eventbinaryaddress only5banks; per-entryidentitycopies<=16loads; same-D copies have distinct regional reset nets. Check synthesized fanout/merge.
4 Registered SRAM replaces47:1mux; per-eventdue precompute separated from firecomparison, arithmetic/exact setup pending gate.
5 FIXED every dense runtime table intrueSRAM except1457bit parallel RX identities and752parallel firedflags. No runtime-indexed flop payload.
6 Macro18.36x20.79 +10.8halo fits43.2gridcell;84macros arranged10x9withfull-widthbottom32.4band. Area estimate8300 inherited from earlierflopimplementation untilsynth; raw20%fill reflects143kbank-accesskeepouts, fully stated in fill_reason. No fit claim untilmeasuredarea/PNG and wrapperallocation.
7 io_hold.03/reset2, per-eventregionalresets. CTS spread pending.
8 Static schedule; zeroaddedoutputedge, originalD>=nw+2 unchanged.

ROOT notice 10-19 08:20 accepted truthful lattice_channel_bound sizing/schema: measuredstd6535um2 / full32.4um band gives42.8%;84macro lattice/channels verifiedalgebraically. Finalvisual/reach/fanout/clockreview remainsrequired. Earlier pin_bound label was incorrect and removed. Diagnostic firstgate has oldpointer source and never qualifies finalRTL. Binaryshadows now use exactlyregisteredlm masks and NSLOT-1fallback, with simulationpointer-correspondence assertions; realcalendar validation pending.
