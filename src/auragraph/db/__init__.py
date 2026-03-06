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
from auragraph.db.kuzu import KuzuDB
from auragraph.db.neo4j import Neo4jDB
from auragraph.db.sqlite import SQLiteFTS5DB

__all__ = ["BaseGraphDB", "SQLiteFTS5DB", "KuzuDB", "Neo4jDB"]
