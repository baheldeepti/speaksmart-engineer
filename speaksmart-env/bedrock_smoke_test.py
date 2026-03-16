import os
import json
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
MODEL_ID = os.getenv("NOVA_MODEL_ID", "amazon.nova-lite-v1:0")

client = boto3.client("bedrock-runtime", region_name=REGION)

system_prompts = [
    {
        "text": (
            "You are a concise assistant. "
            "Reply in one short sentence."
        )
    }
]

messages = [
    {
        "role": "user",
        "content": [
            {
                "text": "Say hello and confirm you are working."
            }
        ]
    }
]

try:
    response = client.converse(
        modelId=MODEL_ID,
        system=system_prompts,
        messages=messages,
        inferenceConfig={
            "maxTokens": 120,
            "temperature": 0.2,
            "topP": 0.9
        }
    )

    text = response["output"]["message"]["content"][0]["text"]
    print("MODEL_ID:", MODEL_ID)
    print("RESPONSE:", text)

except ClientError as e:
    print("ERROR:", e)
