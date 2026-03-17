# Insurance-agents
An AI-powered multi-agent system that automates insurance policy renewal outreach. Based on how close a policy is to expiring, the system automatically selects the right communication channel — email, WhatsApp, voice call, or human agent escalation — generates a personalised message using an LLM (Google Gemini), sends it through the appropriate service, and then runs a compliance check on the message before finalising.
The system also includes a RAG-powered chatbot that lets customers ask questions about their insurance policies.

Tech Stack

LangGraph — Stateful multi-agent workflow orchestration
LangChain + Google Gemini 2.0 Flash — LLM for message generation and compliance checking
FastAPI + Uvicorn — REST API server and frontend serving
SQLite + aiosqlite — Async database for policyholder records
ChromaDB — Vector store for the RAG chatbot
Twilio — WhatsApp messaging and voice calls
SMTP (Gmail) — Email delivery
Tenacity — Retry logic with exponential backoff
Docker + Docker Compose — Containerised deployment


Project Structure
insurance-agents/
├── main.py                  # LangGraph workflow definition
├── api.py                   # FastAPI server and REST endpoints
├── db.py                    # Async SQLite database layer
├── ingest.py                # Knowledge base ingestion (run once)
├── logging_config.py        # Logging setup
├── agents/
│   ├── state.py             # Shared AgentState TypedDict
│   ├── data_retrieval.py    # Fetches policyholder data
│   ├── strategy.py          # Decides communication channel
│   ├── email.py             # Drafts and sends renewal emails
│   ├── whatsapp.py          # Drafts and sends WhatsApp messages
│   ├── voice.py             # Generates script and makes voice calls
│   ├── guardrail.py         # LLM-based compliance checker
│   ├── hitl.py              # Human-in-the-loop escalation
│   └── utils.py             # Shared helpers (LLM, send functions, retry)
├── prompts/
│   ├── email_agent.txt
│   ├── whatsapp_agent.txt
│   ├── voice_agent.txt
│   ├── guardrail_agent.txt
│   └── chatbot_rag.txt
├── knowledge_base/
│   ├── faqs.md
│   ├── policy.md
│   └── policies.pdf
├── static/
│   └── index.html           # Frontend dashboard
├── test_email_agent.py
├── test_voice_agent.py
├── test_whatsapp_agent.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt

How It Works
Agent Pipeline (LangGraph Workflow)
The core of the system is a directed state graph built with LangGraph. Each step is an async node, and the graph manages routing between them based on shared state.
START
  └─► data_retrieval  →  strategy
                              ├─► email     →  guardrail  →  END (approved)
                              │                          └─► hitl → END
                              ├─► whatsapp  →  guardrail  →  END (approved)
                              │                          └─► hitl → END
                              ├─► voice     →  END
                              └─► hitl      →  END
Routing Logic (strategy.py)
The strategy agent decides which channel to use based on days_remaining before policy expiry:
Days RemainingChannel≥ 30 daysEmail15 – 29 daysWhatsApp3 – 14 daysVoice call< 3 daysHuman agent (HITL)
Guardrail Check
After email and WhatsApp messages are generated, the guardrail agent sends the message to Gemini for compliance review. The LLM checks against four rules:

Professional and empathetic tone
No hallucinated policy IDs or dates
No specific financial promises or discounts
No exposure of sensitive PII

If the message passes, it is marked APPROVED and the workflow ends. If it fails, the case is escalated to the HITL node for human review.

File-by-File Breakdown
main.py — Workflow Orchestrator
Builds and compiles the LangGraph StateGraph. Registers all agent nodes, defines edges and conditional routing, and exposes run_automation(ph_id) as the async entry point. The guardrail_router function reads state["guardrail_status"] to decide whether to end or escalate.
agents/state.py — Shared State
Defines AgentState, a TypedDict that is passed between every node in the graph. Fields include policyholder_id, policyholder_data, next_node, communication_channel, status, and guardrail_status.
agents/data_retrieval.py — Data Retrieval Node
Reads policyholder_id from state, fetches the full record from SQLite via db.get_policyholder(), and returns it into state. Sets status = "FAILED" if the record is not found.
agents/strategy.py — Strategy Node
Reads days_remaining from the policyholder data and applies the channel routing rules. Sets next_node and communication_channel in state, which LangGraph uses to pick the next node.
agents/email.py — Email Agent
Loads the email_agent.txt prompt, fills in the customer's name, policy ID, and renewal date, and calls Gemini to generate a professional renewal email. Sends it via SMTP using utils.send_email(), then updates the database with renewal_status = "EMAIL_SENT".
agents/whatsapp.py — WhatsApp Agent
Same flow as the email agent. Uses the whatsapp_agent.txt prompt (shorter, emoji-friendly) and sends via Twilio's messaging API. Updates status to "WHATSAPP_SENT".
agents/voice.py — Voice Agent
Uses voice_agent.txt to generate a voice call transcript/script with Gemini, then triggers a real outbound phone call via Twilio's Programmable Voice API. Updates status to "VOICE_CALL_MADE".
agents/guardrail.py — Guardrail Agent
Runs after email and WhatsApp. Sends the last generated message to Gemini with the guardrail_agent.txt prompt. Sets guardrail_status = "APPROVED" if Gemini responds with GUARDRAIL_PASSED, or stores the failure reason if rejected.
agents/hitl.py — Human-in-the-Loop Node
Handles two scenarios: policies expiring in fewer than 3 days (too urgent for automation) and messages rejected by the guardrail. Logs a warning, updates the database to "ESCALATED", and returns a handover message. In production, this would trigger a CRM ticket or Slack alert.
agents/utils.py — Shared Utilities
Contains the shared LLM instance (ChatGoogleGenerativeAI with Gemini 2.0 Flash) and three send functions, each decorated with @retry from the tenacity library (up to 3 attempts with exponential backoff):

send_email(to, subject, body) — Sends via SMTP over SSL
send_whatsapp(to_number, body) — Sends via Twilio's WhatsApp API
send_voice_call(to_number) — Initiates a call via Twilio Programmable Voice

Also includes get_prompt(filename) which reads prompt templates from the /prompts directory.
db.py — Database Layer
Async SQLite operations using aiosqlite:

init_db() — Creates the policyholders table and seeds 4 test records (one per channel)
get_policyholder(ph_id) — Fetches a single record by ID
update_policyholder(ph_id, updates) — Updates allowed fields (renewal_status, history, etc.)
list_policyholders_async() — Returns all records for the dashboard

api.py — FastAPI Server
The REST interface for the system. Key endpoints:
MethodEndpointDescriptionGET/Serves the frontend dashboardGET/policyholdersLists all policyholdersGET/dashboard/statsReturns status counts for the dashboardPOST/renew/{id}Triggers the full agent pipeline for a policyholderGET/policyholder/{id}Returns a single policyholder's current statusPOST/chatRAG chatbot — answers questions using the knowledge base
On startup, it initialises the SQLite database and loads the ChromaDB vector store for the chatbot.
ingest.py — Knowledge Base Ingestion
A one-time setup script that loads all .md and .pdf files from the knowledge_base/ folder, splits them into 1000-character chunks with 100-character overlap using RecursiveCharacterTextSplitter, embeds them using Google's gemini-embedding-001 model, and stores the vectors in a local ChromaDB database. Must be run before starting the server for the chatbot to work.
logging_config.py — Logging
Sets up timestamped stdout logging for all modules via setup_logging(). Each file gets its own named logger via get_logger(__name__). Third-party library noise from uvicorn is suppressed.
prompts/ — LLM Prompt Templates
Plain text files loaded at runtime and formatted with customer data using Python's .format(). Each agent has its own prompt:

email_agent.txt — Professional renewal email
whatsapp_agent.txt — Concise, friendly WhatsApp message with emoji
voice_agent.txt — Simulated voice call transcript focused on renewal confirmation
guardrail_agent.txt — Compliance review rules and pass/fail response format
chatbot_rag.txt — RAG system prompt that injects retrieved document context

knowledge_base/ — RAG Source Documents
Documents used to power the policy chatbot. Includes faqs.md (claims, coverage, payment questions), policy.md (policy details), and policies.pdf (full policy document). These are processed by ingest.py.
static/index.html — Frontend Dashboard
A single-page HTML UI served by FastAPI. Allows users to view all policyholders, trigger renewal automation, check statuses, and chat with the policy assistant.
Dockerfile + docker-compose.yml — Deployment
Builds a Python image, installs dependencies, and runs the FastAPI server via uvicorn. The compose file sets up port mapping and injects environment variables for all external service credentials.
test_*.py — Agent Tests
Three standalone test scripts for running individual agents in isolation without the full LangGraph pipeline, useful for quickly verifying that a specific channel is working.

Setup and Running
1. Environment Variables
Create a .env file in the project root:
envGEMINI_API_KEY=your_gemini_api_key

# Email (Gmail SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
SENDER_EMAIL=your_email@gmail.com

# Twilio (WhatsApp + Voice)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
TWILIO_VOICE_URL=https://your-twiml-url.com
2. Install Dependencies
bashpip install -r requirements.txt
3. Ingest the Knowledge Base (run once)
bashpython ingest.py
4. Start the Server
bashpython api.py
Or with Docker:
bashdocker-compose up --build
The server runs on http://localhost:8001.

API Usage
Trigger the renewal pipeline for a specific policyholder:
bashcurl -X POST http://localhost:8001/renew/PH_EMAIL
Ask the chatbot a question:
bashcurl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What happens if I miss a payment?"}'

Seed Data
The database is pre-seeded with 4 test policyholders to demonstrate each channel:
IDNameDays RemainingChannelPH_EMAILJohn 30-Day30EmailPH_WHATSAPPBob 15-Day15WhatsAppPH_VOICEJane 7-Day7VoicePH_HITLAlice 2-Day2Human agent

Key Design Patterns
LangGraph state machine — Each agent is a node in a directed graph. State is shared between nodes as a typed dictionary, making the pipeline easy to extend. Adding a new channel is as simple as adding a node and an edge.
RAG chatbot — The policy assistant retrieves relevant document chunks from ChromaDB before generating a response, preventing hallucination and grounding answers in actual policy documents.
Retry with exponential backoff — All external calls (email, WhatsApp, voice) automatically retry up to 3 times using the tenacity library, making the system resilient to transient network failures.
LLM guardrail as a safety layer — AI-generated messages pass through a second Gemini call that acts as a compliance reviewer. Only approved messages are considered final; rejected ones escalate to a human.
Fully async — Every node is async def and the database uses aiosqlite, ensuring the FastAPI server is never blocked during LLM calls or database operations.
