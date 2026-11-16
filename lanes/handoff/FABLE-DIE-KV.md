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
