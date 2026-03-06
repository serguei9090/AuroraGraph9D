import json

new_cases = [
    {
        "id": "FIN-001",
        "category": "finance_aggregation",
        "query": "What was the total net revenue, EPS, and operating margin for OmniCorp Global in FY2025 compared to FY2024?",
        "expected_keywords": ["14.2 billion", "12.03", "5.45", "4.12", "22.1%"],
        "ground_truth": "FY2025 net revenue was $14.2 billion (up 18% from FY2024's $12.03 billion). EPS diluted climbed from $4.12 to $5.45. Operating margins expanded by 240 basis points to 22.1%.",
    },
    {
        "id": "FIN-002",
        "category": "finance_aggregation",
        "query": "Summarize the B2B AI software suite OmniMind's key metrics including CAC, LTV, and churn rate.",
        "expected_keywords": ["12,500", "185,000", "14.8x", "1.2%"],
        "ground_truth": "OmniMind's CAC was $12,500, LTV was $185,000, LTV:CAC ratio reached an industry-leading 14.8x, and churn rate dropped to 1.2% annually.",
    },
    {
        "id": "FIN-003",
        "category": "finance_aggregation",
        "query": "What were the factors causing the Consumer Hardware gross margin to shrink, and what was the margin?",
        "expected_keywords": ["29%", "Neodymium", "Dysprosium", "silicon", "15%"],
        "ground_truth": "Hardware gross margin shrank from 34% to 29% due to a 15% increase in rare-earth metal costs (Neodymium/Dysprosium) and a 10% tariff hike on imported silicon wafers in October.",
    },
    {
        "id": "FIN-004",
        "category": "finance_aggregation",
        "query": "What were the board actions taken in November 2025 regarding share repurchases and dividends?",
        "expected_keywords": ["5 billion", "12%", "0.48", "repurchase"],
        "ground_truth": "In November 2025, the Board authorized a $5 billion share repurchase program and increased the quarterly dividend by 12% to $0.48 per share.",
    },
    {
        "id": "FIN-005",
        "category": "finance_aggregation",
        "query": "What is the forward guidance for full FY2026 revenue and CapEx?",
        "expected_keywords": ["16.5 billion", "17.0", "3.5", "Reykjavik", "Santiago"],
        "ground_truth": "FY2026 projecting total revenue of $16.5B to $17.0B. CapEx expected to peak at $3.5 billion to build data centers in Reykjavik and Santiago.",
    },
    {
        "id": "ABS-001",
        "category": "abstract_reasoning",
        "query": "Explain the Gettier Problem, when it was published, and its impact on the JTB definition of knowledge.",
        "expected_keywords": ["1963", "Justified True Belief", "Smith", "luck"],
        "ground_truth": "Published in 1963, Gettier provided counterexamples (like Smith and the coins) showing that Justified True Belief (JTB) is not always knowledge because beliefs can be true due to luck.",
    },
    {
        "id": "ABS-002",
        "category": "abstract_reasoning",
        "query": "What is the key difference between Endurantism and Perdurantism regarding how objects persist?",
        "expected_keywords": [
            "Endurantism",
            "Perdurantism",
            "temporal parts",
            "entirely present",
            "four-dimensional",
        ],
        "ground_truth": "Endurantism claims an object is entirely present at every moment it exists. Perdurantism (Four-Dimensionalism) argues objects extend through time and have 'temporal parts' like temporal tree layers.",
    },
    {
        "id": "ABS-003",
        "category": "abstract_reasoning",
        "query": "Summarize Hilary Putnam's semantic externalism and the Twin Earth thought experiment.",
        "expected_keywords": ["Hilary Putnam", "1975", "XYZ", "H2O", "in the head"],
        "ground_truth": "Putnam's 1975 essay argued 'meanings just ain\\'t in the head.' In the Twin Earth experiment, 'water' refers to H2O on Earth and XYZ on Twin Earth, meaning words refer to external substances despite identical psychological states.",
    },
    {
        "id": "ABS-004",
        "category": "abstract_reasoning",
        "query": "What is Husserl's concept of intentionality and how did Heidegger expand on it with Dasein?",
        "expected_keywords": [
            "intentionality",
            "Husserl",
            "Heidegger",
            "Dasein",
            "ready-to-hand",
        ],
        "ground_truth": "Husserl defined intentionality as consciousness always being 'directed toward' something. Heidegger (1927) expanded this with 'Dasein', arguing we are thrown into the world, engaging with tools (ready-to-hand) rather than objectively observing them.",
    },
    {
        "id": "ABS-005",
        "category": "abstract_reasoning",
        "query": "Explain the Ship of Theseus thought experiment as recorded by Plutarch and expanded by Hobbes.",
        "expected_keywords": ["Plutarch", "Hobbes", "decay", "second ship", "planks"],
        "ground_truth": "Plutarch asked if a ship whose planks are entirely replaced over time is the same ship. Hobbes asked what if someone gathered the discarded planks to build a second ship, challenging continuity of form vs matter.",
    },
]

file_path = "tests/golden_dataset.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

data.extend(new_cases)

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Added {len(new_cases)} new cases to the golden dataset.")
