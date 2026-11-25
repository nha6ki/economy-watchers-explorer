# Economy Watchers · Industry Evidence Explorer

This bilingual static site explores the reasons given in Japan’s October 2026 Economy Watchers Survey. It contains 2,513 published responses, six period/sector groups, 412 industry/occupation groups and 618 model-generated findings. The explorer filters comments by period, sector, industry, theme, response ID or Japanese text. Findings link to their Japanese source responses. Select an extracted topic to highlight its evidence in the original response.

## Build and run

Use Python 3.10 or newer. The site build has no third-party dependencies, API keys, model downloads or network calls. Node.js is not needed.

```sh
python3 scripts/build.py
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist
```

Open <http://127.0.0.1:8000/> for English or <http://127.0.0.1:8000/ja.html> for Japanese. The generated `dist/` directory contains the complete static site. All its asset paths are relative, including the language switch and workbook download, so it can also be served below a repository path on GitHub Pages.

## Verify

Run the standard-library checks for the data, build, packaged workbook and output escaping:

```sh
python3 -m unittest discover -s tests -v
```

For an optional Chromium smoke test, use a virtual environment and install the pinned development dependency:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python tests/check_browser.py
```

If Chromium is already installed, set `CHROMIUM_PATH` to its executable path to skip the browser download. The smoke test starts and stops its own loopback server.

## Repository layout

| Path | Purpose |
|---|---|
| `src/en.html`, `src/ja.html` | Editable page copy, examples and markup for the two languages |
| `src/assets/` | Shared search, response detail and styling |
| `data/responses.json` | Public responses, theme keys and topic-evidence triples |
| `data/findings.json` | Displayed bilingual findings and source response IDs with character offsets |
| `data/labels.en.json` | English display names for periods, sectors, industries, regions, themes and assessments |
| `data/all-industry-themes.xlsx` | Japanese workbook distributed by the demo |
| `scripts/build.py` | Renders the industry panels and assembles the static files |
| `tests/` | Data/build checks and optional browser smoke test |

Edit the templates, assets or publication data, then rebuild. `dist/` is generated and ignored by Git. The Pages workflow publishes only this directory.

## Publish with GitHub Pages

Push the source to the repository's `main` branch. In **Settings → Pages**, set the publishing source to **GitHub Actions**. On the **Actions** tab, choose **Deploy to GitHub Pages** and run it on `main`. The workflow runs the standard-library tests, builds the site, and publishes `dist/`. Deployments are manual. Run the same workflow after a change you want to publish.

## Data and reproducibility

The packaged files are the publication snapshot for October 2026. The build derives industry counts from response IDs, counting each response once per theme. The survey's own assessments and the model's classifications are separate fields. Japanese IDs are canonical. English IDs are display aliases. An empty evidence span list means the whole displayed response is the evidence. Non-empty spans are zero-based start-inclusive, end-exclusive character offsets in the stored Japanese response.

The snapshot was prepared using Gemma 4 12B (QAT) in local Ollama (`gemma4:12b-it-qat`). The repository reproduces the website and its counts using those saved outputs. Regenerating the model outputs or updating the dataset for another month requires the original analysis workflow. The summaries and translations were not exhaustively reviewed for meaning. The source comments are available in the interface to support comparison.

Source data: [Economy Watchers Survey, October 2026](https://www5.cao.go.jp/keizai3/2026/1110watcher/menu.html), Cabinet Office, Government of Japan. The Economy Watchers · Industry Evidence Explorer project compiled the results and added classifications and summaries. See the [Cabinet Office terms](https://www.cao.go.jp/notice/rule.html) and the [Public Data License 1.0](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0) for source-data reuse. These terms refer to the source data. No separate license for this repository’s code has been specified.

## 日本語

内閣府の令和8年10月景気ウォッチャー調査の公表回答を、現状・先行き、分野、業種・職種、テーマで閲覧できます。`python3 scripts/build.py` で日英ページを生成します。公開済みのモデル出力を使うため、サイトを再生成する際に Ollama やモデルのインストールは不要です。
