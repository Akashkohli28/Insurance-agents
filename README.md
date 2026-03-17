# Insurance-agents
An AI-powered multi-agent system that automates insurance policy renewal outreach. Based on how close a policy is to expiring, the system automatically selects the right communication channel — email, WhatsApp, voice call, or human agent escalation — generates a personalised message using an LLM (Google Gemini), sends it through the appropriate service, and then runs a compliance check on the message before finalising.
The system also includes a RAG-powered chatbot that lets customers ask questions about their insurance policies.

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
