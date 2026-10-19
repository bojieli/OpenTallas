# Relative XC staircase safe-design review

Prior flat candidate's immutable receipt records GPL-0305 in placement/CTS and repeated trial GRT. No route was submitted. This variant makes a structural change in macro topology and pin groups; density and clock targets are unchanged.

1. PASS source: host inputs land in the collar native pin flops; outputs are native registered R/C calendar or status flops. Reset lands in2 registered kit stages. No synthesis pin stages added, so no unpriced operation latency.
2. PASS planned pipeline reach: outline362.88x250.56um, macro columns with intermediate native cfg registers; no planned one-stage axis reach>405um. Actual mapped wire-reach lint remains an adoption gate.
3. PASS source organization, PENDING mapped confirmation: no shared arbitration added, no new global control, original kept pin-reg rules. Gate fanout lint remains authoritative.
4. PASS prior mapped logic depth368.4ps (same source), pending new placement timing. No false path or multicycle masks.
5. PASS actual storage: two1024x256 programme SRAMs and two128x256 descriptor SRAMs, source byte-identical.
6. PASS new floorplan: four origins on43.2 lattice. Programme-left and descriptor-right columns have41.256um between faces. Vertical same-column gaps59.13um/45.36um; outlineaspect1.45. Full-width standard-cell bandy113.67..129.6, no isolated power region. Host pins N and SM outputs W use complete faces. Synthesis1198um2cells+32412um2SRAM; totalfill~37%, space justified by real macro-face channels and lattice. Gate must validate actual pin geometry/density and utilization.
7. PASS configured policy; PENDING measured CTS: hold margins0.030ns, local CTS, root W beside output register mass. Two-face pin masses may change spread: require TT+FFpin-flop<=80ps and parent-relative boundary audit before adoption. Do not waive failed spread.
8. PASS static calendar: no hardware cycle change, R/C alignment unchanged, direct exactXCbench PASS and five mutantsFAIL with committed witness logs. Native parent/die join and production throughput qualification remain open.

Critical review only: report gate PNGs+facts to coordinator. Do not write REVIEW.json or submit this variant from lane.
