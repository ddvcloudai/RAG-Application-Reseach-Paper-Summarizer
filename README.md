# RAG Based Reseach Paper Summarizer
This is RAG based application to summarize research paper using Langchain framework. Presenting a secured and well governed prototype application for demo purpose suggesting how RAG framework handles the vectors and embeddings in dev environment leveraging OpenAI LLM capabilities through summary response.

## Objective:
To summarize how RAG works from development and architecture standpoint.

## Workflow Process: 
The user uploads the research document -> backend augments the text using embeddings -> The vectors are scored -> Sementic search happens utilizing LLM -> Result is sent back. 

## Augmentation:
Guardrails: added as an essential security measure for prompt and retreival perspective.
Governance: every ingenstion, query, rejections and token usage taken into account in log file.
Any other augmentation can be added accordingly.

## Note:
Not considering environment variable as it geneally contain the keys, so avoiding this channel. If you want, feel free to add env file under the project structure so that you can call your LLM like OpenAI. 
This is a simple prototype, so you can customize it according to your requiremnts.

## Assistance:
Some inputs from large language model (claude sonnet usage stood helpful in giving it production grade developer centric approach.

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your OpenAI key in .env
```
OPENAI_API_KEY=sk-...
```

### 3. Start the backend (Terminal 1)
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Start the frontend (Terminal 2)
```bash
cd frontend
streamlit run app.py
```

App runs at: http://localhost:8501
API docs at: http://localhost:8000/docs
