#!/usr/bin/python3
# -*- coding: utf-8 -*-
import html
import io

from book import Book


def _pct(cnt: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{cnt / total * 100:.1f}%"


def _genre_label(genre):
    return genre if genre else "(без жанра)"


def report_txt(total: int,
               genre_rows: list[tuple[str | None, int]],
               author_rows: list[tuple[str, int]],
               generated_at: str) -> str:
    lines = []
    lines.append("        Домашняя библиотека — отчёт")
    lines.append(f"        Сформирован: {generated_at}")
    lines.append(f"        Всего книг: {total}")
    lines.append("")
    lines.append("=" * 50)
    lines.append("По жанрам".center(50))
    lines.append("=" * 50)
    if not genre_rows:
        lines.append("(нет данных)".center(50))
    else:
        for genre, cnt in genre_rows:
            line = f"{_genre_label(genre)}: {cnt} ({_pct(cnt, total)})"
            lines.append(line)
    lines.append("")
    lines.append("=" * 50)
    lines.append("По авторам".center(50))
    lines.append("=" * 50)
    if not author_rows:
        lines.append("(нет данных)".center(50))
    else:
        for author, cnt in author_rows:
            line = f"{author}: {cnt} ({_pct(cnt, total)})"
            lines.append(line)
    lines.append("")
    return "\n".join(lines)


def report_html(total: int,
                genre_rows: list[tuple[str | None, int]],
                author_rows: list[tuple[str, int]],
                generated_at: str) -> str:
    def esc(s) -> str:
        return html.escape(s) if s is not None else ""

    rows_genre = "".join(
        f"<tr><td>{esc(_genre_label(g))}</td>"
        f"<td class='num'>{c}</td><td class='num'>{_pct(c, total)}</td></tr>"
        for g, c in genre_rows
    ) or '<tr><td colspan="3" class="empty">(нет данных)</td></tr>'
    rows_author = "".join(
        f"<tr><td>{esc(a)}</td>"
        f"<td class='num'>{c}</td><td class='num'>{_pct(c, total)}</td></tr>"
        for a, c in author_rows
    ) or '<tr><td colspan="3" class="empty">(нет данных)</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Домашняя библиотека — отчёт</title>
<style>
  :root {{
    --wood-dark:  #2b1a10;
    --wood:       #4a2e1b;
    --wood-light: #6b4426;
    --gold:       #c9a227;
    --gold-light: #e6c453;
    --parchment:  #f3e7c9;
    --parchment-2:#ebdcb9;
    --ink:        #2a1e12;
    --leather:    #5a1e1e;
    --leather-2:  #7a2a2a;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 2em 1em;
    font-family: Georgia, "Times New Roman", "PT Serif", serif;
    color: var(--ink);
    background:
      radial-gradient(ellipse at top, rgba(201, 162, 39, 0.10) 0%, transparent 60%),
      repeating-linear-gradient(
        90deg,
        var(--wood-dark) 0px,
        var(--wood) 18px,
        var(--wood-light) 22px,
        var(--wood) 26px,
        var(--wood-dark) 44px
      );
    background-attachment: fixed;
    min-height: 100vh;
    text-align: center;
  }}
  .card {{
    max-width: 820px;
    margin: 0 auto;
    background: linear-gradient(180deg, var(--parchment) 0%, var(--parchment-2) 100%);
    border: 1px solid var(--gold);
    outline: 6px double var(--gold);
    outline-offset: -12px;
    border-radius: 4px;
    box-shadow: 0 14px 40px rgba(0, 0, 0, 0.55);
    padding: 2.4em 2.8em;
  }}
  h1 {{
    margin: 0 0 0.2em 0;
    font-size: 2em;
    letter-spacing: 0.08em;
    color: var(--leather);
    text-transform: uppercase;
    font-variant: small-caps;
  }}
  h1::before, h1::after {{
    content: "❦";
    color: var(--gold);
    margin: 0 0.5em;
    font-size: 0.75em;
    vertical-align: middle;
  }}
  .subtitle {{
    margin: 0 0 1.8em 0;
    color: #5a4a35;
    font-style: italic;
    font-size: 1em;
  }}
  h2 {{
    margin: 1.8em 0 0.7em 0;
    font-size: 1.15em;
    color: var(--leather);
    font-variant: small-caps;
    letter-spacing: 0.1em;
    border-bottom: 1px solid var(--gold);
    padding-bottom: 0.35em;
    text-align: center;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0 auto 1em auto;
    background: rgba(255, 255, 255, 0.35);
  }}
  th {{
    background: linear-gradient(180deg, var(--leather-2) 0%, var(--leather) 100%);
    color: var(--gold-light);
    padding: 0.7em 0.9em;
    text-align: center;
    font-weight: 600;
    font-variant: small-caps;
    letter-spacing: 0.06em;
    border-bottom: 2px solid var(--gold);
  }}
  td {{
    padding: 0.55em 0.9em;
    border-bottom: 1px solid rgba(122, 42, 42, 0.25);
    text-align: center;
    color: var(--ink);
  }}
  td.num {{ font-variant-numeric: tabular-nums; color: var(--leather); }}
  tr:nth-child(even) td {{ background: rgba(235, 220, 185, 0.65); }}
  tr:nth-child(odd)  td {{ background: rgba(255, 255, 255, 0.35); }}
  tr:hover td {{ background: rgba(201, 162, 39, 0.18); transition: background 0.15s; }}
  td.empty {{ color: #6a5a45; font-style: italic; }}
  footer {{
    margin-top: 1.8em;
    padding-top: 0.9em;
    border-top: 1px solid rgba(201, 162, 39, 0.5);
    font-size: 0.85em;
    color: #5a4a35;
    font-style: italic;
  }}
  @media (max-width: 520px) {{
    body {{ padding: 1em 0.5em; }}
    .card {{ padding: 1.2em 1em; outline-offset: -8px; }}
    h1 {{ font-size: 1.4em; }}
    th, td {{ padding: 0.4em 0.5em; font-size: 0.9em; }}
  }}
</style>
</head>
<body>
  <main class="card">
    <h1>Домашняя библиотека</h1>
    <p class="subtitle">Отчёт · сформирован {esc(generated_at)} · всего книг: {total}</p>

    <h2>По жанрам</h2>
    <table>
      <tr><th>Жанр</th><th>Количество</th><th>Доля</th></tr>
      {rows_genre}
    </table>

    <h2>По авторам</h2>
    <table>
      <tr><th>Автор</th><th>Количество</th><th>Доля</th></tr>
      {rows_author}
    </table>

    <footer>Сгенерировано Домашняя библиотека · {esc(generated_at)}</footer>
  </main>
</body>
</html>
"""

def dump_txt(books: list[Book], generated_at: str) -> str:
    lines = []
    lines.append("        Домашняя библиотека — выгрузка БД")
    lines.append(f"        Сформирован: {generated_at}")
    lines.append(f"        Всего книг: {len(books)}")
    lines.append("")
    header = " | ".join(["id", "Автор", "Фамилия", "Имя", "Отчество",
                         "Название", "Год", "Жанр", "Город", "Издание"])
    sep = "=" * len(header)
    lines.append(sep)
    lines.append(header)
    lines.append(sep)
    for b in books:
        row = [
            str(b.id) if b.id is not None else "—",
            b.author,
            b.last_name,
            b.first_name or "—",
            b.middle_name or "—",
            b.title,
            str(b.year) if b.year is not None else "—",
            b.genre or "—",
            b.city or "—",
            b.publisher or "—",
        ]
        lines.append(" | ".join(row))
    lines.append("")
    return "\n".join(lines)


def dump_html(books: list[Book], generated_at: str) -> str:
    def esc(s) -> str:
        return html.escape(str(s)) if s is not None else ""

    def cell(v) -> str:
        if v is None:
            return '<td class="empty">—</td>'
        return f"<td>{esc(v)}</td>"

    rows = "".join(
        "<tr>"
        f"{cell(b.id)}"
        f"<td>{esc(b.author)}</td>"
        f"<td>{esc(b.last_name)}</td>"
        f"{cell(b.first_name)}"
        f"{cell(b.middle_name)}"
        f"<td>{esc(b.title)}</td>"
        f"{cell(b.year)}"
        f"{cell(b.genre)}"
        f"{cell(b.city)}"
        f"{cell(b.publisher)}"
        "</tr>"
        for b in books
    ) or '<tr><td colspan="10" class="empty">(нет книг)</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Домашняя библиотека — выгрузка БД</title>
<style>
  :root {{
    --wood-dark:  #2b1a10;
    --wood:       #4a2e1b;
    --wood-light: #6b4426;
    --gold:       #c9a227;
    --gold-light: #e6c453;
    --parchment:  #f3e7c9;
    --parchment-2:#ebdcb9;
    --ink:        #2a1e12;
    --leather:    #5a1e1e;
    --leather-2:  #7a2a2a;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 2em 1em;
    font-family: Georgia, "Times New Roman", "PT Serif", serif;
    color: var(--ink);
    background:
      radial-gradient(ellipse at top, rgba(201, 162, 39, 0.10) 0%, transparent 60%),
      repeating-linear-gradient(
        90deg,
        var(--wood-dark) 0px,
        var(--wood) 18px,
        var(--wood-light) 22px,
        var(--wood) 26px,
        var(--wood-dark) 44px
      );
    background-attachment: fixed;
    min-height: 100vh;
    text-align: center;
  }}
  .card {{
    max-width: 1400px;
    margin: 0 auto;
    background: linear-gradient(180deg, var(--parchment) 0%, var(--parchment-2) 100%);
    border: 1px solid var(--gold);
    outline: 6px double var(--gold);
    outline-offset: -12px;
    border-radius: 4px;
    box-shadow: 0 14px 40px rgba(0, 0, 0, 0.55);
    padding: 2em 1.5em;
  }}
  .table-wrap {{
    overflow-x: auto;
    margin: 0 auto 1em auto;
    -webkit-overflow-scrolling: touch;
  }}
  h1 {{
    margin: 0 0 0.2em 0;
    font-size: 2em;
    letter-spacing: 0.08em;
    color: var(--leather);
    text-transform: uppercase;
    font-variant: small-caps;
  }}
  h1::before, h1::after {{
    content: "❦";
    color: var(--gold);
    margin: 0 0.5em;
    font-size: 0.75em;
    vertical-align: middle;
  }}
  .subtitle {{
    margin: 0 0 1.8em 0;
    color: #5a4a35;
    font-style: italic;
    font-size: 1em;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0 auto 1em auto;
    background: rgba(255, 255, 255, 0.35);
  }}
  th {{
    background: linear-gradient(180deg, var(--leather-2) 0%, var(--leather) 100%);
    color: var(--gold-light);
    padding: 0.6em 0.7em;
    text-align: center;
    font-weight: 600;
    font-variant: small-caps;
    letter-spacing: 0.06em;
    border-bottom: 2px solid var(--gold);
  }}
  td {{
    padding: 0.45em 0.7em;
    border-bottom: 1px solid rgba(122, 42, 42, 0.25);
    text-align: left;
    color: var(--ink);
    font-size: 0.95em;
  }}
  tr:nth-child(even) td {{ background: rgba(235, 220, 185, 0.65); }}
  tr:nth-child(odd)  td {{ background: rgba(255, 255, 255, 0.35); }}
  tr:hover td {{ background: rgba(201, 162, 39, 0.18); transition: background 0.15s; }}
  td.empty {{ color: #6a5a45; font-style: italic; text-align: center; }}
  footer {{
    margin-top: 1.8em;
    padding-top: 0.9em;
    border-top: 1px solid rgba(201, 162, 39, 0.5);
    font-size: 0.85em;
    color: #5a4a35;
    font-style: italic;
  }}
  @media (max-width: 700px) {{
    body {{ padding: 1em 0.5em; }}
    .card {{ padding: 1.2em 1em; outline-offset: -8px; }}
    h1 {{ font-size: 1.4em; }}
    th, td {{ padding: 0.4em 0.5em; font-size: 0.85em; }}
  }}
</style>
</head>
<body>
  <main class="card">
    <h1>Домашняя библиотека</h1>
    <p class="subtitle">Выгрузка БД · сформирована {esc(generated_at)} · всего книг: {len(books)}</p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>id</th><th>Автор</th><th>Фамилия</th><th>Имя</th><th>Отчество</th>
            <th>Название</th><th>Год</th><th>Жанр</th><th>Город</th><th>Издание</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>

    <footer>Сгенерировано Домашняя библиотека · {esc(generated_at)}</footer>
  </main>
</body>
</html>
"""
