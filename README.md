# ChatDKG - Natural Language question answering on the OriginTrail Decentralized Knowledge Graph

This example shows a basic extractive question answering application built with OriginTrail Knowledge Assets and Langchain. 
It walks you through the process of creating a single Knowledge Asset on the OriginTrail Decentralized Knowledge Graph and necessary indexing operations to enable extractive question answering (EQA) using natural language based semantic search (such as in the form of asking a question) over the Knowledge Asset content using Langchain and Milvus Vector DB.

In contrast to generative QA systems such as ChatGPT, an extractive system doesn't "hallucinate", rather only extracts content from within the verifiable Knowledge Asset. 
Additionally, to extend the extractive approach, we also demonstrate an "extract & summarize" approach that takes the extracted content from the Knowledge Asset and submits it to an LLM (in this case OpenAI) to summarize.

Additionally, this code can turn a question into a SPARQL query and run it on the DKG. This code has been adapted to function as a FastAPI backend, serving requests from a front end, such as a chatbot web app.

The repository also includes a Twitter Bot implementation in the `twitterBot` folder. This bot can forward tweets from users who tag it to the `app.py` application, enabling integration with Twitter conversations.

## Pre-requisites

- NodeJS v16 or higher.
- Python 3.10 or higher.
- Access to an OriginTrail DKG node. You can setup your own by following instructions [here](https://docs.origintrail.io/decentralized-knowledge-graph-layer-2/testnet-node-setup-instructions/setup-instructions-dockerless)
- An account on [Milvus](https://cloud.zilliz.com/orgs).
- Optionally: OpenAI API key

## Installation

Clone the repository:

```bash
git clone https://github.com/DarrenZal/ChatDKG.git
cd ChatDKG
```

## NodeJS Dependencies

First install the NodeJS dependencies:

```bash
npm install
```

## Python Dependencies

create a python virtual environement (optional)
```bash
python -m venv venv
source venv/bin/activate
```

Then, install Python dependencies:

```bash
pip install python-dotenv openai langchain pandas sentence-transformers pymilvus dkg
```
## Environment Variables

You'll need to setup your environment variables. Copy the .env.example to a new .env file:

```bash
cp .env.example .env
```

Open the .env file and replace the placeholders with your actual values. The file should look like this:

```makefile
OT_NODE_HOSTNAME=<Your OT Node Hostname>
WALLET_PUBLIC_KEY=<Your Wallet Public Key>
WALLET_PRIVATE_KEY=<Your Wallet Private Key>
MILVUS_URI=<Your Milvus URI>
MILVUS_USER=<Your Milvus User>
MILVUS_PASSWORD=<Your Milvus Password>
OPENAI_KEY=<Your OpenAI API Key>
RPC_ENDPOINT=<Your Blockchain RPC URL>
```

# Usage

## Create a Knowledge Asset

Start by running the dkg-demo.js script:

```bash
node dkg-demo.js
```

The console will print a Uniform Asset Locator (UAL), copy that for the next step.
## Generate TSV

Next, run the generate-tsv.js script with the UAL as an argument:

```bash
node ../utils/generate-tsv.js <UAL>
```

This will generate a file named output.tsv.

## Upload Embeddings

Make sure your Milvus account details are set up in the .env file. Then run the upload-embeddings.py script:

```bash
python upload-embeddings.py
```

This script reads the TSV file, generates embeddings and uploads them to your Milvus account.

## Search in the Knowledge Graph

Now you can run the search.py script:

```bash
python search.py
```

This will generate responses based on the uploaded knowledge graph.

## Troubleshooting

If you encounter any issues, please check that you've correctly set all environment variables in the .env file and that you have the right versions of NodeJS and Python. If you continue to experience problems, please open an issue in the GitHub repository.

## If deploying as a backend server with a separate front end:

### 1. **Setting Up FastAPI:**
#### a. Installation:

Install FastAPI and an ASGI server, such as Uvicorn, which will serve your application.

```bash
pip install fastapi[all] 
pip install uvicorn
```

#### b. Basic FastAPI Setup:

Create a new FastAPI application. Here's a simple example to get you started:

```bash
# app.py
server {
    listen 80;
    
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

make sure port 8000 is open
```bash
sudo ufw allow 8000
```

### 2. **Run Your FastAPI Application:**

Use Uvicorn to run your application:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

This command will start your FastAPI application on port 8000.

### 4. **Using Nginx as a Reverse Proxy (Optional but Recommended):**

Setting up Nginx in front of FastAPI can improve performance and security:

- Install Nginx on your server.
- Configure Nginx to act as a reverse proxy to pass requests to FastAPI. Here's a basic configuration snippet:

```bash
server {
    listen 80;
    
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- Replace `yourdomain.com` with your actual domain name.
- Ensure that Nginx is configured to start automatically.

## Front End Example

For an example of how to implement a front end for this application, check out the code at https://github.com/DarrenZal/Myseelia. This repository contains a complete implementation of a chat interface that works with the ChatDKG backend.

## Twitter Bot Integration

The `twitterBot` folder contains code for a Twitter bot that can forward tweets to your ChatDKG application. When users tag the bot in their tweets, it will automatically forward the content to the `app.py` application for processing. This enables integration with Twitter conversations and allows users to interact with your knowledge graph directly through Twitter.
