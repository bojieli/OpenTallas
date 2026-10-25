# TOK-DS: indexed13 (I13) + faultfeed reprice on adopt178 (2026-10-25)

Tool: tools/s81_dv/tokfunc/compose_tok_ds.py (unchanged), base = main 26028effc (adopt178 plan, digest cf2f96c02c280c82).
Runs (epyc1 ot-run unit oth-ubuntu-1389586-1792931845; run.sh): i13_main (main lat + I13), ff_only (faultfeed lat
claude/s81-faultfeed-1025@3a58b44a01, digest 260bb3ecd59638f1), i13_ff (both; files here are this run).

| case | AR DAG T | AR map tok/s | MTP T_step (pipeline) | MTP tok/s | stretch |
|---|---:|---:|---:|---:|---:|
| main adopt178 (of record) | 1,387,238.6 | 784.9 | 1,815,229.6 | 2,749.4 | 2,517.4 |
| faultfeed only | 1,387,238.6 | 784.9 | 1,815,229.6 | 2,749.4 | 2,517.4 |
| I13 only / I13 + faultfeed | 1,387,274.6 (+36) | 784.9 | 1,815,440.6 (+211) | 2,749.1 (-0.01 %) | 2,517.2 |

- I13 (comp/i13_gather.json): command->done 612 cyc/job (S81-PORTS r3 flops, native SRAM D=1024, two-job overlap on the
  other tag bank adds 0; miss/dup/wrongtag/same-bank mutants CAUGHT; RTL codex/s81-idxenc-1025@0221f2570, evidence
  claude/s81-i13-1025@2d87810da2). Slot = TOK-DS call: it replaces the logic of DAG op attn.gather (runtime-index
  selected-row read, K=512 rows/rank; old measured 607.5 cyc/instance), wire/edge terms kept. AR 8 instances +4.5 each.
  Grade of those nodes -> measured-current-RTL (AR 29.18 -> 29.53 %, MTP 25.66 -> 26.10 %).
  Bracket if S81 instead places it as a NEW serial node: +612 x 8 = +4,896 cyc AR (~-0.3 %).
- faultfeed: 58 lane entries differ (9 new flt__* status lanes, 18 changed lanes incl. ctrl seqhost 60->58, attn s_3S_C<->svc_5 -1,
  dn_s_0S/7S_L4 13->15, xtier 26->27); none is on a priced token-path lane class -> 0 cycles AR/MTP. Status-only fault lanes
  as S81-PORTS stated. (The run priced the faultfeed lane table against main plan digest; the table digest differs by design.)
- No change > 5 %; no ledger row needed (I13 within the existing attn.gather price).
- Open: I13 synth fit (yosys, C=1024 dup search) and P&R not run; quant release +118/norm and gather-duty pick B (0 cyc) not composed here.
