from functools import cached_property

from fastembed import TextEmbedding


class Embedder:
    def __init__(self, model_name: str, cache_dir: str | None = None):
        self.model_name = model_name
        self.cache_dir = cache_dir

    @cached_property
    def model(self) -> TextEmbedding:
        return TextEmbedding(model_name=self.model_name, cache_dir=self.cache_dir)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model.embed(texts)]
