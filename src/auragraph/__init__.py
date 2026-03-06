"""
AuroraGraph 10D
================
High-Performance 10D Knowledge Graph & Deterministic Reasoning Engine.

Quickstart::

    from auragraph import AuroraGraphEngine

    engine = AuroraGraphEngine()
    engine.ingest("./my_docs")
    engine.query("What are the core revenue drivers?")

GitHub: https://github.com/serguei9090/AuroraGraph9D
"""

__version__ = "0.1.0"
__author__ = "AuroraGraph Contributors"
__license__ = "MIT"

# Convenience top-level imports
from auragraph.core.config import config
from auragraph.core.engine import AuroraGraphEngine
from auragraph.db.base import BaseGraphDB

__all__ = [
    "AuroraGraphEngine",
    "BaseGraphDB",
    "config",
    "__version__",
]
