# Setup repair transform isolation

Same original immutable source/checkpoint, every HB/driver/net protection retained. Each setup replay restricts the transform sequence and bounds it to one iteration, preserving actual STA constraints and margins. SizeUpMove-only does not reproduce the initial protected-net error and continued through unchanged hold repair; it ends FF hold -37.86ps and is not timing qualified. BufferMove-only returns without the protected-net error and intentionally stops. CloneMove-only reproduces ODB-0373 on ot_inhold_n00001 before the first repair iteration, exactly as the unrestricted setup repair.

This attributes the initial failure to CloneMove in the tested configuration. It does not establish all future paths are safe under the other transforms, authorize suppressing cloning in production, or admit any negative timing. Raw logs and exact hook/run scripts are preserved. Each run uses a separate checkpoint copy; original snapshot remains read-only.
