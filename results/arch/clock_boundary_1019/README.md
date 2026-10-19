# Structural clock boundary census

The inherited main test found that production clock insertion still selected input/output registers with timed paths. A false-path data input could therefore vanish from physical clock spread measurement. The fix selects structural endpoints/startpoints with all arcs, excludes asynchronous-control pins, and keeps only cells of the clock being measured. Setup/hold constraints and uncertainty are unchanged.

The actual Yosys/OpenSTA fixture sets false paths on the input/output, proves the input timed path is absent, and still finds exactly the capture and launch cells. Reset-only, interior and other-clock cells stay outside the boundary. The fixture Liberty checks graph behavior and is not physical signoff evidence. Six focused tests pass; broader clock tests have only the seven fixture/environment failures already recorded by the ROOT baseline. Historical closures and their original measurements are preserved.
