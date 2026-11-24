# S81-OWN-COLH10 (08:5x 11-24 PST)
Job: own S81 col_h10_r0_p1 x5, col_h10_r1 x5, col_h10_r2 x12; adopt/launch kits, drive to sign-off, hand structural census causes to S81-ALLFIX-INT.
State 08:5x: all held at prelint; waiting INT c8 KITS GO + S81-C9-ROWS SWAPPED. Consumer list lanes/handoff/S81-C9-ROMHW-CONSUMERS.txt. Kits only from c9seal_tree --src-manifest seal. Old COL context: lanes/handoff/S81-ALLFIX-COL.md, FAM-S81-COL-H10-R4.md.
## 12:3x 11-24
FT405 RSTREACH: variants va (d40_dl60) vb (d20_dl100) built (epyc9 s81-own-colh10/row_va.json,row_vb.json; rebase.py applies to c9s with old-check + latency deltas). Scoped binds on c8 p6w_sg running epyc9 units oth-ubuntu-727906-1795557807, oth-ubuntu-727782-1795557807, logs s81-own-colh10/scope_bind_{va,vb}.log. On first no-RSTREACH: ot-run --cancel the other, rebase to c9s, ROW-REBASED to S81-ALLFIX-INT. c9 tree fork fails while INT binds (live tree).
