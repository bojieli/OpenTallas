H10wide independent packing candidate

The selected G8 coordinate substitution produces14 overlaps and a345.6um right-seal overrun. The independent candidate preserves all161block bodies and2SerDes reservations, including72frames/12wideH10, with the exact new1782.432x3672 outline and no rotation/shrinking. PHY and16CTRL remain fixed. TenSerDes and their2reservations relocate. Independent geometry_certificate.json verifies33x26mm,100um seal, minimum86.4um body separation.

This is an unbound source-model geometry candidate. Original G8 dimensions for other unclosed masters remain explicit standins. It is not a qualified physical die or an adopted G9 plan. All819logical connections retain source/destination identities and widths; nominal endpoint fractions are reprojected for fresh path pricing. Actual view pin projection, relay body legalization, regionalclock/reset contracts, stage ages/calendar and packageexternal endpoint qualification remain required. No old clock/path/calendar values are inherited.

Constructive run: ep5 unit1110842-1792619213,2orderings, all163bodies placed. The prior bounded240s SMT search was UNKNOWN; fixed-SerDes MaxRects90s ended130/163 without construction. Neither failure proves impossibility. Original evidence is retained in the fleet lane.

Reproduce with gzip -dc baseline_plan.json.gz > input.json; python3 construct.py; python3 verify.py input.json maxrects_candidate.json --out geometry_certificate.json. Heavy construction runs through ot-run; pure verification is local/read-only.
