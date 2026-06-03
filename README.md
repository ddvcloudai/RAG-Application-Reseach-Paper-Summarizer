# RAG-Application: Reseach Paper Summarizer
This is RAG based application to summarize research paper using Langchain framework. Presenting a secured and well governed prototype application for demo purpose suggesting how RAG framework handles the vectors and embeddings in dev environment leveraging OpenAI LLM capabilities through summary response.

## Objective:
To summarize how RAG works from development and architecture standpoint.

## Workflow Process: 
The user uploads the research document -> backend augments the text using embeddings -> The vectors are scored -> Sementic search happens utilizing LLM -> Result is sent back. 

## Agmentation:
Guardrails: added as an essential security measure for prompt and retreival perspective.
Governance: every ingenstion, query, rejections and token usage taken into account in log file.
Any other augmentation can be added accordingly.

##Assistance:
Some inputs from large language model (claude sonnet usage stood helpful in giving it production grade developer centric approach

