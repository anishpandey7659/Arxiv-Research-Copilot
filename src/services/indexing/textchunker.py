import json
import logging
import re
from typing import Dict, List, Optional, Union

from src.schemas.indexing.models import ChunkMetadata, TextChunk

logger = logging.getLogger(__name__)


class TextChunker:
    """Service for chunking text into overlapping segments.

    Uses word-based chunking with configurable chunk size and overlap.
    Default: 600 words per chunk with 100 word overlap.
    """

    def __init__(self, chunk_size: int = 600, overlap_size: int = 100, min_chunk_size: int = 100):
        """Initialize text chunker.

        :param chunk_size: Target number of words per chunk
        :param overlap_size: Number of overlapping words between chunks
        :param min_chunk_size: Minimum words for a chunk to be valid
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size

        if overlap_size >= chunk_size:
            raise ValueError("Overlap size must be less than chunk size")

        logger.info(
            f"Text chunker initialized: chunk_size={chunk_size}, overlap_size={overlap_size}, min_chunk_size={min_chunk_size}"
        )

    def _split_into_words(self, text: str) -> List[str]:
        """Split text into words while preserving whitespace information.

        :param text: Input text
        :returns: List of words
        """
        # Split on whitespace while keeping the words
        words = re.findall(r"\S+", text)
        return words

    def _reconstruct_text(self, words: List[str]) -> str:
        """Reconstruct text from words.

        :param words: List of words
        :returns: Reconstructed text
        """
        return " ".join(words)


    def _append_chunk(self,chunks:List[TextChunk], chunk_dict:TextChunk, chunk_size:int=600, min_words:int=100):
        """Append a chunk to the list, merging into the previous chunk if it's too small."""
        if chunks and chunk_dict.metadata.word_count < min_words:
            prev = chunks[-1]
            # only merge if it won't blow past ~1.5x target (avoid oversized chunks)
            if prev.metadata.word_count + chunk_dict.metadata.word_count <= chunk_size * 1.5:
                prev.text = prev.text+ " " + chunk_dict.text
                prev.metadata.word_count = len(prev.text.split())
                prev.metadata.section_title = f"{prev.metadata.section_title}+{chunk_dict.metadata.section_title}"
                return
        chunks.append(chunk_dict)

    def chunk_paper(
        self,
        full_text: str,
        arxiv_id: str,
        paper_id: str,
        sections: List[dict] = None,
    ) -> List[TextChunk]:
        """Chunk a paper using hybrid section-based approach.

        Strategy:
        - If sections is given then used section based chunking
        - Fallback to traditional chunking if no sections available

        :param full_text: Full text content
        :param arxiv_id: ArXiv ID of the paper
        :param paper_id: Database ID of the paper
        :param sections: Dictionary or JSON string of sections
        :returns: List of text chunks with metadata
        """
        # Try section-based chunking first
        if sections:
            try:
                section_chunks = self._section_based_chunking(sections,arxiv_id,paper_id)
                if section_chunks:
                    logger.info(f"Created {len(section_chunks)} section-based chunks for {arxiv_id}")
                    return section_chunks
            except Exception as e:
                logger.warning(f"Section-based chunking failed for {arxiv_id}: {e}")

        # Fallback to traditional word-based chunking
        logger.info(f"Using traditional word-based chunking for {arxiv_id}")
        return self.chunk_text(full_text, arxiv_id, paper_id)

    def chunk_text(self, text: str, arxiv_id: str, paper_id: str) -> List[TextChunk]:
        """Chunk text into overlapping segments.

        :param text: Full text to chunk
        :param arxiv_id: ArXiv ID of the paper
        :param paper_id: Database ID of the paper
        :returns: List of text chunks with metadata
        """
        if not text or not text.strip():
            logger.warning(f"Empty text provided for paper {arxiv_id}")
            return []

        # Split text into words
        words = self._split_into_words(text)

        if len(words) < self.min_chunk_size:
            logger.warning(f"Text for paper {arxiv_id} has only {len(words)} words, less than minimum {self.min_chunk_size}")
            # Return single chunk if text is too small
            if words:
                return [
                    TextChunk(
                        text=self._reconstruct_text(words),
                        metadata=ChunkMetadata(
                            chunk_index=0,
                            start_char=0,
                            end_char=len(text),
                            word_count=len(words),
                            overlap_with_previous=0,
                            overlap_with_next=0,
                        ),
                        arxiv_id=arxiv_id,
                        paper_id=paper_id,
                    )
                ]
            return []

        chunks = []
        chunk_index = 0
        current_position = 0

        while current_position < len(words):
            # Calculate chunk boundaries
            chunk_start = current_position
            chunk_end = min(current_position + self.chunk_size, len(words))

            # Extract chunk words
            chunk_words = words[chunk_start:chunk_end]
            chunk_text = self._reconstruct_text(chunk_words)

            # Calculate character offsets (approximate)
            start_char = len(" ".join(words[:chunk_start])) if chunk_start > 0 else 0
            end_char = len(" ".join(words[:chunk_end]))

            # Calculate overlaps
            overlap_with_previous = min(self.overlap_size, chunk_start) if chunk_start > 0 else 0
            overlap_with_next = self.overlap_size if chunk_end < len(words) else 0

            # Create chunk
            chunk = TextChunk(
                text=chunk_text,
                metadata=ChunkMetadata(
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                    word_count=len(chunk_words),
                    overlap_with_previous=overlap_with_previous,
                    overlap_with_next=overlap_with_next,
                    section_title=None,  # Could be enhanced with section detection
                ),
                arxiv_id=arxiv_id,
                paper_id=paper_id,
            )
            chunks.append(chunk)

            # Move to next chunk position (with overlap)
            current_position += self.chunk_size - self.overlap_size
            chunk_index += 1

            # Break if we've processed all words
            if chunk_end >= len(words):
                break

        logger.info(f"Chunked paper {arxiv_id}: {len(words)} words -> {len(chunks)} chunks")

        return chunks

    def _section_based_chunking(self,sections_data:List,arxiv_id:str,paper_id:str) -> List[TextChunk]:
        """Production-ready section-based chunking with overlaps and small-chunk merging.

        Args:
            sections_data: List of section dicts with 'title'/'content' keys, or dict (optional)
            Arxiv_id : For metadata:str
            paper_id : For metadata:str

        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []

        chunk_index = 0

        if isinstance(sections_data, list):
            sections_items = [(item.get('title', f'section_{i}'), item.get('content', ''))
                                for i, item in enumerate(sections_data) if isinstance(item, dict)]
        else:
            sections_items = list(sections_data.items())

        for section_name, section_content in sections_items:
            if not section_content or len(str(section_content).strip()) < 10:
                continue

            section_text = str(section_content).strip()
            words = self._split_into_words(section_text)
            
            if len(words) <= self.chunk_size:
                chunk_dict =self._create_section_chunk(section_text,section_name,chunk_index,arxiv_id,paper_id)
                self._append_chunk(chunks,chunk_dict, self.chunk_size,self.min_chunk_size)
                chunk_index += 1
            else:
                start = 0
                while start < len(words):
                    end = start + self.chunk_size
                    chunk_words = words[start:end]
                    chunk_text = self._reconstruct_text(chunk_words)
                    chunk_dict =self._create_section_chunk(chunk_text,section_name,chunk_index,arxiv_id,paper_id)
                    self._append_chunk(chunks,chunk_dict, self.chunk_size, self.min_chunk_size)
                    chunk_index += 1
                    start += (self.chunk_size - self.overlap_size)

                    if end >= len(words):
                        break

        # re-index after merges (since some entries got absorbed)
        for i, c in enumerate(chunks):
            c.metadata.chunk_index=i

        return chunks

    def _create_section_chunk(
        self, chunk_text: str, section_title: str, chunk_index: int, arxiv_id: str, paper_id: str
    ) -> TextChunk:
        """Create a single section-based chunk."""
        return TextChunk(
            text=chunk_text,
            metadata=ChunkMetadata(
                chunk_index=chunk_index,
                start_char=0,
                end_char=len(chunk_text),
                word_count=len(chunk_text.split()),
                overlap_with_previous=0,
                overlap_with_next=0,
                section_title=section_title,
            ),
            arxiv_id=arxiv_id,
            paper_id=paper_id,
        )
