from __future__ import annotations
import urllib.parse
from typing import Any

import requests
import dash
from dash import dcc, html, Input, Output, State, callback, no_update

API_BASE = "http://127.0.0.1:8000"
PER_PAGE = 10

PAGE_STYLE: dict[str, Any] = {
    "maxWidth": "860px",
    "margin": "40px auto",
    "padding": "32px 40px",
    "backgroundColor": "#f7f8fa",
    "borderRadius": "12px",
    "fontFamily": "'Segoe UI', Arial, sans-serif",
    "boxShadow": "0 2px 12px rgba(0,0,0,0.07)",
}

LINK_STYLE: dict[str, Any] = {
    "color": "#1a73e8",
    "textDecoration": "none",
    "fontWeight": "500",
}

HOME_LINK = html.A("Home", href="/", style={**LINK_STYLE, "fontSize": "15px"})

H1_STYLE: dict[str, Any] = {
    "textAlign": "center",
    "color": "#202124",
    "marginBottom": "28px",
    "fontWeight": "700",
}

TABLE_STYLE: dict[str, Any] = {
    "width": "100%",
    "borderCollapse": "collapse",
    "fontSize": "14px",
}

TH_STYLE: dict[str, Any] = {
    "padding": "10px 14px",
    "backgroundColor": "#e8eaed",
    "textAlign": "left",
    "fontWeight": "600",
    "borderBottom": "2px solid #dadce0",
}

TD_STYLE: dict[str, Any] = {
    "padding": "9px 14px",
    "borderBottom": "1px solid #dadce0",
    "color": "#3c4043",
}

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="Taxonomy Browser",
)
server = app.server

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content"),
])


def build_landing_page():
    return html.Div(style=PAGE_STYLE, children=[
        HOME_LINK,
        html.H1("NCBI Taxonomy Search", style=H1_STYLE),
        dcc.Input(
            id="search-keyword",
            type="text",
            placeholder="Enter search keyword",
            debounce=False,
            style={
                "width": "100%",
                "padding": "12px 14px",
                "fontSize": "15px",
                "border": "1px solid #dadce0",
                "borderRadius": "6px",
                "boxSizing": "border-box",
                "marginBottom": "12px",
                "outline": "none",
            },
        ),
        dcc.Dropdown(
            id="search-mode",
            options=[
                {"label": "Contains", "value": "contains"},
                {"label": "Starts with", "value": "starts_with"},
                {"label": "Ends with", "value": "ends_with"},
            ],
            value="contains",
            clearable=False,
            style={
                "marginBottom": "16px",
                "fontSize": "15px",
            },
        ),
        html.Button(
            "Search",
            id="search-button",
            n_clicks=0,
            style={
                "backgroundColor": "#1a73e8",
                "color": "white",
                "border": "none",
                "padding": "11px 24px",
                "fontSize": "15px",
                "borderRadius": "6px",
                "cursor": "pointer",
                "fontWeight": "600",
            },
        ),
        dcc.Location(id="redirect", refresh=True),
    ])


def build_results_page(keyword, mode, page):
    try:
        resp = requests.get(
            f"{API_BASE}/search",
            params={"keyword": keyword, "mode": mode, "page": page, "per_page": PER_PAGE},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return html.Div(style=PAGE_STYLE, children=[
            HOME_LINK,
            html.P(f"Error contacting API: {exc}", style={"color": "red", "marginTop": "20px"}),
        ])

    results = data.get("results", [])
    total = data.get("total", 0)
    current_page = data.get("page", page)
    total_pages = max(1, -(-total // PER_PAGE))

    rows = []
    for item in results:
        tid = item["taxon_id"]
        back_qs = urllib.parse.urlencode({"keyword": keyword, "mode": mode, "page": current_page})
        rows.append(html.Tr([
            html.Td(
                html.A(str(tid), href=f"/taxon?tax_id={tid}&back={urllib.parse.quote(back_qs)}", style=LINK_STYLE),
                style=TD_STYLE,
            ),
            html.Td(item["name_txt"], style=TD_STYLE),
            html.Td(item["name_class"], style=TD_STYLE),
        ]))

    qs_prev = urllib.parse.urlencode({"keyword": keyword, "mode": mode, "page": current_page - 1})
    qs_next = urllib.parse.urlencode({"keyword": keyword, "mode": mode, "page": current_page + 1})

    pagination = html.Div(
        style={"display": "flex", "justifyContent": "space-between", "marginTop": "14px"},
        children=[
            html.A("← Previous", href=f"/search?{qs_prev}",
                   style={**LINK_STYLE, "visibility": "visible" if current_page > 1 else "hidden"}),
            html.Span(
                f"Total results: {total} | Page: {current_page}",
                style={"color": "#5f6368", "fontSize": "13px", "alignSelf": "center"},
            ),
            html.A("Next →", href=f"/search?{qs_next}",
                   style={**LINK_STYLE, "visibility": "visible" if current_page < total_pages else "hidden"}),
        ]
    )

    mode_label = {"contains": "contains", "starts_with": "starts with", "ends_with": "ends with"}.get(mode, mode)

    return html.Div(style=PAGE_STYLE, children=[
        HOME_LINK,
        html.H1(f"Search Results for '{keyword}' ({mode_label})", style=H1_STYLE),
        html.Table(style=TABLE_STYLE, children=[
            html.Thead(html.Tr([
                html.Th("Taxonomy ID", style={**TH_STYLE, "width": "18%"}),
                html.Th("Name", style={**TH_STYLE, "width": "48%"}),
                html.Th("Class", style=TH_STYLE),
            ])),
            html.Tbody(rows if rows else [
                html.Tr(html.Td("No results found.", colSpan=3,
                                style={**TD_STYLE, "textAlign": "center", "color": "#9aa0a6"}))
            ]),
        ]),
        pagination,
    ])


def build_taxon_page(tax_id, back_qs):
    try:
        resp = requests.get(f"{API_BASE}/taxa", params={"tax_id": tax_id}, timeout=10)
        if resp.status_code == 404:
            return html.Div(style=PAGE_STYLE, children=[
                HOME_LINK,
                html.H2(f"Taxon {tax_id} not found.", style={"color": "#d93025", "marginTop": "20px"}),
            ])
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return html.Div(style=PAGE_STYLE, children=[
            HOME_LINK,
            html.P(f"Error contacting API: {exc}", style={"color": "red", "marginTop": "20px"}),
        ])

    parent = data.get("parent")
    if parent:
        p_sci = parent.get("scientific_name") or f"taxon {parent['taxon_id']}"
        parent_el = html.Span([
            "Parent: ",
            html.A(
                f"{p_sci} ({parent['taxon_id']})",
                href=f"/taxon?tax_id={parent['taxon_id']}&back={urllib.parse.quote(back_qs)}",
                style=LINK_STYLE,
            ),
        ], style={"fontSize": "15px", "display": "block", "marginBottom": "10px"})
    else:
        parent_el = html.Span("Parent: (root)",
                              style={"fontSize": "15px", "display": "block", "marginBottom": "10px"})

    child_rows = []
    for c in data.get("children", []):
        c_name = c.get("scientific_name") or f"taxon {c['taxon_id']}"
        child_rows.append(html.Tr([
            html.Td(
                html.A(f"{c_name} ({c['taxon_id']})",
                       href=f"/taxon?tax_id={c['taxon_id']}&back={urllib.parse.quote(back_qs)}",
                       style=LINK_STYLE),
                style=TD_STYLE,
            ),
            html.Td(c["rank"], style=TD_STYLE),
        ]))

    children_section = html.Div([
        html.H2("Children", style={"color": "#202124", "fontWeight": "700", "marginTop": "24px"}),
        html.Table(style=TABLE_STYLE, children=[
            html.Thead(html.Tr([
                html.Th("Child Taxon", style={**TH_STYLE, "width": "75%"}),
                html.Th("Rank", style=TH_STYLE),
            ])),
            html.Tbody(child_rows if child_rows else [
                html.Tr(html.Td("No children.", colSpan=2,
                                style={**TD_STYLE, "textAlign": "center", "color": "#9aa0a6"}))
            ]),
        ]),
    ])

    name_rows = [
        html.Tr([
            html.Td(n["name_txt"], style=TD_STYLE),
            html.Td(n["name_class"], style=TD_STYLE),
        ])
        for n in data.get("names", [])
    ]

    names_section = html.Div([
        html.H2("Names", style={"color": "#202124", "fontWeight": "700", "marginTop": "24px"}),
        html.Table(style=TABLE_STYLE, children=[
            html.Thead(html.Tr([
                html.Th("Name", style={**TH_STYLE, "width": "50%"}),
                html.Th("Class", style=TH_STYLE),
            ])),
            html.Tbody(name_rows if name_rows else [
                html.Tr(html.Td("No names.", colSpan=2,
                                style={**TD_STYLE, "textAlign": "center", "color": "#9aa0a6"}))
            ]),
        ]),
    ])

    back_href = f"/search?{back_qs}" if back_qs else "/"
    back_link = html.Div(
        html.A("← Back to Search Results", href=back_href, style=LINK_STYLE),
        style={"textAlign": "center", "marginTop": "24px", "fontSize": "14px"},
    )

    return html.Div(style=PAGE_STYLE, children=[
        HOME_LINK,
        html.H1(f"Taxon Details: {tax_id}", style=H1_STYLE),
        html.P(f"Rank: {data['rank']}", style={"fontSize": "15px", "marginBottom": "6px"}),
        parent_el,
        children_section,
        names_section,
        back_link,
    ])


@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    Input("url", "search"),
)
def display_page(pathname, search):
    params = urllib.parse.parse_qs((search or "").lstrip("?"))

    def first(key, default=""):
        return params.get(key, [default])[0]

    if pathname in ("/", ""):
        return build_landing_page()
    if pathname == "/search":
        keyword = first("keyword")
        mode = first("mode", "contains")
        page = int(first("page", "1"))
        if not keyword:
            return build_landing_page()
        return build_results_page(keyword, mode, page)
    if pathname == "/taxon":
        tax_id_str = first("tax_id")
        back_qs = first("back", "")
        if not tax_id_str.isdigit():
            return html.Div(style=PAGE_STYLE, children=[HOME_LINK, html.P("Invalid taxon ID.")])
        return build_taxon_page(int(tax_id_str), urllib.parse.unquote(back_qs))

    return html.Div(style=PAGE_STYLE, children=[HOME_LINK, html.P(f"Page '{pathname}' not found.")])


@app.callback(
    Output("redirect", "href"),
    Input("search-button", "n_clicks"),
    State("search-keyword", "value"),
    State("search-mode", "value"),
    prevent_initial_call=True,
)
def on_search_click(n_clicks, keyword, mode):
    if not keyword or not keyword.strip():
        return no_update
    qs = urllib.parse.urlencode({"keyword": keyword.strip(), "mode": mode, "page": 1})
    return f"/search?{qs}"


if __name__ == "__main__":
    app.run(debug=True, port=8050)