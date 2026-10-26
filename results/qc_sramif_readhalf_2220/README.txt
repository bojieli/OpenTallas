Extend the same clock half-cycle capture to SRAM read address/enable, default OFF.
Existing MIF rising staging is retained; a falling-edge landing is inserted before the SRAM read pins.
No read/write-consumption, data, fault or boot cycles added. Final SRAM inputs are all falling-edge landings.
Adds36PROG/32BTAB falling FF beyond write-half candidate (total986PROG/1088BTAB falling FF).
Actual20k-cycle lockstep compares every SRAM consumed READ/WRITE at its original rising edge, outputs and fault; reset bursts and directed same-row read/write collisions included.
Nominal0differences. Only read-landings changed to wrong rising edge mutant caught consumed readenable cycle13.
Prior write-only v1 physical evidence remains FAIL clock20.6/20.1,18readcontrolhold and935inputhold; no failed verdict overwritten.
RD physical candidate still requires fresh synthesis/geometry and both actual416.5pshalfcycle checks; no exceptions/clock relaxation/adoption claimed.
