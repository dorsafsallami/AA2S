import json
import os
import re
import time
from pprint import pprint

import openai
import requests

# -------------------------- Configuration -------------------------- #

# Set your OpenAI API key
openai.api_key = 'put your key here'



# Maximum number of search rounds
MAX_ROUNDS = 3

# Confidence threshold (percentage)
CONFIDENCE_THRESHOLD = 50  # 50%

# -------------------------- Google Search Function -------------------------- #

def google_search(query, result_total=10):
    """
    Conducts a Google search using the provided query and retrieves a specified number of results.
    
    :param query: The search query string.
    :param result_total: Total number of results desired.
    :return: List of search result items.
    """
    def build_payload(query, start=1, num=10, **params):
        """
        Builds the payload for the Google Search API request.

        :param query: Search term.
        :param start: The index of the first result to return.
        :param num: Number of search results per request.
        :param params: Additional parameters for the API request.
        :return: Dictionary containing the API request parameters.
        """
        api_key = "Aput your key here"
        search_engine_ID = "put your key here"
        payload = {
            'key':api_key,
            'q': query,
            'cx': search_engine_ID,
            'start': start,
            'num': num,
        }
        payload.update(params)
        return payload

    def make_request(payload):
        """
        Sends a GET request to the Google Search API and handles potential errors.

        :param payload: Dictionary containing the API request parameters.
        :return: JSON response from the API.
        """
        response = requests.get('https://www.googleapis.com/customsearch/v1', params=payload)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            raise Exception('API key quota exceeded or access forbidden.')
        else:
            raise Exception(f'Request failed with status code {response.status_code}')

    items = []
    pages = (result_total + 9) // 10  # Ensuring we account for all pages including the last one which might be partial
    for i in range(pages):
        start_index = i * 10 + 1
        num_results = 10 if i < pages - 1 else result_total - (i * 10)
        payload = build_payload(query, start=start_index, num=num_results)
        try:
            response = make_request(payload)
            items.extend(response.get('items', []))
        except Exception as e:
            print(f"Google Search Error: {e}")
            break  # Exit on error since there's no alternative API key
    
    
   
    return items

# -------------------------- LLM Functions -------------------------- #

def extract_key_claim(content):
    """
    Extracts the key claim from the input content using OpenAI's GPT model.

    :param content: Input text content.
    :return: The key claim as a string.
    """
    prompt = f"""
    Given the input content below, please summarize the single key claim.

    Input content: {content}

    Please output with the following JSON format:
    {{"key_claim": "XXX"}}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant that extracts key claims from text."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    output = response.choices[0].message['content']
    try:
        key_claim = json.loads(output)["key_claim"]
    except json.JSONDecodeError:
        key_claim = output.strip()
    return key_claim

def generate_query(claim):
    """
    Generates a Google search query based on the provided claim.

    :param claim: The claim to verify.
    :return: The search query as a string.
    """
    prompt = f"""
    Given the claim below, please generate a Google query which can be used to search content to verify this claim.

    Claim: {claim}

    Please output with the following JSON format:
    {{"query": "XXX"}}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant that generates search queries based on claims."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    output = response.choices[0].message['content']
    try:
        query = json.loads(output)["query"]
    except json.JSONDecodeError:
        query = output.strip()
    return query

def analyze_search_result(search_result, claim):
    """
    Analyzes a single search result to determine if it supports, negates, or is baseless regarding the claim.

    :param search_result: A single search result item.
    :param claim: The claim to verify.
    :return: A dictionary with analysis results.
    """
    prompt = f"""
    Below is one web search result:

    Search Result:
    {search_result}

    Below is a claim to be verified:
    Claim: {claim}

    Please perform the following rules to generate an output with this JSON format:
    {{"support_or_contradict_or_unrelated": "support" or "contradict" or "unrelated", "confidence": XX (0-100), "rationale": "XXX"}}

    Rule 1: if the search result content supports the claim, set the "support_or_contradict_or_unrelated" field as "support", and offer a confident score and a rationale.

    Rule 2: if the search result content negates the claim, set the "support_or_contradict_or_unrelated" field as "negate", and offer a confident score and a rationale.

    Rule 3: if the search result content cannot either support or negate the claim, set the "support_or_contradict_or_unrelated" field as "baseless", and offer a confident score and a rationale.

    To clarify: if the content of the search results does not contradict the claim, but lacks some or all of the information presented in the claim, please use the label "baseless" rather than "negate".
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant that analyzes search results against claims."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    output = response.choices[0].message['content']
    try:
        analysis = json.loads(output)
        # Ensure confidence is within [0, 100]
        confidence = analysis.get("confidence", 0)
        if isinstance(confidence, (int, float)):
            confidence = max(0, min(100, confidence))
        else:
            confidence = 0  # Default if not a number
        analysis["confidence"] = confidence
    except json.JSONDecodeError:
        # Fallback parsing if JSON fails
        analysis = {
            "support_or_contradict_or_unrelated": "unrelated",
            "confidence": 0,
            "rationale": "Unable to parse analysis."
        }
    return analysis

def make_final_decision2(claim):
    """
    Aggregates the analyses of all search results to make a final decision using an LLM prompt. If there is no evidence, the function 
    will prompt GPT to classify the claim based on the available text.

    :param claim: The claim to verify.
    :param analyses: List of analysis dictionaries.
    :return: Final decision with confidence.
    """
    print('decision without analyses')
    # If no analyses are available, prompt GPT to classify based solely on the claim text.
    prompt = f"""
    You are an assistant that determines the veracity of a claim based solely on the text provided.

        **Claim:**
        {claim}

        Based on the provided claim, classify whether the statement is real or fake.

        - If you conclude the statement is true, classify it as "real".
        - If you conclude the statement is false, classify it as "fake".
        

        Provide your answer in the following JSON format:
        {{
            "decision": "real" or "fake",
            "confidence": XX  # Confidence score as a percentage between 0 and 100
        }}
        """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant that makes final decisions based on a claim and multiple pieces of evidence."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    output = response.choices[0].message['content']
    try:
        final_decision = json.loads(output)
        # Ensure confidence is within [0, 100]
        confidence = final_decision.get("confidence", 0)
        if isinstance(confidence, (int, float)):
            confidence = max(0, min(100, confidence))
        else:
            confidence = 0  # Default if not a number
        final_decision["confidence"] = confidence
    except json.JSONDecodeError:
        # Fallback decision if JSON parsing fails
        final_decision = {
            "decision": "NEI",
            "confidence": 0
        }

    return final_decision

def make_final_decision(claim, analyses):
    """
    Aggregates the analyses of all search results to make a final decision using an LLM prompt.

    :param claim: The claim to verify.
    :param analyses: List of analysis dictionaries.
    :return: Final decision with confidence.
    """
    print('decision with analyses')

    # Construct a detailed prompt with the claim and all analyses
    analyses_text = "\n".join([
        f"Evidence {i+1}:\nLabel: {analysis['support_or_contradict_or_unrelated']}\nConfidence: {analysis['confidence']}%\nRationale: {analysis['rationale']}\n"
        for i, analysis in enumerate(analyses)
    ])

    prompt = f"""
    You are an assistant that determines the veracity of a claim based on multiple pieces of evidence.

    **Claim:**
    {claim}

    **Evidence and Analysis:**
    {analyses_text}

    Based on the provided web search results, analyze whether the information has enough evidence to decide whether the statement is real or fake.

    - If you conclude the statement is true, classify it as "real".
    - If you conclude the statement is false, classify it as "fake".
    - If the evidence is mixed or insufficient to make a determination, classify it as "NEI" (Not Enough Information).

    Provide your answer in the following JSON format:
    {{
        "decision": "real" or "fake" or "NEI",
        "confidence": XX  # Confidence score as a percentage between 0 and 100
    }}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant that makes final decisions based on a claim and multiple pieces of evidence."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    output = response.choices[0].message['content']
    try:
        final_decision = json.loads(output)
        # Ensure confidence is within [0, 100]
        confidence = final_decision.get("confidence", 0)
        if isinstance(confidence, (int, float)):
            confidence = max(0, min(100, confidence))
        else:
            confidence = 0  # Default if not a number
        final_decision["confidence"] = confidence
    except json.JSONDecodeError:
        # Fallback decision if JSON parsing fails
        final_decision = {
            "decision": "NEI",
            "confidence": 0
        }

    return final_decision

def generate_explanation2(claim, decision, confidence):
    """
    Generates an explanation for the final decision, including reasons, the label, and supporting evidence links. 
    If no evidence is available, prompts GPT to generate an explanation based solely on the claim text and the decision.

    :param claim: The claim to verify.
    :param decision: The final decision ("real", "fake", or "NEI").
    :param confidence: The confidence score as a percentage.
    :param analyses: List of analysis dictionaries.
    :return: A list of dictionaries containing the explanation components (title, rationale, link, etc.)
    """
    explanation_data = []

    # Add the decision label at the top of the explanation
    explanation_data.append({
        "type": "label",
        "label": decision,
        "confidence": confidence
    })
    explanation_data.append({
                "type": "intro",
                "content": f"The classification as {decision} is based on the following evidence:"
            })
    # If no analyses are available, prompt GPT to generate an explanation based on the claim and the decision
    prompt = f"""
        You are an assistant that generates an explanation for a decision based solely on the text of the claim and the classification.

        **Claim:**
        {claim}

        **Decision:**
        {decision}

        **Confidence:**
        {confidence}%

        Based on the claim and the decision, provide a detailed explanation for the classification. 
        The explanation should include reasoning behind the decision, including any relevant context that could support the decision. 
        If the decision is "real" or "fake", explain why. 

        Provide your answer in the following JSON format:
        {{
            "explanation": "<explanation text>"
        }}
        """
        
    response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant that provides explanations for decisions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )

    output = response.choices[0].message['content']
    explanation_data.append({
            "type": "evidence",
            "content": output.strip()
        })
    return explanation_data


def generate_explanation(claim, decision, confidence, analyses):
    """
    Generates an explanation for the final decision, including reasons, the label, and supporting evidence links.
    
    :param claim: The claim to verify.
    :param decision: The final decision ("real", "fake", or "NEI").
    :param confidence: The confidence score as a percentage.
    :param analyses: List of analysis dictionaries.
    :return: A list of dictionaries containing the explanation components (title, rationale, link, etc.)
    """
    explanation_data = []

    # Add the decision label at the top of the explanation
    explanation_data.append({
        "type": "label",
        "label": decision,
        "confidence": confidence
    })

    if decision in ["real", "fake"]:
        # Determine which label corresponds to the decision
        target_label = "support" if decision == "real" else "negate"
        
        # Collect evidence that supports the decision
        supporting_evidence = [analysis for analysis in analyses if analysis['support_or_contradict_or_unrelated'] == target_label]
        
        if supporting_evidence:
            explanation_data.append({
                "type": "intro",
                "content": f"The classification as {decision} is based on the following evidence:"
            })
            
            for idx, evidence in enumerate(supporting_evidence, 1):
                rationale = evidence.get('rationale', 'No rationale provided.')
                link = evidence.get('link', '')
                title = evidence.get('title', 'No title provided.')
                support_label = evidence.get('support_or_contradict_or_unrelated', 'No label provided.')
                explanation_data.append({
                    "type": "evidence",
                    "idx": idx,
                    "title": title,
                    "rationale": rationale,
                    "link": link,
                    "support_label": support_label  # Add the label to each evidence
                })
        else:
            explanation_data.append({
                "type": "no_evidence",
                "content": "No specific evidence was found to support this classification."
            })
    else:
        explanation_data.append({
            "type": "intro",
            "content": "The evidence provided was either mixed or insufficient to make a definitive determination."
        })
        explanation_data.append({
            "type": "analyses",
            "content": "Here are the analyses of the available evidence:"
        })
        
        for idx, evidence in enumerate(analyses, 1):
            label = evidence.get('support_or_contradict_or_unrelated', 'No label provided.')
            rationale = evidence.get('rationale', 'No rationale provided.')
            link = evidence.get('link', '')
            title = evidence.get('title', 'No title provided.')
            explanation_data.append({
                "type": "analysis",
                "idx": idx,
                "title": title,
                "label": label,
                "rationale": rationale,
                "link": link
            })
    
    return explanation_data


# -------------------------- Main Processing Function -------------------------- #

def process_content(content):
    """
    Processes the input content to determine if it's fake, real, or NEI.

    :param content: Input text content.
    :return: Final decision with confidence and explanation.
    """
    round_number = 1
    final_decision = {"decision": "NEI", "confidence": 0}
    explanation = []

    while round_number <= MAX_ROUNDS:
        print(f"\n--- Round {round_number} ---")
    
        # Step 1: Extract key claim
        key_claim = extract_key_claim(content)
        print(f"Extracted Key Claim: {key_claim}")
    
        # Step 2: Generate search query
        query = generate_query(key_claim)
        print(f"Generated Search Query: {query}")
    
        # Step 3: Perform Google search
        try:
            search_results = google_search(query, result_total=10)
            print(f"Number of Search Results Retrieved: {len(search_results)}")
            if len(search_results) != 0:
                # Step 4: Analyze search results
                analyses = []
                for idx, item in enumerate(search_results, 1):
                    snippet = item.get('snippet', 'No snippet provided.')
                    link = item.get('link', 'No link provided.')
                    title = item.get('title', 'No title provided.')
                    search_result = f"Title: {title}\nLink: {link}\nSnippet: {snippet}"
                    print(f"\nAnalyzing Search Result {idx}:")
                    print(search_result)
                    analysis = analyze_search_result(search_result, key_claim)
                    pprint(analysis)
                    # Ensure that title and link are correctly assigned
                    analysis['title'] = title
                    analysis['link'] = link
                    analyses.append(analysis)
    
                    # Step 5: Make final decision using LLM
                    decision = make_final_decision(key_claim, analyses)
                    print(f"\nFinal Decision: {decision['decision']} with confidence {decision['confidence']}%")
    
                    # Step 6: Generate explanation
                    explanation = generate_explanation(key_claim, decision['decision'], decision['confidence'], analyses)
                    print("\n=== Explanation ===")
                    print(explanation)
                    # Check if we need to re-trigger retrieval
                    if decision["decision"] != "NEI" and decision["confidence"] >= CONFIDENCE_THRESHOLD:
                        final_decision = decision
                        break
                    else:
                        final_decision = decision
                        round_number += 1
                        print("Confidence below threshold or NEI. Initiating another retrieval round.")
            else:
                # Step 5: Make final decision using LLM
                decision = make_final_decision2(key_claim)
                print(f"\nFinal Decision: {decision['decision']} with confidence {decision['confidence']}%")
    
                # Step 6: Generate explanation
                explanation = generate_explanation2(key_claim, decision['decision'], decision['confidence'])
                print("\n=== Explanation ===")
                print(explanation)
                break
    
            
        except Exception as e:
            print(f"Google Search Error: {e}")
            #break  # Exit if search fails   
            
    
    print("\n=== Final Decision ===")
    pprint(final_decision)
    return final_decision, explanation
            


