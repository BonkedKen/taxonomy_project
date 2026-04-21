from __future__ import annotations
import sys
import time
from pathlib import Path

from sqlmodel import Session

from database import engine, init_db
from models import Taxon, TaxonName
from parser import parse_nodes, parse_names

BATCH_SIZE = 5_000
DEFAULT_NODES = Path(__file__).parent / "sample_nodes.dmp"
DEFAULT_NAMES = Path(__file__).parent / "sample_names.dmp"


def _bulk_insert(session: Session, objects: list) -> None:
    session.add_all(objects)
    session.commit()


def populate_db(nodes_path, names_path, reset: bool = False) -> None:
    t_start = time.perf_counter()

    if reset:
        print("Dropping and recreating tables...")
        from sqlmodel import SQLModel
        SQLModel.metadata.drop_all(engine)

    init_db()

    print("Pass 1 - reading nodes...")
    node_records = list(parse_nodes(nodes_path))
    print(f"  Read {len(node_records):,} node records.")

    all_taxon_ids = {r.taxon_id for r in node_records}

    print("Pass 2 - inserting Taxon rows...")
    with Session(engine) as session:
        batch = []
        for i, rec in enumerate(node_records, start=1):
            batch.append(Taxon(
                taxon_id=rec.taxon_id,
                parent_taxon_id=None,
                rank=rec.rank,
                division_id=rec.division_id,
                genetic_code_id=rec.genetic_code_id,
            ))
            if len(batch) >= BATCH_SIZE:
                _bulk_insert(session, batch)
                batch = []
        if batch:
            _bulk_insert(session, batch)
    print(f"  Inserted {len(node_records):,} taxon rows.")

    print("Pass 3 - updating parent links...")
    with Session(engine) as session:
        for i, rec in enumerate(node_records, start=1):
            parent_id = (
                None
                if rec.parent_taxon_id == rec.taxon_id
                else rec.parent_taxon_id
            )
            taxon = session.get(Taxon, rec.taxon_id)
            if taxon is not None:
                taxon.parent_taxon_id = parent_id
            if i % BATCH_SIZE == 0:
                session.commit()
        session.commit()
    print(f"  Updated {len(node_records):,} parent links.")

    print("Pass 4 - inserting TaxonName rows...")
    skipped = 0
    count = 0
    with Session(engine) as session:
        batch_names = []
        for rec in parse_names(names_path):
            if rec.taxon_id not in all_taxon_ids:
                skipped += 1
                continue
            batch_names.append(TaxonName(
                taxon_id=rec.taxon_id,
                name_txt=rec.name_txt,
                unique_name=rec.unique_name or None,
                name_class=rec.name_class,
            ))
            count += 1
            if len(batch_names) >= BATCH_SIZE:
                _bulk_insert(session, batch_names)
                batch_names = []
        if batch_names:
            _bulk_insert(session, batch_names)
    print(f"  Inserted {count:,} name rows. ({skipped} skipped)")

    elapsed = time.perf_counter() - t_start
    print(f"\nDone! Database populated in {elapsed:.2f}s")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("nodes", nargs="?", default=str(DEFAULT_NODES))
    parser.add_argument("names", nargs="?", default=str(DEFAULT_NAMES))
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    if not Path(args.nodes).exists():
        sys.exit(f"ERROR: nodes file not found: {args.nodes}")
    if not Path(args.names).exists():
        sys.exit(f"ERROR: names file not found: {args.names}")

    populate_db(args.nodes, args.names, reset=args.reset)