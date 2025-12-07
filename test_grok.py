from groq import Groq
import os

# Get API key
api_key = os.getenv('GROQ_API_KEY') or input("Enter your Groq API key: ")

client = Groq(api_key=api_key)

# Test these models
models = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-groq-70b-8192-tool-use-preview",
    "llama3-groq-8b-8192-tool-use-preview",
    "gemma2-9b-it",
    "gemma-7b-it",
    "llama-3.2-1b-preview",
    "llama-3.2-3b-preview",
    "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview",
]

print("🔍 Testing Groq models...\n")

working = []
for model in models:
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "Hi"}],
            model=model,
            max_tokens=10
        )
        result = response.choices[0].message.content
        print(f"✅ {model} - WORKS!")
        working.append(model)
    except Exception as e:
        error = str(e)
        if "decommissioned" in error:
            print(f"❌ {model} - Decommissioned")
        elif "404" in error:
            print(f"❌ {model} - Not found")
        else:
            print(f"❌ {model} - {error[:50]}")

print(f"\n{'='*60}")
print(f"✅ Working models: {len(working)}")
if working:
    print(f"\n💡 USE THIS MODEL: {working[0]}")
    print(f"\nPowerShell command:")
    print(f"$env:GROQ_MODEL = '{working[0]}'")
print(f"{'='*60}")