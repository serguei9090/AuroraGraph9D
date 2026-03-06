"""
auragraph.ingestion
===================
Document parsing and knowledge extraction pipeline.

- parsers.py   → Rust-backed recursive chunking + metabolic filtering.
- extractor.py → Triple extraction for (Subject)-[Predicate]->(Object) graphs.
"""

from auragraph.ingestion.extractor import extract_triples
from auragraph.ingestion.parsers import extract_chunks

__all__ = ["extract_chunks", "extract_triples"]
