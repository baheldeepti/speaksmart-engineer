from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3, os, logging, json, uuid, time, re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gopa")

app = FastAPI(title="GOPA API", version="1.0.0")

cors_origins = os.getenv("CORS_ORIGINS","https://dev.d2chs9h4rp6fta.amplifyapp.com").split(",")
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

bedrock_mgmt = boto3.client("bedrock", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
s3 = boto3.client("s3", region_name=os.getenv("S3_REGION", "us-east-1"))
S3_BUCKET = os.getenv("S3_BUCKET", "gopa-media")

class StoryRequest(BaseModel):
    prompt: str
    value: str = ""
    child_name: str = "Friend"
    child_photo_key: str = None

class ImageRequest(BaseModel):
    image_prompt: str

class VideoRequest(BaseModel):
    image_prompt: str
    story: str = ""

class VoiceRequest(BaseModel):
    story: str

class TokenRequest(BaseModel):
    room: str
    participant: str

STORY_TEMPLATE = """You are a master storyteller of ancient Indian tales for young children (ages 4-8).

Create an authentic story about Bal Krishna (age 4) based on this theme: {prompt}
The virtue to teach: {value}
Child's name: {child_name}

KRISHNA CHARACTER (always consistent):
- Little Lord Krishna, approximately 4 years old
- Curly dark hair with a small peacock feather
- Big sparkling eyes, innocent divine smile
- Bright yellow dhoti, peachy-orange shawl with mandala patterns
- Setting: Ancient Vrindavan/Gokul with lush forests, Yamuna river, cows

STORY RULES:
- Based on real themes from Krishna childhood (butter stealing, calf herding, river play, forest adventures, helping villagers)
- 4 scenes, each building on the last
- Simple language a 4-year-old can understand
- Each scene is 2-3 sentences
- End with a gentle moral lesson

OUTPUT FORMAT (follow exactly):
TITLE: [story title]

SCENE 1:
NARRATION: [2-3 sentences]
IMAGE: [visual description for Pixar 3D illustration, golden lighting, ancient Vrindavan]

SCENE 2:
NARRATION: [2-3 sentences]
IMAGE: [visual description]

SCENE 3:
NARRATION: [2-3 sentences]
IMAGE: [visual description]

SCENE 4:
NARRATION: [2-3 sentences, include the moral lesson]
IMAGE: [visual description]"""


def parse_story(text: str, value: str) -> dict:
    scenes = []
    title = "A Krishna Adventure"
    title_match = re.search(r'TITLE:\s*(.+)', text)
    if title_match:
        title = title_match.group(1).strip()
    scene_blocks = re.split(r'SCENE \d+:', text)
    for block in scene_blocks[1:]:
        n = re.search(r'NARRATION:\s*(.+?)(?=IMAGE:|SCENE \d+:|$)', block, re.DOTALL)
        i = re.search(r'IMAGE:\s*(.+?)(?=SCENE \d+:|$)', block, re.DOTALL)
        narration = n.group(1).strip() if n else ""
        image_prompt = i.group(1).strip() if i else ""
        if narration:
            scenes.append({"narration": narration, "image_prompt": image_prompt, "image_url": None})
    if not scenes:
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        for idx, para in enumerate(paragraphs[:4]):
            scenes.append({"narration": para, "image_prompt": f"Little Lord Krishna in Vrindavan, {value}, Pixar 3D, golden light, scene {idx+1}", "image_url": None})
    return {"title": title, "scenes": scenes}


def make_image(prompt: str) -> str:
    try:
        full = (f"{prompt}. Little Lord Krishna age 4, curly dark hair with peacock feather, yellow dhoti, "
                "Pixar 3D animation, vibrant colors, warm golden lighting, ancient Vrindavan, children storybook.")[:900]
        body = json.dumps({
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {"text": full},
            "imageGenerationConfig": {"numberOfImages": 1, "height": 512, "width": 512, "cfgScale": 8.0},
        })
        resp = bedrock.invoke_model(modelId=os.getenv("NOVA_CANVAS_MODEL_ID", "amazon.nova-canvas-v1:0"), body=body)
        result = json.loads(resp["body"].read())
        return result["images"][0]
    except Exception as e:
        logger.error(f"Image error: {e}")
        return None


@app.get("/")
async def root():
    return {"message": "GOPA API Active"}


@app.post("/api/story/generate")
async def generate_story(request: StoryRequest):
    try:
        logger.info(f"🎨 Story: {request.prompt}")
        if not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt required")

        prompt = STORY_TEMPLATE.format(
            prompt=request.prompt,
            value=request.value or "kindness",
            child_name=request.child_name or "Friend",
        )

        logger.info("📖 Generating script...")
        resp = bedrock.converse(
            modelId=os.getenv("NOVA_LITE_MODEL_ID", "us.amazon.nova-lite-v1:0"),
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 2000, "temperature": 0.8},
        )
        raw = resp["output"]["message"]["content"][0]["text"].strip()
        logger.info(f"Script preview: {raw[:200]}")

        data = parse_story(raw, request.value)
        logger.info(f"✅ {len(data['scenes'])} scenes parsed")

        for i, scene in enumerate(data["scenes"]):
            logger.info(f"🖼️ Image {i+1}/{len(data['scenes'])}...")
            b64 = make_image(scene["image_prompt"])
            scene["image_url"] = f"data:image/png;base64,{b64}" if b64 else None

        return {
            "status": "success",
            "title": data["title"],
            "scenes": data["scenes"],
            "theme": request.prompt,
            "value": request.value,
        }
    except Exception as e:
        logger.error(f"❌ {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/image/generate")
async def generate_image(request: ImageRequest):
    try:
        b64 = make_image(request.image_prompt)
        if not b64:
            raise HTTPException(status_code=500, detail="Image generation failed")
        return {"status": "success", "image": b64, "format": "png"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/video/generate")
async def generate_video(request: VideoRequest):
    try:
        video_prompt = (f"{request.image_prompt}. Little Lord Krishna age 4 in ancient Vrindavan, "
                        "Pixar 3D animation, warm golden lighting, children storybook, magical.")[:512]
        output_key = f"videos/{uuid.uuid4().hex}"
        s3_uri = f"s3://{S3_BUCKET}/{output_key}"
        model_input = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {"text": video_prompt},
            "videoGenerationConfig": {"durationSeconds": 6, "fps": 24, "dimension": "1280x720", "seed": int(time.time()) % 2147483647},
        }
        resp = bedrock_mgmt.start_async_invoke(
            modelId=os.getenv("NOVA_REEL_MODEL_ID", "amazon.nova-reel-v1:0"),
            modelInput=model_input,
            outputDataConfig={"s3OutputDataConfig": {"s3Uri": s3_uri}},
        )
        return {"status": "success", "message": "Video generation started (2-4 min)", "invocation_arn": resp.get("invocationArn",""), "s3_output": s3_uri}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice/generate")
async def generate_voice(request: VoiceRequest):
    try:
        prompt = f"Transform into 250-word narration for children (4-8):\n\n{request.story}\n\nSimple language, mark pauses [PAUSE], teach moral, end with encouragement."
        resp = bedrock.converse(
            modelId=os.getenv("NOVA_LITE_MODEL_ID", "us.amazon.nova-lite-v1:0"),
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 600, "temperature": 0.6},
        )
        return {"status": "success", "narration": resp["output"]["message"]["content"][0]["text"].strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/token")
async def get_token(request: TokenRequest):
    try:
        from livekit import api
        token = api.TokenWithGrants(
            api_key=os.getenv("LIVEKIT_API_KEY"), api_secret=os.getenv("LIVEKIT_API_SECRET"),
            grant=api.VideoGrant(room_join=True, room=request.room), identity=request.participant, ttl=259200,
        )
        return {"status": "success", "token": token.to_jwt(), "url": os.getenv("LIVEKIT_URL"), "room": request.room}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gopa-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
