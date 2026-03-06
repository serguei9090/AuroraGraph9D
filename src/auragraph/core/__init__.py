"""
auragraph.core
==============
Core orchestration layer: AuroraGraphEngine and configuration.
"""

from auragraph.core.config import config
from auragraph.core.engine import AuroraGraphEngine

__all__ = ["AuroraGraphEngine", "config"]
