import os
from openai import OpenAI


def get_client():

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def generate_gpt_response(prompt):

    client = get_client()

    if client is None:
        return "AI service not configured. Please contact administrator."

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior financial and business consultant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()

    except Exception as e:

        return f"AI temporarily unavailable: {str(e)}"
