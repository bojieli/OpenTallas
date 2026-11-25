# QC-SUL1-BAND handoff (lane memory; one job: SUL1-FACE-BAND row for C1o, cut 03:00 PST, ROW-READY due 02:45)
Parent QC-ALLFIX; ruling FABLE-RC-QC c33df62a (11-25 00:14). Work dir intel1 /srv/opentallas-scratch2/claude/QC-SUL1-BAND (OT_LANE=QC-SUL1-BAND).
Types: slw_su_l1__cla2a78701, slw_su_l1__clcc9d0155.
Cause (CENSUS 00:24): STALE-BINS. C1j kits (hf1c bins, target 960, 42-43 taps) placed 5.8k sinks on one tap. C1n c1k_rebin = native 10.5k + 31.7k plan-row sinks AT PLAN SITES; the rows place in the E strip, so the C1n taps split the placed sinks at 1134/1724 max (5/6 taps over 1000).
Row scope = part 3 (re-bin from the placed kit): bins = ALL clk-net sinks of the placed kit (sink_bins_from_place bins, no --native-only):
  cla2a: epyc7 kit .../private/QC-ALLFIX/slw_su_l1__cla2a78701_1124145701 3_place.odb (C1j), 38797 sinks, bins c751196a8227
  clcc:  epyc8 kit .../private/QC-ALLFIX/slw_su_l1__clcc9d0155_1124052823 3_place.odb, 38902 sinks, bins 095ebf1f0bb9
  path physical/die_plan/qwen_compute/plan_of_record/sink_bins/c1o_sul1/<t>__placed.json (overlay: out/sink_bins/c1o_sul1/)
  target stays 400: planned max 691 / 690 (tune.json).
Pipeline: tune.sh -> apply.sh (retap.repoint on C1n) -> scripts/final.py (carry only clock-side changes onto base; reset side stays at base,
  because reset.consumer_sites_um is frozen, so the retap rr_t renames are the RRDRV class) -> proofs.sh -> bind.sh (tree = fork of epyc11 n/tree, rt 6e9705).
Parts 1 (relay_sites band) and 2 (per-lane landing split) are NOT in this row: proposed for C1p after the cla2a probe.
## 02:26 PST state
- ROW-READY posted 02:26 (coord 04b7de6e). Outputs: C1n-r2 a372ae84fa2a -> 7ae1f6fdd22f, C1n-r c26a5b81029d -> 66e4a7cdf610 (scripts/apply2.py = clock side only; the first retap attempt, apply.py, failed and is unused).
- Proofs: proofs.ot (P1, P2), guard.ot (P3 PASS with out/drops_*.txt), epyc2 /srv/opentallas-scratch3/claude/QC-SUL1-BAND/ev_*.json (rreval 0).
- Scoped strict bind: tree = intel1 QC-SUL1-BAND/tree (fork of epyc11 n/tree, plan installed 7ae1f6fdd22f), launch/ = rt 6e9705. bindS.sh (no standalone PRE) -> bindS.ot/bindS.log/bindS/bind_report.json; follow.sh auto-posts the verdict. bind.sh (standalone PRE, then elab/bind into bind/) also runs and is information only.
- Delete when done (ot-delete): tree/, launch/, bind*/ (about 57 GB).
