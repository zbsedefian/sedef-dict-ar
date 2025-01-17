import asyncio
import logging

import openai
from fastapi import FastAPI, HTTPException
from openai import OpenAI, AsyncOpenAI
from pydantic import BaseModel
import time
import os
import json
from langdetect import detect
from pathlib import Path
import uuid
from typing import List, Optional

from fastapi.middleware.cors import CORSMiddleware

max_tokens_word = 300
max_tokens_sentence = 5000

api_key = os.getenv("OPEN_API_KEY")
if not api_key:
    raise ValueError("OPEN_API_KEY is not set")
client = AsyncOpenAI(
    api_key=api_key,
)
app = FastAPI()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
# Allow all origins during development (unsafe for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all HTTP headers
)

with open("prompts/lookup-prompt.txt", "r") as file:
    lookup_prompt = file.read()

with open("prompts/lookup-prompt-multiple.txt", "r") as file:
    lookup_prompt_multiple = file.read()


class LookupRequest(BaseModel):
    input: str

class AsyncLookupRequest(BaseModel):
    input: str
    context: str

class DictionaryResponse(BaseModel):
    word: str
    language: str
    pos: str
    lemma: str
    english_meaning: str
    base_meaning: str
    transliteration: str
    attributes: dict

class SentenceLookupResponse(BaseModel):
    translation: str
    words: List[DictionaryResponse]

class SpeechResponse(BaseModel):
    filename: str

class BadRequestException(HTTPException):
    pass

class TranslationRequest(BaseModel):
    word: str
    context: str

class TranslationResponse(BaseModel):
    translation: str
    vocalized_sentence: str


def is_arabic(word):
    return detect(word) == 'ar'


@app.post("/lookup/word", response_model=DictionaryResponse)
async def lookup_word(request: LookupRequest):
    try:
        word = request.input
        if is_arabic(word) is False:
            logging.exception(f"User input error: {word}")
            raise BadRequestException(status_code=400, detail=f"Bad request exception: {word} is not Arabic")

        start_time = time.time()
        response = client.chat.completions.create(model="gpt-4o-mini",
                                                  messages=[
                                                      {
                                                          "role": "system",
                                                          "content": lookup_prompt
                                                      },
                                                      {
                                                          "role": "user",
                                                          "content": word
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

        err = response_data.get("error")
        if err:
            logging.exception(f"User input error: {err}")
            raise BadRequestException(status_code=400, detail=f"Bad request exception: {err}")

        if not response_data.get("word"):
            logging.exception(f"Unexpected API response: {response_data}")
            raise BadRequestException(status_code=500, detail=f"An unexpected error occurred: API response invalid")

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
    except BadRequestException as e:
        logging.exception("Bad request error occurred")
        raise HTTPException(status_code=400, detail=f"{str(e)}")
    except Exception as e:
        logging.exception("An unexpected error occurred")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@app.post("/lookup/sentence", response_model=SentenceLookupResponse)
async def lookup_sentence(request: LookupRequest):
    try:
        word = request.input
        if is_arabic(word) is False:
            logging.exception(f"User input error: {word}")
            raise BadRequestException(status_code=400, detail=f"Bad request exception: {word} is not Arabic")

        start_time = time.time()
        max_tokens = 6000
        response = client.chat.completions.create(model="gpt-4o-mini",
                                                  messages=[
                                                      {
                                                          "role": "system",
                                                          "content": lookup_prompt_multiple
                                                      },
                                                      {
                                                          "role": "user",
                                                          "content": word
                                                      }
                                                  ],
                                                  response_format={ "type": "json_object" },
                                                  max_tokens=max_tokens)
        end_time = time.time()
        logging.info(f"OpenAPI Execution time: {end_time - start_time} seconds")
        logging.info(f"Token count: Input {response.usage.prompt_tokens}, "
                     f"Output {response.usage.completion_tokens}, "
                     f"Cached {response.usage.prompt_tokens_details.cached_tokens}, "
                     f"Total {response.usage.total_tokens}")
        logging.debug(response)
        if response.usage.total_tokens == max_tokens:
            logging.exception(f"Tokens exceeded: {max_tokens}")
            raise BadRequestException(status_code=500, detail=f"Tokens exceeded. Input a shorter prompt.")

        response_data = json.loads(response.choices[0].message.content.strip())

        err = response_data.get("error")
        if err:
            logging.exception(f"User input error: {err}")
            raise BadRequestException(status_code=400, detail=f"Bad request exception: {err}")

        word_list = response_data.get("words")
        if not word_list:
            logging.exception(f"API returned bad response: {response_data}")
            raise HTTPException(status_code=500, detail=f"Internal API not working.")

        return SentenceLookupResponse(translation=response_data.get("translation"),
                                      words=[DictionaryResponse(**data) for data in word_list])
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
    except BadRequestException as e:
        logging.exception("Bad request error occurred")
        raise HTTPException(status_code=400, detail=f"{str(e)}")
    except Exception as e:
        logging.exception("An unexpected error occurred")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@app.post("/speech", response_model=SpeechResponse)
async def generate_speech(request: LookupRequest):
    unique_filename = f"{int(time.time())}_{uuid.uuid4()}.mp3"
    speech_file_path = Path(__file__).parent / unique_filename
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=request.input,
    )
    response.write_to_file(speech_file_path)
    return SpeechResponse(filename=speech_file_path.name)


@app.post("/lookup/sentence/async", response_model=SentenceLookupResponse)
async def lookup_sentence(request: LookupRequest):
    try:
        input_text = request.input
        if is_arabic(input_text) is False:
            logging.exception(f"User input error: {input_text}")
            raise BadRequestException(status_code=400, detail=f"Bad request exception: {input_text} is not Arabic")

        words = input_text.split()

        async def translate_sentence(lookup_request: LookupRequest):
            translation_prompt = 'Translate into English and fully vocalize the following Arabic sentence. Return in valid JSON format only: {"translation": "The lark nested by the road",  "vocalized_sentence": "عَشَّشَتْ قُبَّرَةٌ عَلَى طَرِيقٍ"}'
            start_time = time.time()
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": translation_prompt
                    },
                    {
                        "role": "user",
                        "content": lookup_request.model_dump_json()
                    }
                ],
                response_format={"type": "json_object"},
                # max_tokens=200
            )
            end_time = time.time()
            logging.info(response)
            logging.info(f"OpenAPI Execution time: {end_time - start_time} seconds")
            response_data = json.loads(response.choices[0].message.content.strip())
            return TranslationResponse(translation=response_data.get("translation"),
                                       vocalized_sentence=response_data.get("vocalized_sentence"))

        async def translate_word(lookup_request: AsyncLookupRequest):
            try:
                logging.info(lookup_request)
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": lookup_prompt
                        },
                        {
                            "role": "user",
                            "content": lookup_request.model_dump_json()
                        }
                    ],
                    response_format={"type": "json_object"},
                    # max_tokens=max_tokens_word
                )
                response_text = response.choices[0].message.content.strip()
                response_data = json.loads(response_text)
                if "error" in response_data:
                    logging.exception(f"API error for '{lookup_request}': {response_data['error']}")
                    return None
                return DictionaryResponse(**response_data)
            except Exception as e:
                logging.exception(f"Failed to process '{lookup_request}': {str(e)}")
                return None

        # Start OpenAPI calls
        start_time = time.time()

        translation_response = await translate_sentence(request)
        word_lookup_tasks = [translate_word(AsyncLookupRequest(input=word,
                                                               context=translation_response.vocalized_sentence))
                             for word in words]
        word_responses = await asyncio.gather(*word_lookup_tasks)

        end_time = time.time()
        logging.info(f"OpenAPI Execution time: {end_time - start_time} seconds")

        logging.info(word_responses)
        return SentenceLookupResponse(
            translation=translation_response.translation,
            words=word_responses
        )

    except json.JSONDecodeError as e:
        logging.exception(f"Failed to parse response: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    except openai.APIConnectionError as e:
        logging.exception("The server could not be reached")
        logging.exception(e.__cause__)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    except openai.RateLimitError as e:
        logging.exception("A 429 status code was received; we should back off a bit.")
        raise HTTPException(status_code=429, detail=f"An unexpected error occurred: {str(e)}")
    except openai.APIStatusError as e:
        logging.exception("Another non-200-range status code was received")
        logging.exception(e.status_code)
        logging.exception(e.response)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    except BadRequestException as e:
        logging.exception("Bad request error occurred")
        raise HTTPException(status_code=400, detail=f"{str(e)}")
    except Exception as e:
        logging.exception("An unexpected error occurred")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Run using: uvicorn arabic_dict_app:app --reload
