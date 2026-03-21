"""
Degradation model package — Task 2B.

This package will contain:
- ``DegradationModelProtocol`` (defined in bess_engine.engine)
- ``NRELSmith2017Model`` — semi-empirical model with 8 state variables
- ``RainflowCounter`` — ASTM E1049 cycle counting
- ``ChemistryParams`` — chemistry-specific parameter sets
- ``PassthroughDegradation`` — no-op model for testing Task 2A in isolation

Only the passthrough model is implemented here.  The full degradation
models are Task 2B deliverables.
"""

from degradation.passthrough import PassthroughDegradation

__all__ = ["PassthroughDegradation"]
