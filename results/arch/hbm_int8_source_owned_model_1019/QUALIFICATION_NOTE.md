# Governing qualification for the source-owned INT8 model

This note corrects wording in the immutable `b198c841b` README. The governing release checks are **TT setup >= 0, FF hold >= 0, and TT/FF clock spread <= 80 ps**, together with the full source, native electrical, geometry and PG obligations. Its references to “SS setup” and “SS/FF endpoint budgets” are not an alternative qualification policy.

The packet's TT and FF characterized-axis calculations remain exactly as recorded. In particular, the 48 negative FF *setup* residual rows are supplemental analysis; they are not the required FF hold result. No actual FF hold closure follows from those calculations. The 144 negative TT setup bounds are conservative independent-axis bounds, not observed endpoint slack or proof of physical impossibility. A justified waveform, actual wire/phase model and complete TT-setup/FF-hold evaluation remain required.

The clock interval upper bounds above 80 ps fail to establish the required guarantee; they are not measured clock spread. Actual clock phase and wire remain unqualified. No implementation, engine invocation, timing pass or adoption is authorized by this note.

All original source, models, README, outputs and their 48-entry output hash inventory remain unchanged. This is a separate documentation correction, not a replacement measurement.
