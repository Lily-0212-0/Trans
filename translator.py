"""OpenAI ChatGPT API를 이용해 텍스트를 영어/일본어/베트남어로 번역한다."""

import json
import os

import openai
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 30.0
MAX_CHARS = 2000

LANGUAGES = {
    "en": "English",
    "ja": "Japanese",
    "vi": "Vietnamese",
}

TONES = {
    "기본": "Keep the original tone of the source text.",
    "격식체": "Use a formal, polite tone suitable for business communication.",
    "캐주얼": "Use a casual, friendly tone suitable for chatting with friends.",
}

SYSTEM_PROMPT = """You are a professional translator.
Translate the user's text into English, Japanese, and Vietnamese.

Rules:
- Output ONLY a JSON object with exactly these keys: "en", "ja", "vi".
- Each value is the translated text only. No explanations, notes, or romanization.
- Preserve the meaning and nuance, and use natural, native-sounding expressions.
- Preserve line breaks, proper nouns, numbers, and formatting.
- If the source text is already in a target language, return a polished version of it for that key.
- {tone}"""


class TranslationError(Exception):
    """사용자에게 그대로 보여줄 수 있는 메시지를 담은 번역 오류."""


def get_model() -> str:
    return os.getenv("OPENAI_MODEL") or DEFAULT_MODEL


def _get_timeout() -> float:
    try:
        return float(os.getenv("OPENAI_TIMEOUT", DEFAULT_TIMEOUT))
    except ValueError:
        return DEFAULT_TIMEOUT


def _get_client() -> openai.OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise TranslationError(
            "OPENAI_API_KEY가 설정되지 않았습니다. "
            "프로그램 폴더의 .env 파일에 OPENAI_API_KEY=... 를 추가하세요."
        )
    return openai.OpenAI(api_key=api_key, timeout=_get_timeout())


def _parse(content: str) -> dict[str, str]:
    data = json.loads(content)
    if not all(isinstance(data.get(code), str) for code in LANGUAGES):
        raise ValueError("missing keys")
    return {code: data[code].strip() for code in LANGUAGES}


def translate(text: str, tone: str = "기본") -> dict[str, str]:
    """text를 번역해 {"en": ..., "ja": ..., "vi": ...} 형태로 반환한다."""
    text = text.strip()
    if not text:
        raise TranslationError("번역할 내용을 입력하세요.")
    if len(text) > MAX_CHARS:
        raise TranslationError(f"입력은 최대 {MAX_CHARS:,}자까지 가능합니다. (현재 {len(text):,}자)")

    client = _get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(tone=TONES.get(tone, TONES["기본"]))},
        {"role": "user", "content": text},
    ]

    # 응답 JSON 형식이 잘못된 경우 1회 재시도한다.
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=get_model(),
                messages=messages,
                response_format={"type": "json_object"},
            )
        except openai.AuthenticationError:
            raise TranslationError("API 키가 올바르지 않습니다. .env의 OPENAI_API_KEY를 확인하세요.")
        except openai.RateLimitError:
            raise TranslationError("요청이 많거나 크레딧이 부족합니다. 잠시 후 다시 시도하세요.")
        except openai.APITimeoutError:
            raise TranslationError("응답 시간이 초과되었습니다. 다시 시도하세요.")
        except openai.APIConnectionError:
            raise TranslationError("네트워크에 연결할 수 없습니다. 인터넷 연결을 확인하세요.")
        except openai.NotFoundError:
            raise TranslationError(f"모델 '{get_model()}'을(를) 찾을 수 없습니다. .env의 OPENAI_MODEL을 확인하세요.")
        except openai.APIError as e:
            raise TranslationError(f"OpenAI API 오류가 발생했습니다: {e}")

        try:
            return _parse(response.choices[0].message.content or "")
        except (json.JSONDecodeError, ValueError):
            if attempt == 1:
                raise TranslationError("번역 결과를 해석하지 못했습니다. 다시 시도하세요.")

    raise AssertionError("unreachable")
