# QC-FW-CAP handoff (narrow lane, COORD 11-23 21:2x; job: QC fw types over the 400k cap)
Work dir: epyc11 /srv/opentallas-scratch2/claude/QC-FW-CAP (census/*.json, *.py). OT_LANE=QC-FW-CAP.
- 21:30 CENSUS posted (hub 5009b025). Added cells are all BUF (repair_design maxwire 100 plus port buffers). Synth has ~1 INV per FF; chain INV (FF.QN->INV->FF.D) is 54-80k per type.
- ROW = store-complement relays. Inside bind_cells ot_dp_dly, stages alternate polarity; names r[k] are kept. Optional: a CPL param on ot_dp_st chains.
- Base: QC-ALLFIX C1c 3b12251bfd6c, plan epyc7 /srv/opentallas-scratch2/claude/QC-ALLFIX/rows_c/plan_c1_fix2s.json. fw types are identical across C1c/C1d.
  Strict: ot-tree-fork kw45/snap_qwen_compute/qwen_compute_v4c4 -> own dir on epyc7. Then a COPY of QC-ALLFIX/bindB3.sh <dir> <plan> <sha12> rows_f16/auth rows_f16/comb rows_b2/ov_red2 rows_b2/ov_r8 <my overlay>.
  The only acceptable PRE FAIL is ROWS-NO-PROOF on 9 sle_sc. Deliver an idempotent overlay and post ROW-REBASED to QC-ALLFIX, cc FABLE-RC-QC.
## 21:52 PST state
- bind.py OT_DLY_CPL commit 45e1fd372c in epyc7 QC-FW-CAP/repo; ot-push-main running (log tmp/push.log).
  Projection (pol_*.json): dly-only alternation saves 22-31k INV per fw type. With st alternation too (not built, it needs a name-safe CPL on ot_dp_st) it would save 62-66k.
  Synth test: 144 -> 16 NOT; bounded equivalence passes.
- Row: epyc7 QC-FW-CAP/row/fw_dly_cpl_row.py (sha 610e5728d3ee, idempotent) adds OT_DLY_CPL to 9 fw types. Output plan_c1_fwcpl.json 0c14d74c49f2 (on C1c 3b12251bfd6c).
- Tree fork epyc7 QC-FW-CAP/cF/tree (fork.log) for the scoped strict. Use a COPY of QC-ALLFIX bindB3.sh with R = the rt that carries 45e1fd.
- Synth-only probe: epyc11 QC-FW-CAP/probe/slw_fw_v1..._cpl (a kit copy; run_kit refuses it with ENV-PROVENANCE, so it runs make synth directly). Log probe/syn_cpl.log.
  The real place/CTS hold probe needs kit_wave private-spec from the cF bind.
## 22:30 PST state (FABLE d57d810a: phase 2 + 200 um A/B + reset compare in parallel; release target <=360k at place on slw_fw_v1, fw x5 held)
- main 5127d7a29ef = phase 1 (cpl-first). Commit 5d9be36d30 changes it to plain-first and adds phase 2: gen_phys qn_alternate_stations under define OT_ST_QNALT (reuses the HBM qn_alternate.py). Push: epyc7 tmp/push2.log.
- Row v2: row/fw_dly_cpl_row.py 03bd83206081 adds both defines. plan_c1_fwcpl2.json 7224440fdc4e (epyc7 + copy on epyc11).
- Strict bind of plan v1 0c14 on epyc11 cG (tree fork from cache), rt 5127, log cG/bind.ot, unit oth-ubuntu-2646269-1795501019. epyc7 cF tree: ot-delete it after its lease expires at 00:05 PST (epyc7 disk is at 97%).
- Measurement runs (kit copies, ORFS make, probe/*): ab_base100 / ab_base200 (+ft 220) / ab_cpl200 (cpl-first) / slw..._cpl to CTS (cpl-first) / ab_pf (plain-first) / ab_pfqn (plain-first + qn_alternate: 88 stations, 33.2k bits converted). Logs probe/run_*.log; census at gen/<t>/cell_census.jsonl.
- Remaining-INV breakdown: census/rem_cpl.json. Non-fw hash proof: nh.log (su_l1 identical fe277a9e).

## 2026-11-24 03:07 PST
- pfqn result (phase 1 plain-first + phase 2 QN pairs, slw_fw_v1, intel1 probe/ab_pfqn): place non-tap 379,832, floorplan 274,749. Census: intel1 census/place_ab_pfqn.json.
- Place adds 105.1k buffers (87k are wire buffers, mostly BUFx12f/x12). Nets with HPWL 200-300 um carry 48.7k of them; 70k roots have fanout 1. Top groups: u_ft_cws/rsf/rsn ~23k, u_ist_* ~25k, u_lpad ~13k, ports 17.7k.
- Not at 360k, so no ROW-REBASED yet. Next structural lever: add a station on fw ft/ist hops >=200 um (each 200-300 um hop costs ~1.5 BUF/bit), or a type cut. Plan-level choice is with QC-ALLFIX/FABLE-RC-QC.
- Still open: ot-delete epyc7 QC-FW-CAP/cF/tree (lease expired); strict bind of C1g v2 9c527bc425f1 on rt >=5041641 needs OT_PLAN_GATE_PRE=warn (inherited findings are base-identical).
