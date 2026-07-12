"""
ResearchAI — IBM watsonx.ai Client
Wraps the ibm-watsonx-ai SDK for text generation and embeddings.
Implements retry logic, token counting, and structured prompt building.
"""

from __future__ import annotations
import time
from typing import Optional, List, Dict, Any

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from researchai.backend.core.logger import get_logger
from researchai.backend.core.exceptions import WatsonxError
from researchai.config import settings

logger = get_logger("watsonx_client")


class WatsonxClient:
    """
    Singleton client for IBM watsonx.ai API.
    Provides generate() and embed() methods used by all AI modules.
    """

    _instance: Optional["WatsonxClient"] = None

    def __new__(cls) -> "WatsonxClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._setup_client()

    def _setup_client(self) -> None:
        if not settings.WATSONX_API_KEY or not settings.WATSONX_PROJECT_ID:
            logger.warning(
                "WATSONX_API_KEY or WATSONX_PROJECT_ID not set. "
                "AI generation will use stub responses."
            )
            self._model = None
            return
        try:
            # Normalise URL: IBM Cloud SaaS uses ml.cloud.ibm.com or
            # regional endpoints like au-syd.ml.cloud.ibm.com /
            # au-syd.dai.cloud.ibm.com. The SDK Credentials class
            # accepts api_key only for IBM Cloud — never pass `username`
            # or `version` for the SaaS offering.
            url = settings.WATSONX_URL.rstrip("/")
            # Map legacy dai.cloud.ibm.com -> ml.cloud.ibm.com (same service)
            url = url.replace(".dai.cloud.ibm.com", ".ml.cloud.ibm.com")
            if "ml.cloud.ibm.com" not in url:
                # Unknown URL shape — log a warning but proceed
                logger.warning(
                    "Unexpected WATSONX_URL format: %s. "
                    "Expected *.ml.cloud.ibm.com for IBM Cloud SaaS.", url
                )

            credentials = Credentials(
                url=url,
                api_key=settings.WATSONX_API_KEY,
            )
            self._model = ModelInference(
                model_id=settings.GRANITE_MODEL_ID,
                credentials=credentials,
                project_id=settings.WATSONX_PROJECT_ID,
                params={
                    GenParams.MAX_NEW_TOKENS: settings.MAX_NEW_TOKENS,
                    GenParams.TEMPERATURE: settings.TEMPERATURE,
                    GenParams.TOP_P: settings.TOP_P,
                    GenParams.TOP_K: settings.TOP_K,
                    GenParams.REPETITION_PENALTY: settings.REPETITION_PENALTY,
                    GenParams.DECODING_METHOD: DecodingMethods.SAMPLE,
                },
            )
            logger.info(
                "watsonx client initialised — url: %s model: %s", url, settings.GRANITE_MODEL_ID
            )
        except Exception as exc:
            logger.error("Failed to initialise watsonx client: %s", exc)
            self._model = None

    # ------------------------------------------------------------------
    # Text Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        retries: int = 2,
    ) -> str:
        """
        Generate text from a prompt using IBM Granite.
        Falls back to an informative stub when credentials are absent.
        """
        if self._model is None:
            return self._stub_response(prompt)

        full_prompt = self._build_prompt(prompt, system_prompt)
        params: Dict[str, Any] = {}
        if max_new_tokens:
            params[GenParams.MAX_NEW_TOKENS] = max_new_tokens
        if temperature is not None:
            params[GenParams.TEMPERATURE] = temperature

        for attempt in range(retries + 1):
            try:
                response = self._model.generate_text(
                    prompt=full_prompt,
                    params=params if params else None,
                )
                logger.debug(
                    "generate() | prompt_len=%d | response_len=%d",
                    len(full_prompt),
                    len(response),
                )
                return response.strip()
            except Exception as exc:
                if attempt < retries:
                    wait = 2 ** attempt
                    logger.warning(
                        "watsonx generate attempt %d failed: %s — retrying in %ds",
                        attempt + 1, exc, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error("watsonx generate failed after %d retries: %s", retries, exc)
                    raise WatsonxError(f"Text generation failed: {exc}") from exc
        return ""

    def generate_structured(
        self,
        prompt: str,
        output_keys: List[str],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate text and attempt to parse a key:value structured output.
        Returns a dict with the requested keys (empty string if not found).
        """
        keys_instruction = (
            "Respond using EXACTLY the following structure. "
            "Each key on its own line followed by a colon and the value.\n"
            + "\n".join(f"{k}:" for k in output_keys)
            + "\n\nQuery:\n"
        )
        full_prompt = keys_instruction + prompt
        raw = self.generate(full_prompt, system_prompt=system_prompt)
        return self._parse_structured(raw, output_keys)

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Return sentence embeddings for a list of text strings.
        Falls back to zero-vectors when watsonx is not configured.
        """
        if self._model is None:
            dim = settings.EMBEDDING_DIMENSION
            return [[0.0] * dim for _ in texts]

        try:
            # Use sentence-transformers as the embedding backend
            # (ibm-watsonx-ai embedding endpoint requires specific model)
            from sentence_transformers import SentenceTransformer

            if not hasattr(self, "_embed_model"):
                self._embed_model = SentenceTransformer(
                    "sentence-transformers/all-MiniLM-L6-v2"
                )
            vecs = self._embed_model.encode(texts, convert_to_numpy=True)
            return [v.tolist() for v in vecs]
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. Using zero embeddings."
            )
            dim = settings.EMBEDDING_DIMENSION
            return [[0.0] * dim for _ in texts]
        except Exception as exc:
            raise WatsonxError(f"Embedding failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(prompt: str, system_prompt: Optional[str]) -> str:
        if system_prompt:
            return (
                f"<|system|>\n{system_prompt}\n"
                f"<|user|>\n{prompt}\n"
                f"<|assistant|>\n"
            )
        return f"<|user|>\n{prompt}\n<|assistant|>\n"

    @staticmethod
    def _parse_structured(text: str, keys: List[str]) -> Dict[str, str]:
        result: Dict[str, str] = {k: "" for k in keys}
        current_key: Optional[str] = None
        buffer: List[str] = []

        for line in text.splitlines():
            matched = False
            for k in keys:
                if line.lower().startswith(f"{k.lower()}:"):
                    if current_key:
                        result[current_key] = " ".join(buffer).strip()
                    current_key = k
                    buffer = [line[len(k) + 1:].strip()]
                    matched = True
                    break
            if not matched and current_key:
                buffer.append(line)

        if current_key:
            result[current_key] = " ".join(buffer).strip()
        return result

    @staticmethod
    def _stub_response(prompt: str) -> str:
        return (
            "[STUB — watsonx not configured] "
            "Please set WATSONX_API_KEY and WATSONX_PROJECT_ID in your .env file. "
            f"Your prompt was: {prompt[:120]}..."
        )


# Singleton accessor
def get_watsonx_client() -> WatsonxClient:
    return WatsonxClient()
