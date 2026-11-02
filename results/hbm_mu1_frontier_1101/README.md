mu1 native producer frontier

All16 currentC4 mu1 callers are the SW/SE VMS banks in the NW/NE parent wrappers. Exact expressions for all80requestchannels and all write/DMA/collective/packet fields are preserved in current_calls16.json and frontier16.json. The selected originaltop hash is657a9fb5d7e99badd14354068ea3481e766444aa49a468d0e033a5445eaa62f8.

64rq0..3 channels stop at legacy17bit TOP INPUTS: SU lg_rq, hb_dbk rq, xl_ctl rq, hcollrs vm_rq. The remaining16rq4 channels are8×17bit outputs of currentSW rootctl and SE indexreader. None carries the new regular-row-high bit. The old mirror bit must not be relabelled as high-row. The existing legacy field adapter inserts a constant0 and therefore cannot qualify upper-half native storage; no adapter/tie/zero extension was adopted here.

The existing donor source hfd_vms_bank_native_q0_faces_r2048 (d587cc5af) has4realSRAM,2048regular+1024mirror rows, existing fullupper-half component test+mutants PASS, but not currentnative4-edge reset/parent qualification. All16parentbanks need12inputfieldbits+1egoutputbit+1macroclockbit=224newpins in total, with matching producer and receiver field repacking. Existing 3SRAM profiles cannot substitute.

Reset proposal: add a default0 DELIVERED_RESET mode through face/core/body preserving the original donor default; mode1 consumes a synchronous3stage delivered reset. This is a source-contract event, not an equivalence claim between unlike assertion semantics. Exact currentpreferred reset-body join, actual4edge cold/warm proof and parent boot-offset publication remain required before activation. Readable library paths alone do not prove current source selection because83/119 oldbind.f absolute paths are absent.

No RTL, plan, currentparent, sourcealias, PNR or clock contract changed. High-row producer is unavailable in the exact selected ABI; stop that adoption and continue other closure work.
