# Taxonomy Browser

A full-stack web application for searching and exploring NCBI-style taxonomy data. Built with SQLModel, FastAPI, and Dash.

## File Structure

```
taxonomy_project/
├── models.py          # SQLModel table definitions (Taxon, TaxonName)
├── database.py        # Engine, session factory, init_db()
├── parser.py          # Parsers for nodes.dmp and names.dmp
├── populate.py        # Database population script
├── api.py             # FastAPI REST API (GET /taxa, GET /search)
├── app.py             # Dash SPA frontend
├── sample_nodes.dmp   # Sample NCBI-format nodes file (primate subset)
├── sample_names.dmp   # Sample NCBI-format names file (primate subset)
└── requirements.txt
```

## Setup

### 1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install sqlmodel fastapi uvicorn dash requests
```

### 2. Populate the database

```bash
python populate.py
```

### 3. Start the API server

```bash
uvicorn api:app --reload --port 8000
```

API docs available at: http://127.0.0.1:8000/docs

### 4. Start the Dash frontend

Open a second terminal:

```bash
source venv/bin/activate
python app.py
```

Open your browser at: http://127.0.0.1:8050

## API Reference

### GET /taxa
Returns full detail for one taxon.

- Parameter: `tax_id` (int, required) — NCBI taxonomy ID
- Returns: rank, parent, children, and all names
- Returns 404 if taxon not found

Example: http://127.0.0.1:8050/taxon?tax_id=9606&back=keyword%3Dhomo%26mode%3Dcontains%26page%3D1

### GET /search
Paginated search over all taxon names.

- Parameter: `keyword` (str, required) — search term
- Parameter: `mode` — contains, starts_with, or ends_with
- Parameter: `page` (default 1)
- Parameter: `per_page` (default 10, max 100)

Example: http://127.0.0.1:8050/search?keyword=homo&mode=contains&page=1

## What the Pages Mean

### Landing Page
- Search box for keyword
- Dropdown for match mode (Contains, Starts with, Ends with)
- Search button

### Search Results Page
- Table showing Taxonomy ID, Name, and Class
- Taxon IDs are clickable links to the detail page
- Pagination with Previous and Next buttons
- Total results and page counter

### Taxon Detail Page
- Shows taxon ID and rank
- Clickable parent taxon link
- Table of all child taxa
- Table of all associated names
- Back to Search Results link

## My Design Notes

### Database
- Two tables: Taxon and TaxonName
- Taxon has a self-referential foreign key for parent-child relationships
- Root node stores parent_taxon_id as NULL to avoid circular FK issues
- Data loaded in two passes to avoid insertion-order violations

### API
- FastAPI with Pydantic response schemas
- CORS middleware so Dash frontend can call the API
- Case-insensitive search using ilike()
- Proper 404 error handling

### Frontend
- Dash single-page application
- URL routing via dcc.Location
- Search state preserved in URL so Back button works correctly