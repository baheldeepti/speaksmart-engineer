# 🎤 SpeakSmart — AI Communication Coach

> **Amazon Nova Hackathon 2025** | Voice AI Category  
> Built by Ayushi & Deepti

## 🚀 What is SpeakSmart?

SpeakSmart is a **multi-agent Voice AI platform** that helps technical professionals communicate complex ideas clearly to business stakeholders. It solves a critical enterprise problem: **56% of project failures stem from miscommunication**.

### The Problem
Engineers struggle to explain technical concepts to non-technical audiences. They use jargon, lack business framing, and miss the "so what" that executives care about.

### Our Solution
An AI coach powered by **Amazon Nova** that provides:
- **Real-time voice coaching** with natural conversation
- **7-dimension analysis** of communication effectiveness
- **Jargon detection** with plain-language alternatives
- **Actionable feedback** with example rewrites

---

## 🧠 Amazon Nova Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🎙️ COACH MAYA (Nova Sonic)                                    │
│     Real-time bidirectional voice AI                            │
│     Natural coaching conversation                                │
│                                                                 │
│  🧠 EVALUATOR (Nova Lite)                                       │
│     7-dimension speech analysis                                  │
│     Structured JSON scoring                                      │
│                                                                 │
│  📊 FEEDBACK SYNTHESIZER (Nova Lite)                            │
│     Actionable insights generation                               │
│     Personalized improvement plans                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Nova Models Used
| Model | Purpose |
|-------|---------|
| **Nova Lite** | Real-time 7-dimension speech evaluation |
| **Nova Sonic** | Voice synthesis & conversation |
| **AWS Bedrock** | Model orchestration & inference |

---

## 📊 The 7 Dimensions We Evaluate

| # | Dimension | What We Measure |
|---|-----------|-----------------|
| 1 | **Jargon Clarity** | Did you avoid/explain technical terms? |
| 2 | **Business Impact** | Did you connect to revenue, cost, risk? |
| 3 | **Analogy & Story** | Did you use relatable examples? |
| 4 | **Structure** | Context → Explanation → So What? |
| 5 | **The "So What"** | Clear business implication at the end? |
| 6 | **Opening Hook** | Did you grab attention immediately? |
| 7 | **Confidence** | Conviction vs hedging language? |

---

## 💼 Enterprise Impact

### Who Benefits?
- **Engineers** presenting to executives
- **Data scientists** explaining ML models to product teams
- **Technical leads** pitching architecture decisions
- **Anyone** who needs to translate "tech speak" to "business speak"

### Business Value
- 📉 Reduces miscommunication-related project failures
- ⏱️ Saves meeting time with clearer presentations
- 💰 Better stakeholder alignment = faster approvals
- 📈 Career growth for technical professionals

---

## 🛠️ Tech Stack

```
Frontend:    React + LiveKit Client
Backend:     Python + LiveKit Agents
Voice:       Amazon Nova Sonic (via Polly bridge)
Analysis:    Amazon Nova Lite
Streaming:   AWS Transcribe + LiveKit
Infra:       AWS Bedrock
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- AWS credentials with Bedrock access
- LiveKit Cloud account

### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py dev
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Environment Variables
```env
AWS_REGION=us-east-1
NOVA_LITE_MODEL=amazon.nova-lite-v1:0
POLLY_VOICE=Ruth
REACT_APP_LIVEKIT_URL=wss://your-project.livekit.cloud
REACT_APP_LIVEKIT_TOKEN=your-token
```

---

## 📸 Screenshots

### Scenario Selection
Choose from 4 technical communication scenarios:
- Architecture explanation to teammates
- Technical deep dive for stakeholders
- Conference presentation
- Post-mortem / tech decision pitch

### Real-Time Recording
- Live transcription as you speak
- Visual waveform feedback
- Instant stop & evaluate

### 7-Dimension Score Dashboard
- Overall score (1-10)
- Individual dimension breakdown
- Jargon detection with alternatives
- Filler word count
- Strengths & improvements
- Coach's personalized note

---

## 🎯 Why We Built This

As engineers ourselves, we've experienced the pain of:
- "Can you explain that in English?"
- "But what does this mean for the business?"
- "You lost me at microservices..."

SpeakSmart is the coach we wish we had. It's like having a communication mentor available 24/7, powered by Amazon Nova's intelligence.

---

## 🏆 Hackathon Submission

**Category:** Voice AI  
**Event:** [Amazon Nova Hackathon 2025](https://amazon-nova.devpost.com/)  
**Team:** Ayushi & Deepti

### How We Used Amazon Nova

1. **Nova Lite** - Powers our intelligent 7-dimension speech analysis. It evaluates jargon, business framing, structure, and more with remarkable accuracy.

2. **Nova Sonic** - Enables natural voice interaction with Coach Maya. The bidirectional streaming allows for real-time coaching conversation.

3. **AWS Bedrock** - Orchestrates our multi-agent system, handling model inference at scale.

---

## 📄 License

MIT License - Built for Amazon Nova Hackathon 2025
