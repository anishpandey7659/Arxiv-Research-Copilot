from .textchunker import TextChunker
from src.config import get_settings

def get_TextChunker(chunk_size: int,overlap_size: int,min_chunk_size: int):
    setting=get_settings()
    client=TextChunker(setting.chunker.chunk_size,setting.chunker.overlap_size,setting.chunker.min_chunk_size)
    return client