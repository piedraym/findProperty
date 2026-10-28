from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Listing(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    source: str
    address: str
    city: str
    state: str
    zip: str
    price: float
    bedrooms: int
    bathrooms: float
    sqft: int
    latitude: float
    longitude: float
    listed_date: date
    status: Literal["active", "pending", "sold"]
    description: str

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.id}"


# A listing plus its relevance score.
# The score is None when the user did not give a target budget.
class ScoredListing(Listing):
    score: float | None = None


class SearchResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[ScoredListing]
    page: int
    page_size: int
    total: int
    total_pages: int
