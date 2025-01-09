import logging

import openai
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel
import time
import os
import json

api_key = os.getenv("OPEN_API_KEY")
if not api_key:
    raise ValueError("OPEN_API_KEY is not set")
client = OpenAI(
    api_key=api_key,
)
app = FastAPI()
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)


with open("prompts/lookup-prompt.txt", "r") as file:
    lookup_prompt = file.read()


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
        start_time = time.time()
        response = client.chat.completions.create(model="gpt-4o-mini",
                                                  messages=[
                                                      {
                                                          "role": "system",
                                                          "content": lookup_prompt
                                                      },
                                                      {
                                                          "role": "user",
                                                          "content": request.word
                                                      }
                                                  ],
                                                  response_format={ "type": "json_object" },
                                                  max_tokens=300)  # 213 maximum seen
        end_time = time.time()
        logging.info(f"OpenAPI Execution time: {end_time - start_time} seconds")
        logging.info(f"Token count: Input {response.usage.prompt_tokens}, "
                     f"Output {response.usage.completion_tokens}, "
                     f"Cached {response.usage.prompt_tokens_details.cached_tokens}, "
                     f"Total {response.usage.total_tokens}")
        logging.debug(response)

        response_text = response.choices[0].message.content.strip()
        response_data = json.loads(response_text)
        return DictionaryResponse(**response_data)
    except json.JSONDecodeError as e:
        logging.exception(f"Failed to parse response: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
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


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Run using: uvicorn arabic_dict_app:app --reload
