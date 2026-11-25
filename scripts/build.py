"""Build the bilingual static site from its versioned publication snapshot."""

from collections import Counter, defaultdict
from html import escape
import json
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SOURCE = ROOT / "src"
OUTPUT = ROOT / "dist"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def remove_source_marker(text):
    """Hide the survey's opening bullet without changing the stored response."""
    stripped = text.lstrip()
    return stripped[1:].lstrip(" \t\u3000") if stripped.startswith("・") else text


def display_id(response_id, language):
    if language == "ja":
        return response_id
    period, number = response_id.split("-", 1)
    return f"{ {'現状': 'Current', '先行き': 'Outlook'}[period]}-{number}"


def evidence_excerpt(text, spans):
    """Escape all text and highlight the selected offsets in the full response."""
    display = remove_source_marker(text)
    first = len(text) - len(display)
    if not spans:
        return escape(display)
    fragments = []
    cursor = first
    for left, right in spans:
        left = max(left, first)
        if not cursor <= left < right <= len(text):
            raise ValueError("Invalid evidence offsets")
        fragments.extend([
            escape(text[cursor:left]),
            f"<mark>{escape(text[left:right])}</mark>",
        ])
        cursor = right
    fragments.append(escape(text[cursor:]))
    return "".join(fragments)


def render_findings(findings, responses, language):
    japanese = language == "ja"
    heading = "Gemmaによる業種要約" if japanese else "Industry findings by Gemma"
    link = "根拠を読む" if japanese else "Read the evidence"
    output = [f'<div class="gemma-findings"><h4>{heading}</h4>']
    for finding in findings:
        output.append(f'<div class="gemma-finding"><p>{escape(finding[language])}</p>')
        output.append(f"<details><summary>{link}</summary>")
        for ref in finding["evidence"]:
            response_id = ref["id"]
            excerpt = evidence_excerpt(responses[response_id]["text"], ref["spans"])
            output.append(
                '<div class="evidence-row" lang="ja">'
                f"<strong>{escape(display_id(response_id, language))}</strong><p>{excerpt}</p></div>"
            )
        output.append("</details></div>")
    output.append("</div>")
    return "".join(output)


def drill_button(period, sector, industry, theme, label):
    data_filter = escape(json.dumps([period, sector, industry, theme, ""], ensure_ascii=False), quote=True)
    return f'<button class="drill" data-filter="{data_filter}">{escape(label)}</button>'


def render_group(period, sector, industry, rows, language, labels, findings=""):
    japanese = language == "ja"
    count = len(rows)
    judgments = Counter(row["jud"] for row in rows)
    better = judgments["◎"] + judgments["○"]
    same = judgments["□"]
    worse = judgments["▲"] + judgments["×"]
    themes = Counter(theme for row in rows for theme in {e[0] for e in row["ev"]})
    kind = "industry" if industry else "sector-panel"
    if japanese:
        name = industry if industry else f"{period}｜{sector}"
        title = f"{name}（{count:,}件）"
        description = f"{count:,}件のうち、改善が{better}件、変わらないが{same}件、悪化が{worse}件。"
        all_label = f"全{count}件の回答を見る"
        theme_title = "テーマ別回答数" if themes else "テーマが付いた回答はありません。"
    else:
        name = labels["industries"][industry] if industry else f"{labels['periods'][period]} · {labels['sectors'][sector]}"
        title = f"{name} ({count:,})" if industry else f"{name} ({count:,} responses)"
        verb = "reported" if period == "現状" else "expected"
        description = f"Of {count:,} responses, {better} {verb} improvement, {same} no change and {worse} deterioration."
        all_label = f"All {count} responses"
        theme_title = "Gemma themes by response count" if themes else "No theme was recorded for this group."

    attrs = ""
    if industry:
        attrs = f' data-name="{escape(industry, quote=True)}"'
    buttons = [drill_button(period, sector, industry, "", all_label), f"<p>{theme_title}</p>"]
    for theme, total in sorted(themes.items(), key=lambda item: (-item[1], item[0])):
        label = f"{theme}（{total}件）" if japanese else f"{labels['themes'][theme]} ({total})"
        buttons.append(drill_button(period, sector, industry, theme, label))
    return (
        f'<details class="{kind}"{attrs}><summary>{escape(title)}</summary>'
        f"<p>{escape(description)}</p>{findings}{''.join(buttons)}"
    )


def render_panels(sectors, responses, language, labels):
    grouped = defaultdict(list)
    for row in responses.values():
        grouped[row["k"], row["s"], ""].append(row)
        grouped[row["k"], row["s"], row["b"]].append(row)
    output = ['<div class="industry-panels">']
    for group in sectors:
        period, sector = group["period"], group["sector"]
        output.append(render_group(period, sector, "", grouped[period, sector, ""], language, labels))
        for industry in group["industries"]:
            name = industry["name"]
            findings = render_findings(industry["findings"], responses, language)
            output.append(render_group(period, sector, name, grouped[period, sector, name], language, labels, findings))
            output.append("</details>")
        output.append("</details>")
    output.append("</div>")
    return "\n".join(output)


def json_script(element_id, value):
    # The HTML parser recognizes a closing script tag even inside a JSON string.
    content = json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return f'<script id="{element_id}" type="application/json">{content}</script>'


def build():
    data = load("responses.json")
    labels = load("labels.en.json")
    sectors = load("findings.json")
    responses = {row["id"]: row for row in data["answers"]}
    if len(responses) != len(data["answers"]):
        raise ValueError("Duplicate response ID")

    OUTPUT.mkdir(exist_ok=True)
    for name in ("survey.css", "response-detail.js", "explorer.js"):
        copy2(SOURCE / "assets" / name, OUTPUT / name)
    copy2(DATA / "all-industry-themes.xlsx", OUTPUT / "all-industry-themes.xlsx")

    for lang, target in (("en", "index.html"), ("ja", "ja.html")):
        scripts = [json_script("db", data)]
        if lang == "en":
            scripts.append(json_script("labels", labels))
        scripts.extend([
            '<script src="response-detail.js" defer></script>',
            '<script src="explorer.js" defer></script>',
        ])
        page = (SOURCE / f"{lang}.html").read_text(encoding="utf-8")
        for slot, content in (
            ("<!-- INDUSTRY_PANELS -->", render_panels(sectors, responses, lang, labels)),
            ("<!-- APP_SCRIPTS -->", "\n".join(scripts)),
        ):
            if page.count(slot) != 1:
                raise ValueError(f"Expected one {slot} in {lang}.html")
            page = page.replace(slot, content, 1)
        (OUTPUT / target).write_text(page, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build()
