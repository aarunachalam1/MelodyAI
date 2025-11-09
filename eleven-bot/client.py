import os
import asyncio
from dotenv import load_dotenv
from google import genai
from fastmcp import Client

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=gemini_api_key)
mcp_client = Client("server.py") 

conversation = [
    {"role": "system", "content": "You are Melody, a helpful and friendly data science expert that can analyze datasets using MCP tools. You have access to a tool list datasets that allows you to view what datasets are loaded at any time, please use this before stating that there are no datasets loaded to confirm. The server persists datasets and models between sessions so make sure you run list datasets and list models before speaking with the user so you can check what they had in their previous session. DO NOT UNDER ANY CIRCUMSTANCE MAKE UP VALUES NOT OBTAINED THROUGH CALLING MCP TOOLS. Make your analyses and summarizations concise and informative. Don't state the file path of any plots you generate they will be displayed automatically. Format all model evaluations into bullet points and do NOT use markdown formatting."}
]

current_dataset = None

async def init_mcp():
    global mcp_client
    if not mcp_client.is_connected:
        await mcp_client.__aenter__()


async def process_message(user_input: str):
    global current_dataset

    # Strip quotes
    user_input = user_input.strip('"')

    # If user uploads a CSV
    if user_input.lower().endswith(".csv") and os.path.exists(user_input):
        current_dataset = user_input

        async with mcp_client:  # <--- important: enter context
            result = await mcp_client.call_tool("load_csv", {"file_path": current_dataset})

        if hasattr(result, "structured_content") and result.structured_content:
            result_data = result.structured_content
        elif hasattr(result, "data") and result.data:
            result_data = result.data
        else:
            result_data = getattr(result, "text", str(result))

        assistant_reply = (
            f"✅ Server loaded dataset successfully!\n"
            f"Columns: {result_data.get('columns', [])}\n"
            f"Rows: {result_data.get('num_rows', 'unknown')}\n"
        )

        # Update conversation
        conversation.append({
            "role": "user",
            "content": f"I've uploaded a new dataset located at {current_dataset}."
        })
        conversation.append({
            "role": "model",
            "content": f"Got it! The dataset path is now {current_dataset}."
        })

        return assistant_reply

    # Otherwise, normal prompt
    if current_dataset:
        full_prompt = (
            f"{user_input}\n"
            f"The dataset '{current_dataset}' has been loaded and is ready for analysis."
        )
    else:
        full_prompt = (
            f"{user_input}\n"
            "No dataset loaded yet. Please upload a CSV file first."
        )

    conversation.append({"role": "user", "content": full_prompt})

    # Prepare the prompt
    flat_prompt = "You are Melody, a helpful data science assistant.\n\n"
    if current_dataset:
        flat_prompt += f"Current dataset: {current_dataset}\n"
    for msg in conversation[1:]:
        flat_prompt += f"{msg['role'].capitalize()}: {msg['content']}\n"
    flat_prompt += f"User: {user_input}\n"

    # Generate response using Gemini
    try:
        async with mcp_client:  # <--- enter context even when using as a tool
            response = await gemini_client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=flat_prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0,
                    tools=[mcp_client.session],  # MCP client inside async with
                ),
            )

        if response is None or not hasattr(response, "text"):
            assistant_reply = "❌ Error: Model returned None."
        else:
            assistant_reply = response.text.strip()

        conversation.append({"role": "model", "content": assistant_reply})
        return assistant_reply

    except Exception as e:
        return f"Error during generation: {e}"


if __name__ == "__main__":
    try:
        asyncio.run(process_message())
    except KeyboardInterrupt:
        print("Goodbye!\n")