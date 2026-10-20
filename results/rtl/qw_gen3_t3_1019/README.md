# GEN3 structural landing channels, takeover3 Oct19

Source engineering on frozen e60fb2eed; private opt-in, no physical/adoption claim.
The original dv2f19g3 exit4/no-free-landing-site is retained, not retried in place.
The new source owns full-height86.4um column channels and129.6um slice N/S gaps.
All60 hard bodies keep their exact widths/heights/relative internal geometry;
cluster rows follow their actual slice column. Full-shape model has zero hard
body overlaps, 32.6808×24.2136mm outline within the owner's26×33mm, +28.495619mm²
against the same source with legacy43.2um slice gaps. No new die required by this
geometry model. Actual PG/clock/transport placement and legalization may still fail.

Lateral landing frames exchange N/S/E/W dimensions and quantize each target axis;
the emitted master's actual faces are selected from its actual neighboring hops.
This is not a pin-density waiver or a rotated macro with unchanged pin transforms.
The complete existing ring area remains; wide1088-bit lateral frames have the
long data face on E/W. Default zero column gap preserves the legacy source behavior.

Existing frozen446-list cost remains1,154,266FF/13.079mm² and conservative+45cycles
per layer/+1620cycles (1.35us) per36-layer token. This is not a new qualified token
rate. Twenty additional R2 hard crossings and any extra transport introduced by
geometry must be measured from the completed GEN and compiler, never silently free.
OVL/new safe kits and directional physical landing masters remain declared stand-ins.

Native pickup: rC/rD both intra0/655, all153existing lanes measured, maximum drift
302.5/371.6ps below half-period; overall verdictFAIL because446links/186347bits
still unlanded and8no-root. rC has real unpadded forwarded spine10026cells414levels,
model insertion23272.9ps; rD is ideal-entry control. Do not claim a production clock
closure from either. dv2f19g2/g2j remain live in PDN, real-case legal28662/28638inst.
Saved dh2diag terminalGRT overflow7089 and severe TT/FF setup/hold failures are
explicit diagnostic records, not a die result.

Validation: all11channel+BOOTCTX testsPASS; Python compilePASS. Initial10PASS/1FAIL
was a local sparse-checkout setup error (tools/die_port_bind.py omitted, Python
imported the older same-name qwen_split module); adding the exact source dependency
resolves it without code/check changes. Source/model generation is permitted;
no physical submission yet.

Additional contact audit: the legacy generated M.face implementation uses
pitch_tr1/2 (=.048/.096um), so the larger frame's average bits/face dimension
DOES NOT establish the actual local <=6contacts/um requirement. This entire
source GEN remains diagnostic. A new directional physical kit needs >=4tracks
(.192um actual pitch), real pin rectangles and the corresponding enlarged
face spans (548bits needs~109um,1088bits~213um). No contactPASS is claimed.

Fresh source-only GEN: dv2f19g3c1, ot-epyc6 unit1181378, native PythonPID1182671,
48GB/1thread admission against917GB available and5505GB scratch. Exact66e6d5622
source overlay of the frozen predecessor; no place/PDN/route. SOURCE_COMMIT's
literal text accidentally says "2Tcl"; only dv_case.py and qwen_rom_fulldie_b3r2.py
are executable changes (two Python files). The authoritative exact commit and
content hashes, not that descriptive typo, identify the source.
