import os
import json
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
NOVA_MODEL_ID = os.getenv("NOVA_MODEL_ID", "amazon.nova-lite-v1:0")

client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

SYSTEM_PROMPT = """
You are SpeakSmart, a communication coach for engineers.

Evaluate how clearly a user explains a technical concept.

Follow Amazon Nova prompting best practices:
be clear, specific, concise, and structured.

Your task:
score the explanation for clarity, structure, pacing, simplicity, and technical accuracy.
detect filler words like um, like, basically, kind of, you know.
return strict JSON only.

Return exactly this schema:
{
  "communication_scorecard": {
    "clarity": 0,
    "structure": 0,
    "pacing": 0,
    "simplicity": 0,
    "technical_accuracy": 0
  },
  "filler_words_detected": [],
  "confidence_score": 0.0,
  "strengths": "",
  "suggestions": "",
  "improved_explanation": "",
  "reasoning": ""
}
"""

USER_TEXT = """
Kubernetes is like um this system that basically runs containers across machines
and kind of schedules them and you know helps them talk to each other.
"""

messages = [
    {
        "role": "user",
        "content": [
            {
                "text": f"User explanation:\n{USER_TEXT}"
            }
        ]
    }
]

try:
    response = client.converse(
        modelId=NOVA_MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
        inferenceConfig={
            "maxTokens": 1200,
            "temperature": 0.15,
            "topP": 0.9
        }
    )

    raw_text = response["output"]["message"]["content"][0]["text"]
    print("MODEL_ID:", NOVA_MODEL_ID)
    print("RAW_RESPONSE:")
    print(raw_text)

    parsed = json.loads(raw_text)
    print("\nPARSED_JSON:")
    print(json.dumps(parsed, indent=2))

except ClientError as e:
    print("CLIENT_ERROR:", e)
except json.JSONDecodeError as e:
    print("JSON_PARSE_ERROR:", e)
