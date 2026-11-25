'use strict';

const language = document.documentElement.lang;
const japanese = language === 'ja';
const { answers, themes } = JSON.parse(document.getElementById('db').textContent);
const labels = japanese ? {} : JSON.parse(document.getElementById('labels').textContent);
const copy = japanese ? {
    periods: '現状・先行き',
    sectors: 'すべての分野',
    industries: 'すべての業種・職種',
    themes: '全テーマ（テーマなしを含む）',
    empty: '該当する回答はありません。',
    page: 'ページ ',
    groups: '組が該当',
} : {
    periods: 'Both sections',
    sectors: 'All sectors',
    industries: 'All industries',
    themes: 'All themes (including untagged responses)',
    empty: 'No matching responses.',
    page: 'Page ',
    groups: ' matching groups',
};
const byId = id => document.getElementById(id);
const value = id => byId(id).value;
const englishId = id => id.replace(/^現状-/, 'Current-').replace(/^先行き-/, 'Outlook-');
const displayId = japanese ? id => id : englishId;
const pageSize = 25;
let page = 0;

function inGroup(response, period, sector, industry) {
    return (!period || response.k === period)
        && (!sector || response.s === sector)
        && (!industry || response.b === industry);
}

function matches(response, theme, query) {
    const matchesTheme = !theme || response.ev.some(evidence => evidence[0] === theme);
    const matchesQuery = !query || response.id.includes(query) || response.text.includes(query)
        || (!japanese && englishId(response.id).toLowerCase().includes(query.toLowerCase()));
    return matchesTheme && matchesQuery;
}

function setOptions(id, values, caption, names = {}) {
    const select = byId(id);
    const previous = select.value;
    const label = key => names[key] || key;
    const unique = [...new Set(values)].sort((a, b) => label(a).localeCompare(label(b), language));
    select.replaceChildren(new Option(caption, ''));
    for (const key of unique) select.add(new Option(label(key), key));
    if (values.includes(previous)) select.value = previous;
}

function updateSectors() {
    const available = answers.filter(row => inGroup(row, value('k'), '', ''));
    setOptions('s', available.map(row => row.s), copy.sectors, labels.sectors);
}

function updateIndustries() {
    const available = answers.filter(row => inGroup(row, value('k'), value('s'), ''));
    setOptions('b', available.map(row => row.b), copy.industries, labels.industries);
}

function render() {
    const base = answers.filter(row => inGroup(row, value('k'), value('s'), value('b')));
    const theme = value('t');
    const query = value('q').trim();
    const filtered = base.filter(row => matches(row, theme, query));
    const count = filtered.length;
    const ratio = (base.length ? 100 * count / base.length : 0).toFixed(1);
    byId('result').textContent = japanese
        ? `${count} / ${base.length}件（${ratio}%）`
        : `${count} / ${base.length} responses (${ratio}%)`;

    const list = byId('list');
    const visible = filtered.slice(page * pageSize, (page + 1) * pageSize);
    list.replaceChildren(...visible.map(row => responseDetail(row, theme, japanese, labels, englishId)));
    if (!count) {
        const empty = document.createElement('p');
        empty.textContent = copy.empty;
        list.append(empty);
    }
    byId('prev').disabled = page === 0;
    byId('next').disabled = (page + 1) * pageSize >= count;
    byId('page').textContent = count ? `${copy.page}${page + 1} / ${Math.ceil(count / pageSize)}` : '';
}

function resetPage() {
    page = 0;
    render();
}

function selectGroup(period, sector, industry, theme, id = '') {
    byId('k').value = period;
    updateSectors();
    byId('s').value = sector;
    updateIndustries();
    byId('b').value = industry;
    byId('t').value = theme;
    byId('q').value = id ? displayId(id) : '';
    resetPage();
    if (id) {
        const response = byId('list').querySelector('details');
        if (response) response.open = true;
    }
}

function showExplorer() {
    location.hash = 'explorer';
    const explorer = byId('explorer');
    explorer.focus({ preventScroll: true });
    explorer.scrollIntoView();
}

setOptions('k', ['現状', '先行き'], copy.periods, labels.periods);
updateSectors();
updateIndustries();
setOptions('t', themes, copy.themes, labels.themes);

byId('k').addEventListener('change', () => {
    updateSectors();
    updateIndustries();
    resetPage();
});
byId('s').addEventListener('change', () => {
    updateIndustries();
    resetPage();
});
for (const id of ['b', 't']) byId(id).addEventListener('change', resetPage);
byId('q').addEventListener('input', resetPage);
byId('clear').addEventListener('click', () => selectGroup('', '', '', ''));
for (const [id, step] of [['prev', -1], ['next', 1]]) {
    byId(id).addEventListener('click', () => {
        page += step;
        render();
        byId('result').scrollIntoView();
    });
}

const presets = [
    ['現状', '家計動向関連', 'スーパー', '売上・業績・集客'],
    ['現状', '雇用関連', '人材派遣会社', '人手不足・採用・求人'],
    ['先行き', '家計動向関連', '乗用車販売店', '商品・サービス・在庫'],
];
for (const button of document.querySelectorAll('.preset')) {
    button.addEventListener('click', () => {
        selectGroup(...presets[button.dataset.i]);
        showExplorer();
    });
}

byId('survey-report').addEventListener('click', event => {
    const button = event.target.closest('button[data-filter]');
    if (!button) return;
    selectGroup(...JSON.parse(button.dataset.filter));
    showExplorer();
});

const industryQuery = byId('industry-query');
const panels = [...document.querySelectorAll('.sector-panel')];
const priorOpen = new Map();
const normalize = text => text.normalize('NFKC').toLowerCase();

industryQuery.addEventListener('input', () => {
    const query = normalize(industryQuery.value).trim();
    let count = 0;
    for (const panel of panels) {
        let hits = 0;
        for (const row of panel.querySelectorAll('.industry')) {
            const localized = japanese ? '' : row.querySelector('summary').textContent;
            row.hidden = !normalize(row.dataset.name).includes(query) && !normalize(localized).includes(query);
            hits += Number(!row.hidden);
        }
        count += hits;
        if (query) {
            if (!priorOpen.has(panel)) priorOpen.set(panel, panel.open);
            panel.hidden = !hits;
            panel.open = Boolean(hits);
        } else {
            panel.hidden = false;
            if (priorOpen.has(panel)) panel.open = priorOpen.get(panel);
        }
    }
    if (!query) priorOpen.clear();
    byId('industry-count').textContent = query
        ? new Intl.NumberFormat(language).format(count) + copy.groups
        : '';
});

render();
