"""Full-chip hierarchical implementation flow (docs/FULL_CHIP_IMPLEMENTATION.md).

Modules:

* ``macros``     -- LEF / Liberty / Verilog views for placeholder macros
                    (multi-port SRAM, ROM banks, PHY and link black boxes)
                    until the memory compilers land;
* ``boundary``   -- per-port boundary characterisation of a synthesised block;
* ``budgets``    -- block I/O timing budgets derived from the top-level
                    floorplan, and the SDC each block is re-closed against;
* ``floorplans`` -- the tile and die floorplans of the three architectures;
* ``orfs``       -- the OpenROAD-flow-scripts driver shared by every level;
* ``harden``     -- harden one block into a macro with abstracts;
* ``assemble``   -- a parent level (tile or die) built from hardened macros;
* ``report``     -- the records and budget tables under
                    results/physical_abi3/asap7/chip/.
"""
