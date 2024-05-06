import logging
import os

import aiohttp
import requests
from typing import List, Optional

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.core.callbacks.base import CallbackManager

logger = logging.getLogger(__name__)

"""DeepInfra Inference API URL."""
INFERENCE_URL = "https://api.deepinfra.com/v1/inference"
"""Environment variable name of DeepInfra API token."""
ENV_VARIABLE = "DEEPINFRA_API_TOKEN"
"""Default model ID for DeepInfra embeddings."""
DEFAULT_MODEL_ID = "sentence-transformers/clip-ViT-B-32"
"""Maximum batch size for embedding requests."""
MAX_BATCH_SIZE = 1024


class DeepInfraEmbeddingModel(BaseEmbedding):
    """
    A wrapper class for accessing embedding models available via the DeepInfra API. This class allows for easy integration
    of DeepInfra embeddings into your projects, supporting both synchronous and asynchronous retrieval of text embeddings.

    Args:
        model_id (str): Identifier for the model to be used for embeddings. Defaults to 'sentence-transformers/clip-ViT-B-32'.
        normalize (bool): Flag to normalize embeddings post retrieval. Defaults to False.
        api_token (str): DeepInfra API token. If not provided,
        the token is fetched from the environment variable 'DEEPINFRA_API_TOKEN'.

    Examples:
        >>> from llama_index.embeddings.deepinfra import DeepInfraEmbeddingModel
        >>> model = DeepInfraEmbeddingModel()
        >>> print(model.get_text_embedding("Hello, world!"))
        [0.1, 0.2, 0.3, ...]
    """

    _model_id: str = PrivateAttr()
    _normalize: bool = PrivateAttr()
    _api_token: str = PrivateAttr()
    _query_prefix: str = PrivateAttr()
    _text_prefix: str = PrivateAttr()

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        normalize: bool = False,
        api_token: str = None,
        callback_manager: Optional[CallbackManager] = None,
        query_prefix: str = "",
        text_prefix: str = "",
    ) -> None:
        """
        Init params.
        """
        self._model_id = model_id
        self._normalize = normalize
        self._api_token = os.getenv(ENV_VARIABLE, api_token)
        self._query_prefix = query_prefix
        self._text_prefix = text_prefix

        super().__init__(callback_manager=callback_manager)

    def _post(self, data: List[str]) -> List[List[float]]:
        """
        Sends a POST request to the DeepInfra Inference API with the given data and returns the API response.
        Input data is chunked into batches to avoid exceeding the maximum batch size (1024).

        Args:
            data (List[str]): A list of strings to be embedded.

        Returns:
            dict: A dictionary containing embeddings from the API.
        """
        url = self.get_url()
        chunked_data = _chunk(data)
        embeddings = []
        for chunk in chunked_data:
            response = requests.post(
                url,
                json={
                    "inputs": chunk,
                },
                headers={
                    "Authorization": f"Bearer {self._api_token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            embeddings.extend(response.json()["embeddings"])
        return embeddings

    def get_url(self):
        """
        Get DeepInfra API URL.
        """
        return f"{INFERENCE_URL}/{self._model_id}"

    async def _apost(self, data: List[str]) -> List[List[float]]:
        """
        Sends a POST request to the DeepInfra Inference API with the given data and returns the API response.
        Input data is chunked into batches to avoid exceeding the maximum batch size (1024).

        Args:
            data (List[str]): A list of strings to be embedded.
        Output:
            List[float]: A list of embeddings from the API.

        """
        url = self.get_url()
        chunked_data = _chunk(data)
        embeddings = []
        for chunk in chunked_data:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={
                        "inputs": chunk,
                    },
                    headers={
                        "Authorization": f"Bearer {self._api_token}",
                        "Content-Type": "application/json",
                    },
                ) as resp:
                    response = await resp.json()
                    embeddings.extend(response["embeddings"])
        return embeddings

    def _get_query_embedding(self, query: str) -> List[float]:
        """
        Get query embedding.
        """
        return self._post(self._add_query_prefix([query]))[0]

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """
        Async get query embedding.
        """
        response = await self._apost(self._add_query_prefix([query]))
        return response[0]

    def _get_query_embeddings(self, queries: List[str]) -> List[List[float]]:
        """
        Get query embeddings.
        """
        return self._post(self._add_query_prefix(queries))

    async def _aget_query_embeddings(self, queries: List[str]) -> List[List[float]]:
        """
        Async get query embeddings.
        """
        return await self._apost(self._add_query_prefix(queries))

    def _get_text_embedding(self, text: str) -> List[float]:
        """
        Get text embedding.
        """
        return self._post(self._add_text_prefix([text]))[0]

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """
        Async get text embedding.
        """
        response = await self._apost(self._add_text_prefix([text]))
        return response[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get text embedding.
        """
        return self._post(self._add_text_prefix(texts))

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Async get text embeddings.
        """
        return await self._apost(self._add_text_prefix(texts))

    def _add_query_prefix(self, queries: List[str]) -> List[str]:
        """
        Add query prefix to queries.
        """
        return [self._query_prefix + query for query in queries]

    def _add_text_prefix(self, texts: List[str]) -> List[str]:
        """
        Add text prefix to texts.
        """
        return [self._text_prefix + text for text in texts]


def _chunk(items: List[str]) -> List[List[str]]:
    """
    Chunk items into batches of size MAX_BATCH_SIZE.
    """
    return [items[i : i + MAX_BATCH_SIZE] for i in range(0, len(items), MAX_BATCH_SIZE)]