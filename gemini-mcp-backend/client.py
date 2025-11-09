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
    {"role": "system", "content": "You are Melody, a helpful data science assistant that can analyze datasets using MCP tools."}
]

async def run_data_science_assistant():

    print("Hello, I am Melody, your personal Data Science Assistant!\n")
    print("Type 'exit' to quit at any time.\n\n")
    
    async with mcp_client:

        current_dataset = None
        # datasets = []
        while True:
            user_input = input("You: ").strip()

            if user_input.lower() in {"exit"}:
                print("Goodbye!")
                break

            if user_input.lower().endswith(".csv") and os.path.exists(user_input.strip('"')):
                current_dataset = user_input.strip('"')
                print(f"Dataset path updated to: {current_dataset}\n")

                conversation.append({
                    "role": "user",
                    "content": f"I've uploaded a new dataset located at {current_dataset}."
                })
                conversation.append({
                    "role": "model",
                    "content": f"Got it! The dataset path is now {current_dataset}. You can ask me to summarize or analyze it."
                })
                continue

            if current_dataset:
                full_prompt = (
                    f"{user_input}\n"
                    f"Current dataset path is: {current_dataset}\n"
                    "Use MCP tools like load_csv, summarize_data, or run_linear_regression as necessary."
                )
            else:
                full_prompt = (
                    f"{user_input}\n"
                    "No dataset loaded yet. Ask the user to load one using a file path ending in '.csv'."
                )
            conversation.append({"role": "user", "content": full_prompt})
            
            try:
                # Flatten conversation into a single string
                flat_prompt = "You are Melody, a helpful data science assistant that can analyze datasets using MCP tools.\n\n"

                if current_dataset:
                    flat_prompt += f"Current dataset path: {current_dataset}\n"

                for msg in conversation[1:]:  # skip system message
                    role = msg["role"].capitalize()
                    content = msg["content"]
                    flat_prompt += f"{role}: {content}\n"

                # Add the current user input at the end
                flat_prompt += f"User: {user_input}\n"

                response = await gemini_client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=flat_prompt,  # ✅ string only
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

#dataset_path = r"C:\Users\anirk\Downloads\archive\1.01. Simple linear regression.csv"
#dataset_path = input("Enter dataset path (drag file here): ").strip().strip('"')
#user_request = f"Analyze the dataset {dataset_path} and find relationships between SAT scores and GPA."

if __name__ == "__main__":
    try:
        asyncio.run(run_data_science_assistant())
    except KeyboardInterrupt:
        print("Goodbye!\n")