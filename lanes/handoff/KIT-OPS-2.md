# KIT-OPS-2 handoff (kit-wave ops lane; COORD is the coordinator) -- 2026-11-12 23:52 PST. DONE, stopped.

## Result (RESULT posted to the queue; it holds the full detail)
- kit_wave.json 9e586a4304b (23:33), on origin. epyc4 is in hosts and first in place_prefer (top level + every die). It is first in gen_hosts for qwen_compute only. epyc7 is in s81 hosts/place_prefer. intel2 sits after the big epyc hosts and before epyc2/intel1, and has no gen.
  Revert: <key> <- <key>_prev_kitops2_e4. Backup: kit_wave.json.bak-kitops2-e4-1112. Script: intel2 /tmp/kitops2_e4_add.py (scratchpad kitops2/e4_add.py).
- intel2 ot-run cap: HOST_RESERVE localhost (16, 207) = 96 threads / about 800 GB, in 3 ot-run files under ~/.local/lib/fleet/{rehost1-kw38-spill-99d7dfcd, kw43-rootreal, isolate-1-kw46m-590d7d62e7}. Backups: .bak-kitops2-intel2cap-1112. Tick wall time did not grow (7.4-7.9 min); if it does, restore (48, 400).
- epyc4 staged on nvme scratch2 (about 9 GB): kit-ops-1/* inputs, hbm t39w/p37 sources, qc src_sw2, the 97 lfcs files. QC src s28 verified (FLEET-2 copy).
- The 4 big src trees (KV/S81/HEAD/HBM) were on the md0 ROOT disk (scratch3 = bind of /home/ubuntu/scratch-root). I removed them per COORD; root is at 513 GB free. They need about 200 GB of nvme (scratch2 has 238 GB at 94%, floor 150), so gen for those dies stays off epyc4 until COORD rules.
- Nothing in the configs lists epyc4 as retired. The ap-e5438a810146 "no host qualifies" happened because its kit dir is gone on every host.
## Open
- COORD: nvme room for 4 src trees on epyc4, or allow root.
- Not yet seen: a QC gen on epyc4 (no QC launch in the first tick).
- epyc8 tools/die_plan/gen_phys.py changed in the 4 kw45 trees during my copy (someone patched it there); this is not mine.
