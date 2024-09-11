import logging
import anthropic
from dotenv import load_dotenv
import asyncio
import os
import json

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# Guardrails configuration
GUARDRAILS_CONFIG = {
    "blocking": [
        {
            "name": "profanity_filter",
            "function": "check_profanity"
        },
        {
            "name": "sentiment_analysis",
            "function": "analyze_sentiment"
        }
    ],
    "non_blocking": [
        {
            "name": "log_conversation",
            "function": "log_to_database"
        },
        {
            "name": "update_user_stats",
            "function": "update_stats"
        }
    ]
}

class Guardrails:
    @staticmethod
    async def check_profanity(text):
        # Simulated profanity check
        print("Checking profanity...")
        profane_words = ["badword1", "badword2"]
        return not any(word in text.lower() for word in profane_words)

    @staticmethod
    async def analyze_sentiment(text):
        # Simulated sentiment analysis
        return True

    @staticmethod
    async def log_to_database(text):
        print(f"Logged to DB: {text[:20]}...")
        return True

    @staticmethod
    async def update_stats(text):
        print(f"Updated user stats: {len(text)} characters")
        return True

async def apply_guardrails(text, guardrail_type):
    tasks = []
    for guardrail in GUARDRAILS_CONFIG[guardrail_type]:
        func = getattr(Guardrails, guardrail['function'])
        tasks.append(func(text))
    
    results = await asyncio.gather(*tasks)
    return all(results) if guardrail_type == "blocking" else True

# """
# todo:
# improve latency by batching the streaming text to identify profanity/gaurd
# """
async def process_message(message: str, conversation_history: list) -> str:
    # Apply blocking guardrails
    if not await apply_guardrails(message, "blocking"):
        return "I'm sorry, but I can't process that message due to content restrictions."

    conversation_history.append({"role": "user", "content": message})
    client = anthropic.AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    try:
        logging.debug("Sending message to Anthropic API")
        response = await client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            temperature=0.7,
            messages=conversation_history
        )
        logging.debug("Received response from Anthropic API")

        ai_message = response.content[0].text
        conversation_history.append({"role": "assistant", "content": ai_message})
        
        
        if not await apply_guardrails(ai_message, "blocking"):
            return "I'm sorry, but I can't process that message due to content restrictions."

        # Apply non-blocking guardrails
        asyncio.create_task(apply_guardrails(ai_message, "non_blocking"))

        return ai_message
    except Exception as e:
        logging.error(f"Error in process_message: {str(e)}")
        raise

async def main():
    conversation_history = []
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("Goodbye!")
            break
        
        response = await process_message(user_input, conversation_history)
        print(f"AI: {response}")

if __name__ == "__main__":
    asyncio.run(main())