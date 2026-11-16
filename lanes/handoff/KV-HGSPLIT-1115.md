# KV-HGSPLIT-1115 handoff
Base 7u b7156937f334. Work dir epyc10 /srv/opentallas-scratch2/claude/kv-hgsplit-1115 (v2 = band-near placement, not bindable; v18 = tap-stable, G0 PASS; v19 = v18 minus raw rows, bind 0 errors, R8 changed 0, LATCHECK 2404/2404; v20 = v19 + kse_rawfix raw rows, plan sha 2579d59dc225, G0 PASS 0 errors; v20 bind+LATCHECK running: out/v20.bind.out).
Recipe: hgsplit.py BASE OUT --margin 8.64 --site-clear 1.5 --keep-taps ; setcells.py OUT OUT2 census.tsv ; strip landing_raw_branches ; strict bind ; kse_rawfix raw --bind-rtl ; full gate.
Files in lanes/handoff: KV-HGSPLIT-1115-{hgsplit.py,setcells.py,rows.tsv,census.tsv,displacement.tsv}.
Open: 3 rings soft (hgi_v3/v4/v5 ectl W1560); displacement median 117 um (27 over 340); COORD r216 wants band-side placement + one-step re-solve of taps/reset/stations; station rows u_hstN->u_headN not included (needs RTL decision F1b).
Masters mostly unsigned (planned cores); no new masters needed.
