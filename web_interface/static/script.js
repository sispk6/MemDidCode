document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');

            navItems.forEach(i => i.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            item.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // Stats and Entities Loading
    loadStats();
    loadEntities();

    // Search
    const searchBtn = document.getElementById('search-btn');
    const queryInput = document.getElementById('query-input');
    const resultsContainer = document.getElementById('results-container');

    searchBtn.addEventListener('click', performSearch);
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    async function performSearch() {
        const text = queryInput.value;
        if (!text) return;

        resultsContainer.innerHTML = '<div class="loading">Searching memory...</div>';

        const platform = document.getElementById('platform-filter').value;
        const entity_id = document.getElementById('entity-filter').value;

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, platform, entity_id })
            });
            const data = await response.json();
            displayAnswer(data.answer);
            displayResults(data.results);
        } catch (error) {
            resultsContainer.innerHTML = `<div class="error">Search failed: ${error}</div>`;
        }
    }

    function displayAnswer(answer) {
        const answerContainer = document.getElementById('answer-container');
        const answerBox = document.getElementById('answer-box');
        const answerMeta = document.getElementById('answer-meta');

        if (!answer || !answer.answer) {
            answerContainer.style.display = 'none';
            return;
        }

        answerContainer.style.display = 'block';
        answerBox.innerHTML = answer.answer.replace(/\n/g, '<br>');
        answerMeta.innerHTML = `<small>Confidence: ${answer.confidence} | Sources: ${answer.sources_used}</small>`;
    }

    function displayResults(results) {
        if (!results || results.length === 0) {
            resultsContainer.innerHTML = '<div class="empty-state">No matching memories found.</div>';
            return;
        }

        resultsContainer.innerHTML = results.map(res => `
            <div class="result-card">
                <div class="result-meta">
                    <span class="tag">${res.platform}</span>
                    <span>${res.date}</span>
                    <span>Score: ${res.similarity.toFixed(2)}</span>
                </div>
                <div class="result-subject">${res.subject}</div>
                <div class="result-sender">From: ${res.sender}</div>
                <div class="result-snippet">${res.snippet}</div>
            </div>
        `).join('');
    }

    // Ingest and Embed Actions
    const ingestBtn = document.getElementById('ingest-btn');
    const embedBtn = document.getElementById('embed-btn');
    const logContent = document.getElementById('activity-log');

    ingestBtn.addEventListener('click', async () => {
        const mode = document.getElementById('ingest-mode').value;
        addLog(`[System] Requesting ingestion: mode=${mode}`);

        try {
            const response = await fetch('/api/ingest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode, max_results: 50 })
            });
            const data = await response.json();
            addLog(`[OK] ${data.status}`);
        } catch (error) {
            addLog(`[ERROR] ${error}`);
        }
    });

    embedBtn.addEventListener('click', async () => {
        addLog(`[System] Requesting embedding generation...`);
        try {
            const response = await fetch('/api/embed', { method: 'POST' });
            const data = await response.json();
            addLog(`[OK] ${data.status}`);
        } catch (error) {
            addLog(`[ERROR] ${error}`);
        }
    });

    function addLog(msg) {
        const time = new Date().toLocaleTimeString();
        logContent.innerHTML += `<div>[${time}] ${msg}</div>`;
        logContent.scrollTop = logContent.scrollHeight;
    }

    async function loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            document.getElementById('doc-count').innerText = data.total_messages;
            document.getElementById('platform-name').innerText = "Hybrid";
        } catch (e) {
            console.error("Stats load failed", e);
        }
    }

    async function loadEntities() {
        try {
            const response = await fetch('/api/kb/entities');
            const data = await response.json();
            const filter = document.getElementById('entity-filter');
            const list = document.getElementById('kb-entities-list');

            if (data.entities && data.entities.length > 0) {
                filter.innerHTML = '<option value="">All People</option>' +
                    data.entities.map(e => `<option value="${e.id}">${e.canonical_name}</option>`).join('');

                list.innerHTML = data.entities.map(e => `
                    <div class="card person-card">
                        <h4>${e.canonical_name}</h4>
                        <p>${e.type.toUpperCase()}</p>
                        <small>ID: ${e.id.substring(0, 8)}...</small>
                    </div>
                `).join('');
            }
        } catch (e) {
            console.error("Entities load failed", e);
        }
    }
});
