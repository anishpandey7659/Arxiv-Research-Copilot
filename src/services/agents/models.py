from pydantic import BaseModel,Field
from typing import List,Dict,Any


class SourceItem(BaseModel):
    arxiv_id: str = Field(description="Arxiv Id of the paper")
    title: str = Field(description="Title of the paper")
    author: List[str] = Field(description="Author of that paper")
    relevant_score: float = Field(default=0.0,description="Score of the Retrive chunks")
    url: str = Field(description="Url link of the paper")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "arxiv_id":self.arxiv_id,
            "title":self.title,
            "url":self.url,
            "author":self.author,
            "url":self.url
        }
