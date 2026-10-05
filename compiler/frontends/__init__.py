"""Model front ends that export into the shared, backend-neutral IR.

Each front end reads one pinned source checkpoint and emits a document that
both the HBM/SRAM backend and a ROM backend consume unchanged.  A front end
never names a memory target, a schedule, or an engine instance; those belong to
the backend Physical Plan IRs (ADR-003 section 15).
"""
