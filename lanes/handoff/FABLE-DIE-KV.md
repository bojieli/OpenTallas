# FABLE-DIE-KV handoff (owner of whole-die PD quality for KV qwen_kvsys; started 2026-11-16 07:00 PST)

Report: lanes/FABLE-DIE-KV.md. Types stay with FABLE-FIX-KV-PVHUB / KV-PVHG-O. The die delta goes into KV-HG1 (one event).
Branch claude/fable-die-kv-1116 @272407d9f41 (READY posted, remote gate GREEN 1/1): tools/clk/configs/kv_7yhr.yaml,
stage registry entry inv_ndr_kv_7yhr_b7d, tools/die_plan/die_rows.py + test. Clone epyc7 fable-die-kv/repo.

## Where things are (work dir /srv/opentallas-scratch2/claude/fable-die-kv on each host; clocks: epyc7 / epyc9 print UTC)
- epyc9 runs/b7 (record form), b7h, b7d; reach/ (reach_rules + die_hop_scan on 7yhr and 7uh). epyc9 scratch is full: no new runs there.
- epyc7 runs/b7e, b7f, b7g (chosen form); reach/plan_rr1.json; qk/ = 7yhr plan dir, qk1/ = event plan 5cfab111c977; event/ = row files.
- epyc2 runs/p1 = proof of 5cfab111c977 (die kit b7g form + GRT0 + STA + CA gate), gate/gate.out = G0 + reach + strict bind + LATCHECK.
  On epyc2 kw45 is a link to scratch3: kit_direct.sh there mounts scratch3 too. Die-priority ot-run is refused on epyc2 / epyc7
  for disk (60 GB reservation); the proof runs as a normal --crit job (script copy shared/p1run.sh).
- intel2 ~/tmp/fdkv: ot-run logs, event/ row files, die_b7.png (whole-die render).

## Chain
shared/chain_direct.sh ENV TAG = kit_direct.sh (ot_clk argv of the yaml, stage cal = cal_b7d.json) -> proto_grt_sta.sh
(GRT0 TT + FF, tap arrivals, die_sta_related) -> ca_gate.sh (count-aligned gate). About 25 min, 8 GB.

## Next
1. Read runs/p1 and gate/gate.out; fill section 6 of the report; post RESULT.
2. Die hold on real views: kit with --views of the signed records (rtx-pro signed-export-1114/qwen_kvsys), first measured hold.
3. After the KV-HG1 type compose: row A, die clock kit with kv_7yhr.yaml, regenerate rows B / C from that tree, die proof.
4. Signed PHY under the clock (2,024 cells): row B2 + PHY rebuild, with FABLE-FIX-KV-PVHUB.
5. QC-KV d2d +3 stations: take the KV row file from FABLE-FIX-QC-CBGLUE when it exists (requested 09:3x); 15 lanes L341..L355.

## UPDATE 13:40 PST
- 7yhr adopted. HG1A (plan 08d352df7ef0) and HG1B (b78d8aa38797 = A + fresh site rows + per-port windows) both pass pre / G0 / bind / LATCHECK
  on epyc10 fable-fix-kv-pvhub/hg1 (composed by FABLE-FIX-KV-PVHUB / Codex with my rows + die_rows.py + kv_7yhr.yaml). Die run on HG1A: hg1/runs/c1.
- Delta rows file: lanes/handoff/KV-102-delta-die1.tsv. Row F (QC d2d) withdrawn: no KV plan row.
- Still open, mine: (1) die run on HG1B itself (chain_direct on treeB plan, 25 min) to show contract 0 / 0 on the adopted plan;
  (2) die hold on real views (PVHUB C1 attempt: 20-view pack refused for missing sidecars, 18-view derived timing running: read it, do not duplicate);
  (3) row B2 / PHY rebuild; (4) rect count per type (max 366, target 100).
- epyc2 gate2 (bind of 5cfab111c977) is redundant; let it end, do not relaunch.
