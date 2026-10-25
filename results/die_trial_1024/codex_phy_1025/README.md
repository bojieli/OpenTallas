# Declared PHY supply window measurements, 2026-10-25

The separate VDDPHY supply and dedicated 45-um PG rows from owner decision7 have now been exercised in PDNSim. The earlier tool ignored `die.pg.domains`; its historical shared-grid failures are preserved.

| Vehicle | Power assumed | PG sources | Worst / average drop | Wall / peak RAM |
|---|---:|---:|---:|---:|
| S81 WS0 horizontal PHY |0.2361W|640|2.55 /0.746mV|377.1s /6.17GB|
| S81 WS3 vertical reserve PHY |0.2052W|539|2.74 /0.562mV|470.5s /5.47GB|
| Head HOST0 PHY |0.612W|1728|3.12 /0.591mV|821.5s /15.72GB|

All pass separate VDDPHY and VSS connectivity checks and complete the actual PDNSim solver. Grid/bump diagrams were viewed before the run; IR maps were viewed after it. Worst points lie in the planned63.64-um bump-free fringes. Head HOST0 represents the common geometry of12 head PHY domains; S81 has7 domain geometry classes, of which the horizontal and narrow vertical examples were measured here.

These are standalone window results at explicit uniform0.15W/mm² and nominal0.7V, not whole-die IR signoff. Actual selected PHY power, package signal/PG bump mapping and coupled core-ground loading are still inputs to the final measurement. The old235/270mV figures used different windows and a shared grid; they are not a like-for-like quantitative comparison.

Reproduce: `python3 tools/die_plan/phy_ir.py PLAN --domain NAME --density .15 --out DIR`, view `domain_review.png`, then `ot-run --mem64 --threads8 --dir DIR -- bash DIR/run_psm.sh` (insert spaces after flag names). Collect with `python3 tools/die_plan/phy_ir.py --report DIR`.

Sources: S81 xdie3@69f1ce1a87 and head3@612e029779; each metadata file includes the exact source-plan SHA256. New source is self-contained against the main die_trial helpers and does not require the unmerged trial WIP.
