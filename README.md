# ClaimVerAgents: Retrieval-Augmented Multi-Agent Fake News Verification

ClaimVerAgents is a modular and interpretable framework for real-time fake news detection. It uses Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) within a multi-agent architecture. The system extracts claims, retrieves live evidence from the web, evaluates credibility, and delivers explainable decisions.

## Features

- Modular, multi-agent architecture
- Each agent powered by a large language model (LLM)
- Real-time evidence retrieval via Google Search API
- Confidence-based multi-round verification
- Support for abstention using NEI (Not Enough Information)
- Structured JSON explanations with evidence rationales and source links

## Installation

1. Clone the repository:


2. Install the required dependencies:

    ```
    pip install -r requirements.txt
    ```

3. Create a `.env` file in the root directory and add your API keys:

    ```
    OPENAI_API_KEY=your_openai_key
    GOOGLE_API_KEY=your_google_key
    SEARCH_ENGINE_ID=your_search_engine_id
    ```
## Usage

Run the system from the command line:

    python agents_LLM_RAG.py
    


You will be prompted to enter a news article or claim. The system will:

- Extract the key factual claim
- Generate a search query
- Retrieve relevant evidence from the web
- Evaluate the credibility of sources
- Output a verdict: `real`, `fake`, or `NEI`
- Generate a structured explanation with supporting rationale

The results will be saved as a JSON file in the `timestamps/` directory.

## Output Format

The output is saved as a JSON file with the following structure:

```json
{
  "input": "Text to verify...",
  "decision": {
    "decision": "fake",
    "confidence": 89
  },
  "explanation": [
    {
      "type": "label",
      "label": "fake",
      "confidence": 89
    },
    {
      "type": "intro",
      "content": "The classification as fake is based on the following evidence:"
    },
    {
      "type": "evidence",
      "idx": 1,
      "title": "Fact Check: No, California Didn’t Turn Away Fire Trucks...",
      "rationale": "This article refutes the claim.",
      "link": "https://example.com",
      "support_label": "negate"
    }
  ]
}
```

Each explanation includes the decision label, a short summary, and evidence with title, rationale, and link.


## Dataset and Evaluation

The system was evaluated using a cleaned version of the PolitiFact dataset, which is included in this repository as:
    ```
    politifact.csv
    ```


This dataset provides a structured benchmark for claim verification. Unlike static-only approaches, ClaimVerAgents uses live web search in addition to the dataset to generalize to unseen claims and improve real-time adaptability.

### Performance Summary on PolitiFact Dataset

| Model              | Real F1 | Real P | Real R | Fake F1 | Fake P | Fake R |
|-------------------|---------|--------|--------|----------|--------|--------|
| ClaimVerAgents3.5 | 0.82    | 0.71   | 0.99   | 0.74     | 0.98   | 0.59   |
| ClaimVerAgents4   | 0.85    | 0.83   | 0.86   | 0.83     | 0.84   | 0.83   |

## License

This repository is released for peer-review purposes only. License terms will be specified upon publication.

## Acknowledgment

This repository is part of an anonymous submission. Author names and affiliations have been omitted in accordance with the double-blind review process.
