"""
SpeakSmart - AI Communication Coach
Amazon Nova Hackathon 2025
─────────────────────────────────────
Coach Maya: Your AI-powered presentation coach
Direct room connection — no dispatch needed
"""

from dotenv import load_dotenv
import os, logging, json, asyncio, re, random
import boto3
from livekit import rtc, api

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("speaksmart")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
ROOM_NAME = os.getenv("ROOM_NAME", "speaksmart")

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
polly = boto3.client("polly", region_name=AWS_REGION)

SCENARIOS = {
    "A": {"name": "Engineer → Engineers", "audience": "Technical team", "type": "technical"},
    "B": {"name": "Engineer → Executives", "audience": "Leadership", "type": "executive"},
    "C": {"name": "Data → Business", "audience": "Business team", "type": "business"},
    "D": {"name": "Tech → Client", "audience": "External client", "type": "client"},
    "E": {"name": "Roadmap Pitch", "audience": "Product managers", "type": "product"},
}

MAYA_GREETINGS = [
    "Hey there! I'm Maya, your communication coach. Pick your audience and let's make you unforgettable!",
    "Hi! Maya here, ready to coach. Choose who you're speaking to and show me what you've got!",
]

MAYA_START_LINES = {
    "technical": "Nice, speaking to fellow engineers. Show me the depth. Go!",
    "executive": "Executives care about impact and dollars. Lead with the so what. Go!",
    "business": "Business folks want clarity, not complexity. Make the data tell a story. Go!",
    "client": "Clients want to know what is in it for them. Lead with benefits. Go!",
    "product": "Product people want the roadmap to sing. Connect features to customer pain. Go!",
}

ANALYSIS_PROMPT = '''You are Coach Maya, a warm, direct, expert communication coach.
You are analyzing a speech given to: {audience}.

TRANSCRIPT: """{transcript}"""

Return ONLY valid JSON (no markdown fences, no preamble). Be specific, quote their actual words.
{{
  "overall_score": <1-10>,
  "maya_headline": "<A punchy one-line summary>",
  "opening_analysis": {{
    "score": <1-10>,
    "their_words": "<quote their actual first sentence>",
    "issue": "<specific problem>",
    "better_opening": "<rewritten version>"
  }},
  "structure_analysis": {{
    "score": <1-10>,
    "flow": "<how they organized their points>",
    "suggestion": "<better structure>"
  }},
  "clarity_analysis": {{
    "score": <1-10>,
    "jargon_found": ["<jargon terms they used>"],
    "simplification_tips": "<how to simplify for this audience>"
  }},
  "impact_analysis": {{
    "score": <1-10>,
    "their_topic": "<what they discussed>",
    "missing_impact": "<what value/outcome they did not mention>",
    "suggested_impact_statement": "<a sentence they should add>"
  }},
  "conclusion_analysis": {{
    "score": <1-10>,
    "how_they_ended": "<their ending>",
    "better_conclusion": "<stronger ending with clear CTA>"
  }},
  "confidence_analysis": {{
    "score": <1-10>,
    "hedging_words_found": ["<filler/hedge words>"],
    "confidence_tip": "<specific replacement>"
  }},
  "reframes": [
    {{"original": "<their exact quote>", "issue": "<problem>", "better_version": "<improved>", "why_better": "<reason>"}}
  ],
  "strengths": ["<specific strength with quoted example>"],
  "top_improvement": {{
    "area": "<one focus area>",
    "current": "<what they did>",
    "target": "<what to aim for>",
    "practice_tip": "<how to improve>"
  }},
  "voice_feedback": "<2-3 sentences Maya says aloud: praise one specific thing, then give 1 concrete actionable tip. Sound warm and direct.>",
  "articulation_score": <1-10>,
  "articulation_feedback": "<pacing, filler words, clarity notes>"
}}'''


def generate_agent_token():
    """Generate a token for the agent to join the room."""
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity("agent-maya")
    token.with_name("Coach Maya")
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=ROOM_NAME,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    ))
    return token.to_jwt()


async def send_data(room, data):
    try:
        payload = json.dumps(data).encode()
        await room.local_participant.publish_data(payload, reliable=True)
        logger.info(f"📤 Sent: {data.get('type', 'unknown')}")
    except Exception as e:
        logger.error(f"Send error: {e}")


async def speak(audio_source, text):
    if not text:
        return
    logger.info(f"🔊 Speaking: {text[:80]}...")
    try:
        resp = polly.synthesize_speech(
            Text=text, OutputFormat="pcm", VoiceId="Ruth",
            SampleRate="16000", Engine="neural",
        )
        pcm = resp["AudioStream"].read()
        chunk_size = 640
        for i in range(0, len(pcm), chunk_size):
            chunk = pcm[i : i + chunk_size]
            if len(chunk) < chunk_size:
                chunk = chunk.ljust(chunk_size, b"\x00")
            frame = rtc.AudioFrame(
                data=chunk, sample_rate=16000,
                num_channels=1, samples_per_channel=320,
            )
            await audio_source.capture_frame(frame)
            await asyncio.sleep(0.02)
    except Exception as e:
        logger.error(f"TTS error: {e}")


def analyze_speech(transcript, scenario):
    prompt = ANALYSIS_PROMPT.format(
        audience=scenario["audience"], transcript=transcript[:3000]
    )
    try:
        resp = bedrock.converse(
            modelId="amazon.nova-lite-v1:0",
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 1500, "temperature": 0.3},
        )
        text = resp["output"]["message"]["content"][0]["text"].strip()
        text = re.sub(r"^```json?\n?|```$", "", text, flags=re.MULTILINE).strip()
        result = json.loads(text)
        result["scenario_type"] = scenario["type"]
        result["audience"] = scenario["audience"]
        return result
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return {
            "overall_score": 5,
            "maya_headline": "I had trouble analyzing, but let us try again!",
            "strengths": ["You showed up and practiced, that is already ahead of most people."],
            "reframes": [],
            "voice_feedback": "Good effort! I had a small hiccup on my end. Want to give it another go?",
            "scenario_type": scenario["type"],
            "audience": scenario["audience"],
        }


async def main():
    logger.info("🚀 SpeakSmart Agent Starting (Direct Mode)")

    if not LIVEKIT_URL or not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        logger.error("❌ Missing LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET in .env")
        return

    # Generate token and connect directly
    agent_token = generate_agent_token()
    logger.info(f"🔑 Token generated for room: {ROOM_NAME}")

    room = rtc.Room()

    # Shared state
    state = {
        "scenario_key": None,
        "scenario_event": asyncio.Event(),
        "stop_event": asyncio.Event(),
    }

    # ── Event handlers ──
    @room.on("participant_connected")
    def on_participant_connected(participant):
        if participant.identity != "agent-maya":
            logger.info(f"👤 User joined: {participant.identity}")

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        if participant.identity != "agent-maya":
            logger.info(f"👋 User left: {participant.identity}")

    @room.on("data_received")
    def on_data(data_packet):
        try:
            raw = data_packet.data
            if not isinstance(raw, bytes):
                raw = bytes(raw)
            data = json.loads(raw.decode())
            msg_type = data.get("type")
            logger.info(f"📨 Received: {msg_type}")

            if msg_type == "scenario":
                state["scenario_key"] = data.get("scenario", "A")
                state["scenario_event"].set()
            elif msg_type == "stop":
                state["stop_event"].set()
        except Exception as e:
            logger.error(f"Data parse error: {e}")

    # ── Connect ──
    try:
        await room.connect(LIVEKIT_URL, agent_token)
        logger.info(f"✅ Connected to room: {room.name}")
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return

    # ── Audio output ──
    audio_source = rtc.AudioSource(sample_rate=16000, num_channels=1)
    audio_track = rtc.LocalAudioTrack.create_audio_track("coach-maya", audio_source)
    options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    await room.local_participant.publish_track(audio_track, options)
    logger.info("🔊 Audio track published")

    # Send ready
    await send_data(room, {"type": "agent_ready"})
    logger.info("📤 Agent ready!")

    # Greet
    greeting = random.choice(MAYA_GREETINGS)
    await speak(audio_source, greeting)
    await send_data(room, {"type": "agent_ready"})

    # ══════════════════════════════════════════
    # MAIN LOOP
    # ══════════════════════════════════════════
    try:
        while True:
            state["scenario_key"] = None
            state["scenario_event"] = asyncio.Event()
            state["stop_event"] = asyncio.Event()

            logger.info("⏳ Waiting for scenario...")
            await state["scenario_event"].wait()

            scenario = SCENARIOS.get(state["scenario_key"], SCENARIOS["A"])
            logger.info(f"📋 Selected: {scenario['name']}")

            start_line = MAYA_START_LINES.get(scenario["type"], "Go ahead, I am listening!")
            await speak(audio_source, start_line)

            # ── Transcribe ──
            logger.info("🎙️ Starting transcription")
            try:
                from amazon_transcribe.client import TranscribeStreamingClient
                from amazon_transcribe.handlers import TranscriptResultStreamHandler

                class Handler(TranscriptResultStreamHandler):
                    def __init__(self, stream, rm):
                        super().__init__(stream)
                        self.rm = rm
                        self.segments = []
                        self.pc = 0

                    async def handle_transcript_event(self, event):
                        for result in event.transcript.results:
                            for alt in result.alternatives:
                                text = alt.transcript.strip()
                                if not text:
                                    continue
                                if result.is_partial:
                                    self.pc += 1
                                    if self.pc % 3 == 0:
                                        asyncio.create_task(send_data(self.rm, {"type": "partial", "text": text}))
                                else:
                                    self.segments.append(text)
                                    logger.info(f"📝 Final: {text[:60]}...")
                                    asyncio.create_task(send_data(self.rm, {"type": "partial", "text": text}))

                    def get_transcript(self):
                        return " ".join(self.segments).strip()

                tclient = TranscribeStreamingClient(region=AWS_REGION)
                tstream = await tclient.start_stream_transcription(
                    language_code="en-US",
                    media_sample_rate_hz=48000,
                    media_encoding="pcm",
                )
                handler = Handler(tstream.output_stream, room)
                handler_task = asyncio.create_task(handler.handle_events())
            except Exception as e:
                logger.error(f"Transcribe error: {e}")
                await send_data(room, {"type": "error", "message": f"Transcription failed: {e}"})
                await send_data(room, {"type": "agent_ready"})
                continue

            # ── Pipe audio ──
            frames_sent = 0

            async def pipe_audio():
                nonlocal frames_sent
                user_track = None
                for _ in range(60):
                    if state["stop_event"].is_set():
                        return
                    for p in room.remote_participants.values():
                        for pub in p.track_publications.values():
                            if pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                                user_track = pub.track
                                break
                        if user_track:
                            break
                    if user_track:
                        break
                    await asyncio.sleep(0.25)

                if not user_track:
                    logger.error("❌ No user audio track")
                    return

                logger.info("🎤 Piping audio to Transcribe")
                astream = rtc.AudioStream(user_track)
                try:
                    async for ev in astream:
                        if state["stop_event"].is_set():
                            break
                        frames_sent += 1
                        try:
                            await tstream.input_stream.send_audio_event(audio_chunk=bytes(ev.frame.data))
                        except Exception as e:
                            if "closed" in str(e).lower():
                                break
                            logger.error(f"Send error: {e}")
                except Exception as e:
                    logger.warning(f"Stream ended: {e}")

            pipe_task = asyncio.create_task(pipe_audio())

            logger.info("🎧 Recording...")
            await state["stop_event"].wait()
            logger.info(f"🛑 Stop. Frames: {frames_sent}")

            # Cleanup
            await asyncio.sleep(1.0)
            try:
                await tstream.input_stream.end_stream()
            except Exception:
                pass

            try:
                await asyncio.wait_for(handler_task, timeout=5.0)
            except Exception:
                handler_task.cancel()

            pipe_task.cancel()
            try:
                await pipe_task
            except asyncio.CancelledError:
                pass

            transcript = handler.get_transcript()
            logger.info(f"📝 Transcript ({len(transcript)} chars): {transcript[:100]}...")
            await send_data(room, {"type": "transcript", "text": transcript})

            if not transcript or len(transcript) < 5:
                await send_data(room, {"type": "error", "message": "No speech detected. Check your mic."})
                await speak(audio_source, "I did not catch that. Check your mic and try again!")
                await send_data(room, {"type": "agent_ready"})
                continue

            # ── Analyze ──
            await send_data(room, {"type": "analyzing"})
            await speak(audio_source, "Okay, give me a moment to break that down...")

            logger.info("🧠 Analyzing...")
            analysis = await asyncio.get_event_loop().run_in_executor(
                None, analyze_speech, transcript, scenario
            )

            await send_data(room, {
                "type": "results",
                "transcript": transcript,
                "analysis": analysis,
                "scenario": scenario,
            })

            voice = analysis.get("voice_feedback", "Nice work!")
            await speak(audio_source, voice)

            await asyncio.sleep(1)
            await send_data(room, {"type": "agent_ready"})
            await speak(audio_source, "Ready for another round when you are!")

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await room.disconnect()
        logger.info("👋 Disconnected")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bye!")