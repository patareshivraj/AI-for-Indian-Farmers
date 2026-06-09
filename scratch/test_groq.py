import os
from groq import Client

client = Client(api_key=os.environ["GROQ_API_KEY"])

try:
    completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Return valid JSON."},
            {"role": "user", "content": "Extract scheme details."}
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    print(completion.choices[0].message.content)
except Exception as e:
    import traceback
    traceback.print_exc()
