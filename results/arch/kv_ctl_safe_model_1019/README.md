# KV CTL mu5 structural model: HOLD before source or a new gate

Exact source c5fbbded9, existing mu5 gate on ot-epyc6 at
`/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_ctl_mu5-20261019-115839`.
The live mu5/mu5b gates remain diagnostic evidence. No RTL, kit, macro, clock,
calendar, or running job was altered. This packet is an incomplete structural
model, not a SAFE source or permission to build.

## Actual native all-driver audit

`census.py` read the existing **3_2_place_iop.odb**, SHA256
`fcbc77429404faa5ab91981c1901b93dfb43f5b254bc0992e0d9cdd38460af0a`.
It counts unique native endpoint pins through every BUF/INV/HB chain, including
FF, combinational, input, tie, and macro drivers; it excludes PG and clock pins.
No synthesis or placement was repeated. Fleet ot-run unit
`oth-ubuntu-1969229-1792439193` completed exit0. The first launch exited127
because OpenROAD was not on the image PATH; the corrected absolute executable
was `/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad`.

| Driver | Roots | Maximum logical fanout | Roots >32 |
|---|---:|---:|---:|
| FF | 17,394 | 1,033 | 111 |
| Combinational | 21,149 | 2,336 | 74 |
| Input | 1,729 | 13 | 0 |
| Macro output | 584 | 4 | 0 |
| Tie | 7,029 | 1 | 0 |

The mapped design has 79,962 cells and **185 unsafe roots**. Examples:
`u_fanr.ph1` FF1033, `u_wprg.ld` FF325, `u_own.g_mu.rn` RESETN303,
and many writer reset leaves RESETN256. The worst OR root drives2336 actual
logic inputs. Therefore the old four/three reset copies and max256 relay
policy do not solve this tile. Sixty unsafe roots drive only RESETN: at least
148 extra same-edge reset FF copies are needed. The other125 roots need at
least436 extra driver equivalents. These are lower bounds, not a completed
copy forest: duplicating a driver adds predecessor loads and must be solved
to a fixed point, preserving functional conditions, reset polarity and updates.
Combinational copies can merge; a buffer/inverter tree does not close logical
fanout. `census.json.gz` contains every root and all unsafe endpoint identities;
`census_summary.json` is the compact review view.

## Storage and existing n64 alternative

The three current128x256 macros each expose410/409 contacts over41.064um
(9.984/9.960 perum), above6. Face area and average tile density cannot waive it.
Current useful boot state is20,736 bits plus288 derived gap flags. Of these,
136 bits are the four stage-1 gap registers with flags; macro useful state is
20,888 bits. Exact row widths are256 (lprg A),168 (lprg B),160 (writer).
Replacing them with **4+3+3 existing n64 macros** gives10 macros,81,920 physical
bits,9,298.6272um2 macro area. The old three macros occupy11,681.558208um2.
Upper padding remains physical pins and is included; all2,100 contacts count.

Candidate family `ot_sram_1r1w2c_128x64_m1` exists at HBM bc42f77a8. Its exact
JSON and view hashes are copied to `n64_family.json`:33.720x27.576um,
105 contacts perface=3.808/um. It has **two clock pins**, both tied to the tile
clock only if selected:20 actual contacts total, TT186.916/FF207.464/SS173.6752fF.
This is an analytical abstract calibrated on measured ASAP7 bitcells/standard
cell FO4, with explicit assumed dual-port/periphery terms; no macro transistor
layout, SPICE, or silicon qualification. No HBM whole-tile qualification transfers.

Registered read is one edge and holds when disabled. The existing dual-clock
behavior uses separate active-event read/write processes and **does not promise
OLD data on a simultaneous same-address access**. CTL intends boot-only writes
and reads only after seal; this must be proved under arbitrary macro power-up,
reset/reboot, last-write/seal/start and illegal rewrite before replacement.
The old repair inputs are tied off in this candidate; n64 has no repair spares.
No functional repair or ECC claim is added. The academic no-new-ECC policy
remains applicable, with fault-free mutable memory assumptions.

## Bounded physical and schedule proposal

`model.json` records ten lattice origins in two columns x86.4/216 and five rows
y43.2/129.6/216/302.4/388.8, R0, within the current345.6x475.2 outline. Vertical
pitch86.4 leaves58.824um clear; horizontal gap95.88um. A proposed connected
full-width std-cell band at y250.56..293.76 has43.2um height between macro rows;
clock entry would align with that band at y272.16. This is geometry feasibility,
not placement, reach, clock or PG proof. Final std area after all functional
copies, utilization, maximum stage reach and delay remain NULL. The parent
1123x172.8 slot cannot host this outline; a real parent regrant is required.

The exact n64 LEF has side M4 signal rectangles0..0.024 and33.696..33.720,
PG stripes on M4 from x0.300..33.420, and M1..M3 full OBS plus M4 interior
OBS x0.072..33.648. These are not interchangeable with a dense family abstract.
All proposed lattice positions must be checked against actual parent track
phase, PG stripe polarity/origin, contacts, via enclosures and halo escape.
The contact average alone does not establish legal access.

Target extra edges are0 for n64 and same-edge useful copies. Existing mu4
prices stay: QUIET window +1 before enter/leave, abort observation +1, and
input/output face capture +1 each. Full source replay must preserve every
compiler event edge. Whole SU and MU token deltas remain NULL until composed
with the real die; no timing or token-rate qualification is claimed.

Next: coordinator model review; prove boot/no-overlap; choose n64 versus the
separate reviewed wider-pitch model; complete the185-root copy fixed point and
synthesis-priced floorplan/regrant. Only then implement opt-in source, whole-tile
lockstep/mutants and SAFE checklist review before any new physical gate.
