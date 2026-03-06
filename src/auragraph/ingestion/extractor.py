from typing import Dict, List

import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("[!] Spacy model 'en_core_web_sm' not found. Run: uv run python -m spacy download en_core_web_sm")
    nlp = None


def extract_triples(text: str) -> List[Dict[str, str]]:
    """
    Extracts (Subject)-[Predicate]->(Object) triples from text
    using SpaCy dependency parsing.

    Returns a list of dicts: {"subject": str, "predicate": str, "object": str}
    """
    if not nlp:
        return []

    doc = nlp(text)
    triples = []

    for token in doc:
        # Looking for the main verb
        if token.pos_ == "VERB":
            subject = None
            obj = None

            # Find subject and object children
            for child in token.children:
                if child.dep_ in ("nsubj", "nsubjpass"):
                    # Get the full noun chunk for the subject
                    subject = " ".join([t.text for t in child.subtree]).strip()
                elif child.dep_ in ("dobj", "pobj", "attr", "acomp"):
                    # Get the full noun chunk for the object
                    obj = " ".join([t.text for t in child.subtree]).strip()

            if subject and obj:
                triples.append(
                    {
                        "subject": subject,
                        "predicate": token.lemma_.upper(),  # Canonicalize verb
                        "object": obj,
                    }
                )

    return triples
