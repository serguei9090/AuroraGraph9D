"""
auragraph.db
============
Pluggable graph database backends implementing BaseGraphDB.

Supported backends:
- SQLiteFTS5DB  → Fast keyword retrieval for local/dev use.
- KuzuDB        → Embedded high-performance property graph.
- Neo4jDB       → Enterprise-scale managed graph cluster.
"""

from auragraph.db.base import BaseGraphDB

# We avoid top-level imports of KuzuDB, Neo4jDB, etc. to support optional dependencies.
# Users should import them directly from their modules:
#   from auragraph.db.kuzu import KuzuDB

__all__ = ["BaseGraphDB"]
