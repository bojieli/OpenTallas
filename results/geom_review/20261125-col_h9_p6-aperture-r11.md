# S81 R11 P6 central aperture candidate

Exact candidate `7dcdbee0664b93d75a2b4e23b71151e92c7e4611dffa415df590b3abdee24704`. Viewed the type render under `epyc12:/srv/opentallas-scratch2/claude/FP-S81/render/c_street_r11_p6_physical_1125/review_corrected/` and compared with the prior static arm `ec988d6312d3`.

**Place comparison candidate.** Seven further moves widen the physical central gap between the lower ROM groups from 25.380 to 38.340 µm and the upper gap from 24.804 to 29.124 µm. The central opening still narrows at the upper band and the return by the east CFIFO stays tight. Modeled route-supply p99 drops from 5.818 to 3.876 while peak horizontal core supply pressure rises from 2.579 to 2.831. A placed density and path comparison is needed to see how traffic uses the added space.

The generator retained all 21 stages and the die envelope. The planned maximum measured hop is 397.3 µm, with zero reach gate, equivalence, or physical core overlap findings from the generator. The old lean render drew five overlaps from raw core origins. The corrected render uses each signed track offset and shows zero physical overlaps. The base's inherited 30.7 µm reticle-width excess is still present. Scoped PRE is running. Strict bind and owner review precede any CAD dispatch.
