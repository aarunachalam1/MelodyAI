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
    {"role": "system", "content": "You are Melody, a helpful and friendly data science expert that can analyze datasets using MCP tools. You have access to a tool list datasets that allows you to view what datasets are loaded at any time, please use this before stating that there are no datasets loaded to confirm. The server persists datasets and models between sessions so make sure you run list datasets and list models before speaking with the user so you can check what they had in their previous session."}
]

async def run_data_science_assistant():

    print("Hello, I am Melody, your personal Data Science Assistant!\n")
    print("Type 'exit' to quit at any time.\n\n")
    
    async with mcp_client:

        current_dataset = None
        while True:
            user_input = input("You: ").strip('"')

            if user_input.lower() in {"exit"}:
                print("Goodbye!")
                break

            if user_input.lower().endswith(".csv") and os.path.exists(user_input.strip('"')):
                current_dataset = user_input.strip('"')
                print(f"Dataset path updated to: {current_dataset}\n")

                result = await mcp_client.call_tool("load_csv", {"file_path": current_dataset})

                if hasattr(result, "structured_content") and result.structured_content:
                    result_data = result.structured_content
                elif hasattr(result, "data") and result.data:
                    result_data = result.data
                else:
                    result_data = getattr(result, "text", str(result))

                print(f"✅ Server loaded dataset successfully:")
                print(f"   Columns: {result_data.get('columns', [])}")
                print(f"   Rows: {result_data.get('num_rows', 'unknown')}\n")


                conversation.append({
                    "role": "user",
                    "content": f"I've uploaded a new dataset located at {current_dataset}. Please make sure you run your list datasets tool before telling me that no datasets have been loaded."
                })
                conversation.append({
                    "role": "model",
                    "content": f"Got it! The dataset path is now {current_dataset}. You can ask me to summarize or analyze it. I will run list datasets before telling the user no datasets have been loaded"
                })
                continue

            if current_dataset != None:
                full_prompt = (
                    f"{user_input}\n"
                    f"The dataset '{current_dataset}' has been loaded successfully and is ready for analysis. "
                    "Use MCP tools such as summarize_data or run_linear_regression on this dataset."
                    "Make sure you run list datasets before telling me no datasets have been loaded"
                )
            else:
                full_prompt = (
                    f"{user_input}\n"
                    "No dataset loaded yet. State that you would love to help and very kindly ask the user to load one using a file path ending in '.csv'."
                )
            conversation.append({"role": "user", "content": full_prompt})
            
            try:
                # Flatten conversation into a single string
                flat_prompt = "You are Melody, a helpful data science assistant that can analyze datasets using MCP tools.\n\n"

                if current_dataset:
                    flat_prompt += f"Current dataset path: {current_dataset}\n"

                for msg in conversation[1:]:
                    role = msg["role"].capitalize()
                    content = msg["content"]
                    flat_prompt += f"{role}: {content}\n"

                flat_prompt += f"User: {user_input}\n"

                response = await gemini_client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=flat_prompt,
                    config=genai.types.GenerateContentConfig(
                        temperature=0,
                        tools=[mcp_client.session],
                    ),
                )

                assistant_reply = response.text.strip()
                print(f"\nAssistant: {assistant_reply}\n")

                conversation.append({"role": "model", "content": assistant_reply})
            except Exception as e:
                print(f"Error during generation: {e}\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_data_science_assistant())
    except KeyboardInterrupt:
        print("Goodbye!\n")