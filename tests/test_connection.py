
import os

from dotenv import load_dotenv
from openai import OpenAI


def main():

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found in .env"
        )

    client = OpenAI(
        api_key=api_key,
        timeout=30.0
    )

    models = client.models.list()

    print("=" * 50)
    print("FinSight AI - Connection Test")
    print("=" * 50)

    print("API key loaded successfully.")
    print("OpenAI connection successful.")

    print("\nAvailable GPT models:")

    model_ids = sorted(
        model.id
        for model in models.data
        if model.id.startswith("gpt-")
    )

    for model_id in model_ids:
        print(model_id)

    print("\nConnection test completed.")


if __name__ == "__main__":
    main()
