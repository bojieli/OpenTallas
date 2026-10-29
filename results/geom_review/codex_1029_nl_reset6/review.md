# NL reset6 independent placement review

Verdict: PASS-COND for one diagnostic GRT50 after current LEC and planned clock geometry are qualified. Current placement alone does not authorize CTS/DRT/sign-off.

Personally viewed nl_reset6_place.png from intel1 qca0k11/geom. Parent outline457.92x1157.76,18 macro blocks in two lower columns and three upper columns. Macro walls are separated by a continuous central street; no std-cell/macro overlap. The narrow logic strips along the right central wall match the reported channel_v1.501/col_v1.817 hotspot atx256..266,y522.5. Current repaired reach404.35um/0bad and pin p908.99um are the actual placement outputs; no relay collapse.

Owner actual cut-net packet has926 net boxes/982 weights.285 boxes have width<=1um, including183 place-resizer nets;339 place-resizer nets total. This stacks estimated vertical projection beside the macro wall. Approximate central street width73um gives3517 raw Vtracks at48.18/um, so982 weighted demand is~0.28 of gross width, before other loads. This supports one GRT50 diagnostic rather than an outline change from this estimator alone. If it exposes real overflow, spread combin/resizer nodes across at least34um of the central street (roughlyx215..256), preserving explicit FF anchors and all cycles. No pin split or macro widening proposed.

Aspect2.528 and partial E/W pin faces follow the fixed parent ABI; no interface change is authorized here. Clock762.57um is from entry to farthest sink with no structured interior clock cells yet; a balanced spine/tree plan remains required before CTS. Fresh-gate LEC remains a separate unresolved launch precondition. Prior AUTO FAIL is retained; this is a manual diagnostic-only scope, not blanket closure.
