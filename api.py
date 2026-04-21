from __future__ import annotations
from typing import Generator, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_db_session
from models import Taxon, TaxonName


app = FastAPI(
    title="Taxonomy API",
    description="Search and explore NCBI-style taxonomy data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


class NameOut(BaseModel):
    name_txt: str
    unique_name: Optional[str]
    name_class: str

    class Config:
        from_attributes = True


class ChildOut(BaseModel):
    taxon_id: int
    rank: str
    scientific_name: Optional[str]

    class Config:
        from_attributes = True


class ParentOut(BaseModel):
    taxon_id: int
    rank: str
    scientific_name: Optional[str]

    class Config:
        from_attributes = True


class TaxonDetailOut(BaseModel):
    taxon_id: int
    rank: str
    parent: Optional[ParentOut]
    children: List[ChildOut]
    names: List[NameOut]

    class Config:
        from_attributes = True


class SearchResultItem(BaseModel):
    taxon_id: int
    name_txt: str
    name_class: str

    class Config:
        from_attributes = True


class SearchResultOut(BaseModel):
    total: int
    page: int
    per_page: int
    results: List[SearchResultItem]


def _get_scientific_name(session: Session, taxon_id: int) -> Optional[str]:
    stmt = (
        select(TaxonName.name_txt)
        .where(TaxonName.taxon_id == taxon_id)
        .where(TaxonName.name_class == "scientific name")
        .limit(1)
    )
    return session.exec(stmt).first()


@app.get("/taxa", response_model=TaxonDetailOut, tags=["Taxonomy"])
def get_taxon(
    tax_id: int = Query(..., description="NCBI taxonomy ID", gt=0),
    session: Session = Depends(get_db_session),
) -> TaxonDetailOut:
    taxon: Optional[Taxon] = session.get(Taxon, tax_id)
    if taxon is None:
        raise HTTPException(status_code=404, detail=f"Taxon {tax_id} not found.")

    parent_out: Optional[ParentOut] = None
    if taxon.parent_taxon_id is not None:
        parent: Optional[Taxon] = session.get(Taxon, taxon.parent_taxon_id)
        if parent is not None:
            parent_out = ParentOut(
                taxon_id=parent.taxon_id,
                rank=parent.rank,
                scientific_name=_get_scientific_name(session, parent.taxon_id),
            )

    children_stmt = select(Taxon).where(Taxon.parent_taxon_id == tax_id)
    children_rows = session.exec(children_stmt).all()
    children_out: List[ChildOut] = [
        ChildOut(
            taxon_id=c.taxon_id,
            rank=c.rank,
            scientific_name=_get_scientific_name(session, c.taxon_id),
        )
        for c in children_rows
    ]

    names_stmt = select(TaxonName).where(TaxonName.taxon_id == tax_id)
    name_rows = session.exec(names_stmt).all()
    names_out: List[NameOut] = [
        NameOut(
            name_txt=n.name_txt,
            unique_name=n.unique_name,
            name_class=n.name_class,
        )
        for n in name_rows
    ]

    return TaxonDetailOut(
        taxon_id=taxon.taxon_id,
        rank=taxon.rank,
        parent=parent_out,
        children=children_out,
        names=names_out,
    )


@app.get("/search", response_model=SearchResultOut, tags=["Search"])
def search_taxa(
    keyword: str = Query(..., description="Search keyword", min_length=1),
    mode: Literal["contains", "starts_with", "ends_with"] = Query(
        "contains", description="Match mode"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Results per page"),
    session: Session = Depends(get_db_session),
) -> SearchResultOut:
    kw_escaped = keyword.replace("%", r"\%").replace("_", r"\_")
    if mode == "contains":
        pattern = f"%{kw_escaped}%"
    elif mode == "starts_with":
        pattern = f"{kw_escaped}%"
    else:
        pattern = f"%{kw_escaped}"

    base_stmt = (
        select(TaxonName)
        .where(TaxonName.name_txt.ilike(pattern))
        .order_by(TaxonName.taxon_id, TaxonName.name_class)
    )

    total: int = len(session.exec(base_stmt).all())

    offset = (page - 1) * per_page
    page_stmt = base_stmt.offset(offset).limit(per_page)
    rows = session.exec(page_stmt).all()

    results: List[SearchResultItem] = [
        SearchResultItem(
            taxon_id=r.taxon_id,
            name_txt=r.name_txt,
            name_class=r.name_class,
        )
        for r in rows
    ]

    return SearchResultOut(
        total=total,
        page=page,
        per_page=per_page,
        results=results,
    )


@app.get("/health", tags=["Utility"])
def health_check() -> dict:
    return {"status": "ok"}