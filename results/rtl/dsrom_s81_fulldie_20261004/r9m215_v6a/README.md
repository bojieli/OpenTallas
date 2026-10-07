# S81 v6a (r9m215khdc: v5 + --hop-fix --meso-d8 --cfifo-v2), EPYC2 cases/v6a

Round trip scan 159 / layer1 163 / head 159; python legality 0, pin clashes 0.
PA legality overlaps 41 / 52 / 54 and GRT i50 overflow scan 1,511 (v5 341) / layer1 233 (137) / head 993 (466):
the hop stations were placed anywhere on the die and crowded the HC corridor / VCH crossing (hc_s<->hc_n, rE*, aSE, KE0r).
v6b restricts them to the die channels and frame regions (re-run).
