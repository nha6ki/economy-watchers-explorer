function responseDetail(response, activeTheme, japanese, labels, englishId) {
    const make = (tag, text, className) => {
        const element = document.createElement(tag);
        element.textContent = text;
        if (className) element.className = className;
        return element;
    };

    const detail = make('details', '');
    const heading = make('summary', '');
    const displayId = japanese ? response.id : englishId(response.id);
    const industry = japanese ? response.b : labels.industries[response.b];
    const region = japanese ? response.region : labels.regions[response.region];
    heading.append(make('strong', displayId), make('span', [industry, region].filter(Boolean).join(' · ')));
    if (japanese) heading.lang = 'ja';
    detail.append(heading);

    const body = make('div', '', 'response-body');
    body.lang = japanese ? 'ja' : 'en';
    const metadata = make('dl', '', 'response-facts');
    const facts = [[japanese ? '景気判断' : 'Assessment', japanese ? response.jud : labels.judgments[response.jud]]];
    for (const [label, value] of facts) {
        const pair = make('div', '');
        pair.append(make('dt', label), make('dd', value));
        metadata.append(pair);
    }

    const source = make('div', '', 'response-source');
    source.id = 'response-source-' + response.id;
    source.lang = 'ja';
    const breaks = [...response.text.matchAll(/。(?=[^」』】）)\s])/g)].map(match => match.index + 1);
    const prefix = response.text.match(/^\s*・[ \t\u3000]*/);
    const first = prefix ? prefix[0].length : 0;
    const boundaries = [first, ...breaks.filter(offset => offset > first), response.text.length];
    function showSource(quote) {
        const start = quote ? response.text.indexOf(quote) : -1;
        const end = start + (quote?.length || 0);
        source.replaceChildren();
        for (let i = 1; i < boundaries.length; i++) {
            const left = boundaries[i - 1], right = boundaries[i];
            const paragraph = make('p', '');
            if (start < 0 || left >= end || right <= start) {
                paragraph.textContent = response.text.slice(left, right);
            } else {
                paragraph.append(
                    response.text.slice(left, Math.max(left, start)),
                    make('mark', response.text.slice(Math.max(left, start), Math.min(right, end))),
                    response.text.slice(Math.min(right, end), right)
                );
            }
            source.append(paragraph);
        }
    }
    showSource('');
    body.append(metadata, make('p', japanese ? '回答原文' : 'Original response', 'response-label'), source);

    if (response.ev.length) {
        body.append(make('p', japanese ? '抽出された話題' : 'Evidence by theme', 'response-label'));
        const topics = make('ul', '', 'response-topics');
        const buttons = [];
        const totals = new Map();
        const positions = new Map();
        for (const [theme] of response.ev) totals.set(theme, (totals.get(theme) || 0) + 1);
        for (const [theme, topic, quote] of response.ev) {
            const item = make('li', '');
            const button = make('button', '', 'response-topic');
            button.type = 'button';
            if (japanese) button.lang = 'ja';
            button.setAttribute('aria-controls', source.id);
            button.setAttribute('aria-pressed', 'false');
            if (theme === activeTheme) button.classList.add('matches-theme');
            if (japanese) {
                button.append(make('strong', topic), make('span', theme, 'response-theme'));
            } else {
                const position = (positions.get(theme) || 0) + 1;
                positions.set(theme, position);
                const title = labels.themes[theme];
                button.append(make('strong', totals.get(theme) > 1 ? title + ' — passage ' + position : title));
            }
            button.addEventListener('click', () => {
                const selected = button.getAttribute('aria-pressed') === 'true';
                for (const option of buttons) option.setAttribute('aria-pressed', 'false');
                if (!selected) button.setAttribute('aria-pressed', 'true');
                showSource(selected ? '' : quote);
            });
            buttons.push(button);
            item.append(button);
            topics.append(item);
        }
        body.append(topics);
    } else {
        body.append(make('p', japanese ? '抽出された話題はありません。' : 'No topics extracted.', 'response-hint'));
    }

    detail.append(body);
    return detail;
}
