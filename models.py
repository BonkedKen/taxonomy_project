from __future__ import annotations
from typing import Optional
from sqlmodel import Field, SQLModel


class Taxon(SQLModel, table=True):
    __tablename__ = "taxon"

    taxon_id: int = Field(primary_key=True)
    parent_taxon_id: Optional[int] = Field(
        default=None,
        foreign_key="taxon.taxon_id",
        index=True
    )
    rank: str = Field(max_length=64, index=True)
    division_id: Optional[int] = Field(default=None)
    genetic_code_id: Optional[int] = Field(default=None)


class TaxonName(SQLModel, table=True):
    __tablename__ = "taxon_name"

    id: Optional[int] = Field(default=None, primary_key=True)
    taxon_id: int = Field(foreign_key="taxon.taxon_id", index=True)
    name_txt: str = Field(max_length=256, index=True)
    unique_name: Optional[str] = Field(default=None, max_length=256)
    name_class: str = Field(max_length=64, index=True)