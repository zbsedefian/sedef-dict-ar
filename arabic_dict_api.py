import logging

import openai
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel
import time
import os

api_key = os.getenv("OPEN_API_KEY")
if not api_key:
    raise ValueError("API_KEY is not set")
client = OpenAI(
    api_key=api_key,
)
app = FastAPI()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)


with open("prompt.txt", "r") as file:
    prompt = file.read()


class DictionaryRequest(BaseModel):
    word: str


class DictionaryResponse(BaseModel):
    word: str
    language: str
    pos: str
    lemma: str
    english_meaning: str
    base_meaning: str
    attributes: dict


@app.post("/lookup", response_model=DictionaryResponse)
async def lookup_word(request: DictionaryRequest):
    try:
        # Send request to the OpenAI ChatCompletion API
        start_time = time.time()
        response = client.chat.completions.create(model="gpt-4o-mini",
                                                  messages=[
                                                      {
                                                          "role": "system",
                                                          "content": prompt
                                                      },
                                                      {
                                                          "role": "user",
                                                          "content": request.word
                                                      }
                                                  ],
                                                  max_tokens=300)  # 206 maximum seen
        end_time = time.time()
        logging.info(f"OpenAPI Execution time: {end_time - start_time} seconds")
        logging.info(f"Token count: Input {response.usage.prompt_tokens}, "
                     f"Output {response.usage.completion_tokens}, "
                     f"Total {response.usage.total_tokens}")

        response_text = response.choices[0].message.content.strip()
        logging.debug(response_text)

        response_data = eval(response_text)

        return DictionaryResponse(
            word=response_data.get("word"),
            language=response_data.get("language"),
            pos=response_data.get("pos"),
            lemma=response_data.get("lemma"),
            english_meaning=response_data.get("english_meaning"),
            base_meaning=response_data.get("base_meaning"),
            attributes=response_data.get("attributes")
        )

    except openai.APIConnectionError as e:
        logging.exception("The server could not be reached")
        logging.exception(e.__cause__)  # an underlying Exception, likely raised within httpx.
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    except openai.RateLimitError as e:
        logging.exception("A 429 status code was received; we should back off a bit.")
        raise HTTPException(status_code=429, detail=f"An unexpected error occurred: {str(e)}")
    except openai.APIStatusError as e:
        logging.exception("Another non-200-range status code was received")
        logging.exception(e.status_code)
        logging.exception(e.response)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    except Exception as e:
        logging.exception("An unexpected error occurred")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


# Run using: uvicorn arabic_dict_app:app --reload
