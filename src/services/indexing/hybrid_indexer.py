import logging
from typing import Dict,List,cast

from src.models.paper import Paper

from src.services.embeddings.jina_client import JinaEmbeddingsClient
from src.services.opensearch.client import OpenSearchClient
from src.services.indexing.textchunker import TextChunker


logger =logging.getLogger(__name__)


class HybridIndexingService:
    """ Service for indexing paper with chunking and embedding.

    Orchestrates the process of:
    1.Chunking the paper into overlapping segments.
    2.Making the embedding of obtain chunk text.
    3.Store the embed chunk text with metadata     
    
    """
    def __init__(self,chunker:TextChunker, embeddings_client:JinaEmbeddingsClient, opensearch_client:OpenSearchClient):
        """ Intializing the required Service for indexing
        :param TextChunker
        :param JinaEmbeddingsClient
        :param OpenSearchClient
        """
        self.opensearch_client =opensearch_client
        self.embedding_client =embeddings_client
        self.Text_chunker =chunker

    async def index_paper(self,paper_data:Paper):
        """Indexing the single paper with chunking and embedding
        :param paper_data: Paper data from database
        :returns : Dictionary with indexing statistics 
        """

        paper_id=str(getattr(paper_data, "id", None))
        arxiv_id=getattr(paper_data, "arxiv_id", None)
        if not arxiv_id:
            logger.error("Paper missing arxiv_id")
            return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}
        
        try:            
            chunks=self.Text_chunker.chunk_paper(
                            full_text=cast(str, paper_data.raw_text),
                            arxiv_id=arxiv_id,
                            paper_id=paper_id,
                            sections= cast(List, paper_data.sections),
                            )
            if chunks is None:
                logger.error(f"Get Empty chunk from Text_chunker: {arxiv_id}")
                return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}
            
            logger.info(f"Created {len(chunks)} chunks for paper {arxiv_id}")
            
            chunk_text = [chunk.text for chunk in chunks]
            chunks_embedding = await self.embedding_client.embed_passages(chunk_text)

            if len(chunks) != len(chunks_embedding):
                logger.error(f"Embedding count mismatch: {len(chunks_embedding)} != {len(chunks)}")
                return {"chunks_created": len(chunks), "chunks_indexed": 0, "embeddings_generated": len(chunks_embedding), "errors": 1}
            
            chunks_with_embeddings = []

            for chunk,embedding in zip(chunks,chunks_embedding):
                chunk_data={
                    "chunk_index":chunk.metadata.chunk_index,
                    "arxiv_id":arxiv_id,
                    "paper_id":paper_id,
                    "chunk_text": chunk.text,
                    "chunk_word_count":chunk.metadata.word_count,
                    "start_char":chunk.metadata.start_char,
                    "end_char":chunk.metadata.end_char,
                    "section_title":chunk.metadata.section_title,
                    "authors":paper_data.authors,
                    "abstract":paper_data.abstract,
                    "categories":paper_data.categories,
                    "published_date":paper_data.published_date,
                    "embedding_model":"jina-embeddings-v3",
                    "created_at":paper_data.created_at

                }
                chunks_with_embeddings.append({"chunk_data": chunk_data, "embedding": embedding})

            results=self.opensearch_client.bulk_index_chunks(chunks_with_embeddings)
            logger.info(f"Indexed paper {arxiv_id}: {results['success']} chunks successful, {results['failed']} failed")

            return {
                "chunks_created": len(chunks),
                "chunks_indexed": results["success"],
                "embeddings_generated": len(chunks_embedding),
                "errors": results["failed"],
            }

        except Exception as e:
            logger.error(f"Error indexing paper {arxiv_id}: {e}")
            return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}

    async def index_papers_batch(self, papers: List[Dict], replace_existing: bool = False) -> Dict[str, int]:
        """Index multiple papers in batch.

        :param papers: List of paper data
        :param replace_existing: If True, delete existing chunks before indexing
        :returns: Aggregated statistics
        """
        total_stats = {
            "papers_processed": 0,
            "total_chunks_created": 0,
            "total_chunks_indexed": 0,
            "total_embeddings_generated": 0,
            "total_errors": 0,
        }

        for paper in papers:
            arxiv_id = paper.get("arxiv_id")

            # Optionally delete existing chunks
            if replace_existing and arxiv_id:
                self.opensearch_client.delete_paper_chunks(arxiv_id)

            # Index the paper
            stats = await self.index_paper(paper)

            # Update totals
            total_stats["papers_processed"] += 1
            total_stats["total_chunks_created"] += stats["chunks_created"]
            total_stats["total_chunks_indexed"] += stats["chunks_indexed"]
            total_stats["total_embeddings_generated"] += stats["embeddings_generated"]
            total_stats["total_errors"] += stats["errors"]

        logger.info(
            f"Batch indexing complete: {total_stats['papers_processed']} papers, "
            f"{total_stats['total_chunks_indexed']} chunks indexed"
        )

        return total_stats

    async def reindex_paper(self, arxiv_id: str, paper_data: Dict) -> Dict[str, int]:
        """Reindex a paper by deleting old chunks and creating new ones.

        :param arxiv_id: ArXiv ID of the paper
        :param paper_data: Updated paper data
        :returns: Indexing statistics
        """
        # Delete existing chunks
        deleted = self.opensearch_client.delete_paper_chunks(arxiv_id)
        if deleted:
            logger.info(f"Deleted existing chunks for paper {arxiv_id}")

        # Index with new data
        return await self.index_paper(paper_data)
