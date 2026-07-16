from dataclasses import dataclass, field
from typing import Any,Dict
from src.schemas.arxiv.paper import PaperCreate

@dataclass
class PaperProcessingError:
    """Records a failure for a single paper without aborting the whole batch."""

    arxiv_id: str
    stage: str
    error: str


@dataclass
class PipelineResult:
    """Aggregated outcome of a full ingestion run."""

    processed: list[PaperCreate] = field(default_factory=list)
    stored: list[Any] = field(default_factory=list)
    indexed_stats : Dict[str, int]  = field(default_factory=dict)
    errors: list[PaperProcessingError] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Requested:  {self.timings.get('requested', 0)}",
            f"Processed:  {len(self.processed)}",
            f"Stored:     {len(self.stored)}",
            f"Indexed_Stats:    {self.indexed_stats}",
            f"Errors:     {len(self.errors)}",
        ]
        for key, value in self.timings.items():
            if key == "requested":
                continue
            lines.append(f"  {key}: {value:.2f}s")
        for err in self.errors:
            lines.append(f"  [FAILED] {err.arxiv_id} @ {err.stage}: {err.error}")
        return "\n".join(lines)

