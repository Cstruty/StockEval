// ==== SCORING WEIGHTS & MODAL LOGIC ====

// Default scoring weights for all metrics
const scoringWeights = {
    roce: 30,
    interestCov: 30,
    grossMargin: 10,
    netMargin: 10,
    ccr: 5,
    gpAssets: 5,
    peRatio: 5,
    dividendYield: 5
};

// Track last non-deleted weights for each metric
const lastWeights = { ...scoringWeights };
// Track metrics explicitly removed via the toggle button
const deletedMetrics = new Set();

/** Reset modal fields and row states to match current weights */
function resetWeightModal() {
    const config = [
        { key: 'roce', input: 'weight-roce' },
        { key: 'interestCov', input: 'weight-interest' },
        { key: 'grossMargin', input: 'weight-gross' },
        { key: 'netMargin', input: 'weight-net' },
        { key: 'ccr', input: 'weight-ccr' },
        { key: 'gpAssets', input: 'weight-gp' },
        { key: 'peRatio', input: 'weight-pe' },
        { key: 'dividendYield', input: 'weight-div' }
    ];
    config.forEach(({ key, input }) => {
        const row = document.getElementById(`row-${key}`);
        const inputEl = document.getElementById(input);
        const btn = row ? row.querySelector('.weight-toggle') : null;
        const nameSpan = row ? row.querySelector('.metric-name') : null;
        const weight = scoringWeights[key] || 0;
        const deleted = deletedMetrics.has(key);
        if (inputEl) inputEl.value = weight;
        if (row && btn) {
            row.dataset.prev = lastWeights[key] || 0;
            if (deleted) {
                row.classList.add('deleted');
                if (nameSpan) nameSpan.classList.add('deleted');
                btn.innerHTML = '<span class="green-plus">+</span>';
            } else {
                row.classList.remove('deleted');
                if (nameSpan) nameSpan.classList.remove('deleted');
                btn.innerHTML = '<span class="x-icon">❌</span>';
            }
        }
    });
    updateWeightTotal();
}

/** Open the "Adjust Scoring Weights" modal and populate inputs */
function openWeightModal() {
    resetWeightModal();
    document.getElementById('weight-modal').style.display = 'flex';
}

/** Close the scoring weight modal */
function closeWeightModal() {
    document.getElementById('weight-modal').style.display = 'none';
    resetWeightModal();
}

/** Get total of all weights entered in modal */
function getWeightTotal() {
    const ids = ['weight-roce','weight-interest','weight-gross','weight-net','weight-ccr','weight-gp','weight-pe','weight-div'];
    return ids.reduce((sum, id) => {
        const el = document.getElementById(id);
        if (!el) return sum;
        return sum + (parseFloat(el.value) || 0);
    }, 0);
}

/** Updates the donut chart in the scoring modal based on total */
function updateWeightTotal() {
    const total = getWeightTotal();
    updateWeightDonut(total);
}

/** Clear all weight inputs in the modal */
function clearWeightInputs() {
    document.querySelectorAll('#weight-modal input[type="number"]').forEach(inp => {
        inp.value = '';
    });
    updateWeightTotal();
}

/** Toggle delete/add state for a weight row */
function toggleWeight(key) {
    const row = document.getElementById(`row-${key}`);
    if (!row) return;
    const input = row.querySelector('input');
    const nameSpan = row.querySelector('.metric-name');
    const btn = row.querySelector('.weight-toggle');
    if (row.classList.contains('deleted')) {
        row.classList.remove('deleted');
        if (nameSpan) {
            nameSpan.classList.add('reverse');
            nameSpan.classList.remove('deleted');
            setTimeout(() => nameSpan.classList.remove('reverse'), 300);
        }
        setTimeout(() => { btn.innerHTML = '<span class="x-icon">❌</span>'; }, 150);

        input.value = row.dataset.prev || lastWeights[key] || 0;
    } else {
        row.classList.add('deleted');
        if (nameSpan) nameSpan.classList.add('deleted');
        setTimeout(() => { btn.innerHTML = '<span class="green-plus">+</span>'; }, 150);
        row.dataset.prev = input.value;
        lastWeights[key] = input.value;
        input.value = 0;
    }
    updateWeightTotal();
}

/** Animate and color the donut chart in modal */
function updateWeightDonut(total) {
    const circle = document.querySelector('#weight-chart circle.progress');
    const text = document.getElementById('weight-chart-text');
    if (!circle || !text) return;
    const radius = circle.r.baseVal.value;
    const circumference = 2 * Math.PI * radius;
    circle.style.strokeDasharray = `${circumference}`;
    const offset = circumference - (total / 100) * circumference;
    circle.style.strokeDashoffset = offset;
    text.textContent = total;
    circle.classList.remove('green', 'red', 'black');
    text.classList.remove('green', 'red', 'black');
    if (total === 100) {
        circle.classList.add('green'); text.classList.add('green');
    } else if (total > 100) {
        circle.classList.add('red'); text.classList.add('red');
    } else {
        circle.classList.add('black'); text.classList.add('black');
    }
}

/** Save custom weights if valid and update scores */
function saveWeights() {
    const total = getWeightTotal();
    if (total !== 100) {
        showToast('Total weight must equal 100');
        return;
    }
    const columnMap = {
        roce: 'roce',
        interestCov: 'interestCov',
        grossMargin: 'grossMargin',
        netMargin: 'netMargin',
        ccr: 'ccr',
        gpAssets: 'gpAssets',
        peRatio: 'peRatio',
        dividendYield: 'dividendYield'
    };
    const rows = document.querySelectorAll('.weight-item');
    deletedMetrics.clear();
    rows.forEach(row => {
        const key = row.dataset.key;
        const input = row.querySelector('input');
        if (row.classList.contains('deleted')) {
            deletedMetrics.add(key);
            scoringWeights[key] = 0;
        } else {
            scoringWeights[key] = parseFloat(input.value) || 0;
            lastWeights[key] = scoringWeights[key];
        }
        const cls = columnMap[key];
        if (cls) {
            document.querySelectorAll(`.col-${cls}`).forEach(el => {
                el.style.display = deletedMetrics.has(key) ? 'none' : '';
            });
        }
    });
    closeWeightModal();
    updateScores();
    showToast('Scores updated');
}

/** Hide or show metric columns in a row based on current weights */
function applyColumnVisibility(row) {
    const columnMap = {
        roce: 'roce',
        interestCov: 'interestCov',
        grossMargin: 'grossMargin',
        netMargin: 'netMargin',
        ccr: 'ccr',
        gpAssets: 'gpAssets',
        peRatio: 'peRatio',
        dividendYield: 'dividendYield'
    };
    Object.entries(columnMap).forEach(([key, cls]) => {
        const cell = row.querySelector(`.col-${cls}`);
        if (cell) {
            cell.style.display = deletedMetrics.has(key) ? 'none' : '';
        }
    });
}

// ==== SCORING & RENDERING ====

// Convert metric value (handle %, x, $ etc)
function parseMetric(val, isPercent) {
    if (!val) return 0;
    val = String(val).replace(/[%,x$]/g, '').replace(/,/g, '');
    let num = parseFloat(val);
    if (isNaN(num)) return 0;
    return isPercent ? num / 100 : num;
}

/** Main financial scoring algorithm based on metrics and weights */
function calculateScore(metrics) {
    let score = 0;
    const wRoce = scoringWeights.roce || 0;
    const wInt = scoringWeights.interestCov || 0;
    const wGross = scoringWeights.grossMargin || 0;
    const wNet = scoringWeights.netMargin || 0;
    const wCcr = scoringWeights.ccr || 0;
    const wGp = scoringWeights.gpAssets || 0;
    const wPe = scoringWeights.peRatio || 0;
    const wDiv = scoringWeights.dividendYield || 0;

    if (wRoce) score += Math.max(Math.min((metrics.roce / 0.15) * wRoce, wRoce), 0);
    if (wInt) score += Math.max(Math.min((metrics.interestCov / 10) * wInt, wInt), 0);
    if (wGross) score += Math.max(Math.min((metrics.grossMargin / 0.40) * wGross, wGross), 0);
    if (wNet) score += Math.max(Math.min((metrics.netMargin / 0.15) * wNet, wNet), 0);
    if (wCcr) score += Math.max(Math.min((metrics.ccr / 0.90) * wCcr, wCcr), 0);
    if (wGp) score += Math.max(Math.min((metrics.gpAssets / 0.3) * wGp, wGp), 0);
    if (wPe) score += Math.max(Math.min((20 / (metrics.peRatio || 1)) * wPe, wPe), 0);
    if (wDiv) score += Math.max(Math.min((metrics.dividendYield / 0.03) * wDiv, wDiv), 0);
    return Math.min(Math.round(score), 100);
}

/** Update all scores in the watchlist table */
function updateScores() {
    document.querySelectorAll('#watchlist-body tr').forEach(row => {
        const metrics = {
            roce: parseFloat(row.dataset.roce || 0),
            interestCov: parseFloat(row.dataset.interestCov || 0),
            grossMargin: parseFloat(row.dataset.grossMargin || 0),
            netMargin: parseFloat(row.dataset.netMargin || 0),
            ccr: parseFloat(row.dataset.ccr || 0),
            gpAssets: parseFloat(row.dataset.gpAssets || 0),
            peRatio: parseFloat(row.dataset.peRatio || 0),
            dividendYield: parseFloat(row.dataset.dividendYield || 0)
        };
        const score = calculateScore(metrics);
        const cell = row.cells[11];
        if (cell) {
            const donut = cell.querySelector('.score-donut');
            if (donut) {
                updateScoreDonut(donut, score);
            } else {
                cell.innerHTML = createScoreDonut(score);
            }
        }
        row.dataset.score = score;
    });
}

/** Sort table rows based on column and direction */
function sortTable(column, asc) {
    const tbody = document.getElementById('watchlist-body');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort((a, b) => {
        let av = a.dataset[column];
        let bv = b.dataset[column];
        if (column === 'company' || column === 'symbol') {
            av = (av || '').toLowerCase();
            bv = (bv || '').toLowerCase();
            if (av < bv) return asc ? -1 : 1;
            if (av > bv) return asc ? 1 : -1;
            return 0;
        }
        av = parseFloat(av); bv = parseFloat(bv);
        if (isNaN(av)) av = 0; if (isNaN(bv)) bv = 0;
        return asc ? av - bv : bv - av;
    });
    rows.forEach(r => tbody.appendChild(r));
}

// ==== SEARCH & INPUTS ====

// Live search for tickers and show suggestion dropdown
async function searchTicker() {
    const searchInput = document.getElementById("search");
    const query = searchInput.value;
    const suggestionsDiv = document.getElementById("suggestions");
    suggestionsDiv.style.width = `${searchInput.offsetWidth}px`;
    if (query.length < 1) {
        suggestionsDiv.innerHTML = '';
        return;
    }
    const res = await fetch(`/search_ticker?q=${query}`);
    const data = await res.json();
    suggestionsDiv.innerHTML = '';
    data.forEach(stock => {
        const item = document.createElement("div");
        item.className = "suggestion-item";
        item.tabIndex = 0;
        const country = stock.CountryShort ? ` -${stock.CountryShort}` : '';
        item.innerText = `${stock.Name} (${stock.Symbol})${country}`;
        item.onclick = () => {
            document.getElementById("search").value = '';
            showResults();
            evaluateStock(stock.Symbol);
            suggestionsDiv.innerHTML = '';
        };
        item.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                (item.nextElementSibling || suggestionsDiv.firstElementChild).focus();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (item.previousElementSibling) {
                    item.previousElementSibling.focus();
                } else {
                    searchInput.focus();
                }
            } else if (e.key === 'Enter') {
                e.preventDefault();
                item.click();
            }
        });
        suggestionsDiv.appendChild(item);
    });
}

const searchInputField = document.getElementById('search');
if (searchInputField) {
    searchInputField.addEventListener('keydown', (e) => {
        const suggestionsDiv = document.getElementById('suggestions');
        if (!suggestionsDiv) return;
        const items = suggestionsDiv.querySelectorAll('.suggestion-item');
        if (e.key === 'ArrowDown' && items.length) {
            e.preventDefault();
            items[0].focus();
        } else if (e.key === 'ArrowUp' && items.length) {
            e.preventDefault();
            items[items.length - 1].focus();
        }
    });
}

// Raw ticker input (from hidden box)
function evaluateRawTicker() {
    const input = document.getElementById('raw-ticker-input');
    const ticker = input.value.trim().toUpperCase();
    if (!ticker) {
        alert('Please enter a ticker symbol.');
        return;
    }
    input.value = '';
    showResults();
    evaluateStock(ticker);
}

// ==== TABLE: ADD/REMOVE/EVALUATE ====

// Fetch data for ticker and add a new row (if not duplicate)
async function evaluateStock(symbol) {
    if (!symbol) return;
    try {
        const res = await fetch(`/evaluate/${symbol}`);
        const data = await res.json();
        if (data.error) {
            alert("Error: " + data.error);
            return;
        }
        if (document.getElementById(`row-${symbol}`)) return; // avoid duplicates
        const rowHtml = buildRow(data);
        const temp = document.createElement('tbody');
        temp.innerHTML = rowHtml;
        const rowNode = temp.firstElementChild;
        // Store metrics for sorting/scoring
        rowNode.dataset.symbol = data.Symbol || '';
        rowNode.dataset.company = data["Company Name"] || '';
        rowNode.dataset.country = data.Country || '';
        rowNode.dataset.price = parseMetric(data.Price, false);
        rowNode.dataset.dividendYield = parseMetric(data["Dividend Yield"], true);
        rowNode.dataset.peRatio = parseMetric(data["P/E Ratio"], false);
        rowNode.dataset.roce = parseMetric(data.ROCE, true);
        rowNode.dataset.interestCov = parseMetric(data["Interest Coverage"], false);
        rowNode.dataset.grossMargin = parseMetric(data["Gross Margin"], true);
        rowNode.dataset.netMargin = parseMetric(data["Net Margin"], true);
        rowNode.dataset.ccr = parseMetric(data["Cash Conversion Ratio (FCF)"], true);
        rowNode.dataset.gpAssets = parseMetric(data["Gross Profit / Assets"], true);
        rowNode.dataset.ai = 0;
        applyColumnVisibility(rowNode);
        document.getElementById("watchlist-body").appendChild(rowNode);
        updateScores();
    } catch (err) {
        console.error("Evaluation failed:", err);
    }
}

/** Remove a stock row by ticker symbol */
function removeRow(symbol) {
    const row = document.getElementById(`row-${symbol}`);
    if (row) row.remove();
}

// ==== AI ANALYSIS ====

// Run AI qualitative analysis for a single row
async function runAIForRow(symbol, btn) {
    btn.disabled = true;
    btn.innerHTML = `<img src="static/icons/loading.gif" alt="Loading" style="width:25px; height:25px;">`;
    try {
        const res = await fetch("/run_qualitative", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tickers: [symbol] })
        });
        const data = await res.json();
        if (!Array.isArray(data) || data.length === 0) {
            btn.innerText = "Retry";
            alert(`No AI result for ${symbol}.`);
            return;
        }
        const cleanText = data[0].Qualitative.replace(/<br\s*\/?>/gi, "<br>");
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" width="50" height="50" fill="white" xmlns="http://www.w3.org/2000/svg">
            <path d="M14 3h7v7h-2V6.41l-9.29 9.3-1.42-1.42L17.59 5H14V3z"/>
            <path d="M5 5h5V3H5c-1.1 0-2 .9-2 2v5h2V5z"/>
            <path d="M19 19h-5v2h5c1.1 0 2-.9 2-2v-5h-2v5z"/>
            <path d="M5 19v-5H3v5c0 1.1.9 2 2 2h5v-2H5z"/>
            </svg>`;
        btn.disabled = false;
        btn.dataset.analysis = cleanText;
        btn.onclick = () => showModal(`${symbol} AI Analysis`, cleanText);
        const row = document.getElementById(`row-${symbol}`);
        if (row) row.dataset.ai = 1;
    } catch (err) {
        alert(`Error running AI for ${symbol}`);
        btn.innerText = "Retry";
        btn.disabled = false;
    }
}

/** Run AI qualitative analysis for all watchlist stocks */
async function runAllAI() {
    const rows = Array.from(document.querySelectorAll("#watchlist-body tr"));
    const symbols = rows.map(row => row.id.replace("row-", ""));
    if (symbols.length === 0) {
        alert("No stocks to analyze.");
        return;
    }
    const buttons = rows.map(row => row.querySelector(".ai-button"));
    buttons.forEach(btn => {
        btn.disabled = true;
        btn.innerHTML = `<img src="static/icons/loading.gif" alt="Loading" style="width:16px; height:16px;">`;
    });
    try {
        const res = await fetch("/run_qualitative", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tickers: symbols })
        });
        const data = await res.json();
        if (!Array.isArray(data) || data.length === 0) {
            alert("No AI results.");
            return;
        }
        const resultMap = {};
        data.forEach(item => { resultMap[item.Symbol] = item.Qualitative; });
        rows.forEach(row => {
            const symbol = row.id.replace("row-", "");
            const btn = row.querySelector(".ai-button");
            if (resultMap[symbol]) {
                btn.innerText = "View";
                btn.disabled = false;
                const cleanText = resultMap[symbol].replace(/<br\s*\/?>/gi, "<br>");
                btn.dataset.analysis = cleanText;
                btn.onclick = () => showModal(`${symbol} AI Analysis`, cleanText);
                row.dataset.ai = 1;
            } else {
                btn.innerText = "N/A";
                btn.disabled = true;
                row.dataset.ai = 0;
            }
        });
    } catch (err) {
        alert("Error running AI analysis.");
    }
}

// ==== IMPORT/EXPORT ====

// Import stocks and scoring weights from Excel file
function importFromExcel(event) {
    const file = event.target.files[0];
    if (!file) return;
    showResults();
    const reader = new FileReader();
    reader.onload = function (e) {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const sheet = workbook.Sheets[sheetName];
        const json = XLSX.utils.sheet_to_json(sheet);
        json.forEach(row => {
            const symbol = row.Symbol || row['symbol'];
            if (symbol && !document.getElementById(`row-${symbol}`)) {
                evaluateStock(symbol.trim());
            }
        });

        // Import custom weights if present
        const weightSheet = workbook.Sheets['Scoring Weight'];
        if (weightSheet) {
            const weights = XLSX.utils.sheet_to_json(weightSheet, { header: 1 });
            const map = {
                'ROCE': 'roce',
                'Interest Coverage': 'interestCov',
                'Gross Margin': 'grossMargin',
                'Net Margin': 'netMargin',
                'Cash Conversion Ratio': 'ccr',
                'Gross Profit / Assets': 'gpAssets',
                'P/E Ratio': 'peRatio',
                'Dividend Yield': 'dividendYield'
            };
            weights.forEach((row) => {
                if (row.length >= 2 && map[row[0]]) {
                    const val = parseFloat(row[1]);
                    if (!isNaN(val)) scoringWeights[map[row[0]]] = val;
                }
            });
            updateScores();
            updateWeightDonut(getWeightTotal());
        }
    };
    reader.readAsArrayBuffer(file);
}

/** Export table and AI analysis as multi-sheet Excel */
function exportToExcel() {
    const originalTable = document.getElementById("watchlist-table");
    const clonedTable = originalTable.cloneNode(true);

    // Remove sort arrows and settings button
    clonedTable.querySelectorAll('.sort-arrows').forEach(el => el.remove());
    const settingsBtn = clonedTable.querySelector('#settings-btn');
    if (settingsBtn) settingsBtn.remove();

    // Remove last "Delete" column and AI column
    const headerRow = clonedTable.querySelector("thead tr");
    if (headerRow) headerRow.removeChild(headerRow.lastElementChild);
    const headers = Array.from(headerRow.cells);
    let aiColIndex = headers.findIndex(th => th.textContent.trim().toLowerCase() === "qualitative analysis");
    if (aiColIndex === -1) aiColIndex = headers.length - 1;
    if (headerRow.cells[aiColIndex]) headerRow.removeChild(headerRow.cells[aiColIndex]);
    clonedTable.querySelectorAll("tbody tr").forEach(row => {
        if (row.cells[aiColIndex]) row.removeChild(row.cells[aiColIndex]);
        if (row.lastElementChild) row.removeChild(row.lastElementChild);
    });

    const wb = XLSX.utils.book_new();
    const watchlistSheet = XLSX.utils.table_to_sheet(clonedTable);
    XLSX.utils.book_append_sheet(wb, watchlistSheet, "Watchlist");

    // AI analysis sheet
    const aiRows = [["Ticker", "Qualitative Analysis"]];
    document.querySelectorAll("#watchlist-body tr").forEach(row => {
        const symbol = row.id.replace("row-", "");
        const btn = row.querySelector(".ai-button");
        let analysis = btn?.dataset?.analysis;
        if (analysis) {
            analysis = analysis.replace(/<br\s*\/?>/gi, '\n')
                .replace(/<\/p>\s*<p>/gi, '\n')
                .replace(/<[^>]+>/g, '')
                .trim()
                .replace(/\n+/g, '\n');
            const lines = analysis.split('\n');
            aiRows.push([symbol, lines[0]]);
            for (let i = 1; i < lines.length; i++) aiRows.push(["", lines[i]]);
            aiRows.push(["", ""]);
        }
    });
    if (aiRows.length > 1) {
        const aiSheet = XLSX.utils.aoa_to_sheet(aiRows);
        XLSX.utils.book_append_sheet(wb, aiSheet, "Qualitative Analysis");
    }

    // Scoring weights
    const weightRows = [
        ["Metric", "Weight"],
        ["ROCE", scoringWeights.roce],
        ["Interest Coverage", scoringWeights.interestCov],
        ["Gross Margin", scoringWeights.grossMargin],
        ["Net Margin", scoringWeights.netMargin],
        ["Cash Conversion Ratio", scoringWeights.ccr],
        ["Gross Profit / Assets", scoringWeights.gpAssets],
        ["P/E Ratio", scoringWeights.peRatio],
        ["Dividend Yield", scoringWeights.dividendYield]
    ];
    const weightSheet = XLSX.utils.aoa_to_sheet(weightRows);
    XLSX.utils.book_append_sheet(wb, weightSheet, "Scoring Weight");

    XLSX.writeFile(wb, "watchlist.xlsx");
}

// ==== MODAL HANDLING ====

// Show modal popup with title and content
function showModal(title, content) {
    const modal = document.getElementById("ai-modal");
    const container = document.getElementById("modal-content");
    container.innerHTML = `<h3>${title}</h3>${content}`;
    modal.style.display = "flex";
}

function openInfoModal() {
    const headers = document.querySelectorAll('#watchlist-table thead th');
    let list = '<ul class="info-list">';
    headers.forEach(th => {
        const desc = th.getAttribute('title');
        const labelEl = th.querySelector('.th-label');
        const rawLabel = labelEl ? labelEl.innerText : th.textContent;
        const label = rawLabel.replace(/▲|▼/g, '').trim();
        if (desc) {
            list += `<li><strong>${label}</strong>: ${desc}</li>`;
        }
    });
    list += '</ul>';
    showModal('Column Information', list);
}
function closeModal() {
    document.getElementById("ai-modal").style.display = "none";
}

// Generic "click outside to close" logic for any modal
function enableClickOutsideToClose(modalId, contentId, closeFn) {
    const modal = document.getElementById(modalId);
    const content = document.getElementById(contentId);
    if (!modal || !content) return;
    modal.addEventListener("click", function (e) {
        if (!content.contains(e.target)) closeFn();
    });
}

// ==== UI TRANSITIONS & TOAST ====

// Transition to table/results view
window.showResults = function () {
    const initialView = document.getElementById('initial-view');
    const resultsView = document.getElementById('results-view');
    const exportBtn = document.getElementById('export-btn');
    const quoteContainer = document.getElementById('quote-container');
    const pageBackground = document.getElementById("page-background");
    const mobileActions = document.querySelector('.mobile-action-buttons');
    const infoBtn = document.getElementById('info-btn');
    if (initialView) {
        initialView.classList.remove('expanded');
        initialView.classList.add('shrunk');
        if (exportBtn) exportBtn.style.display = 'inline-flex';
        if (quoteContainer) quoteContainer.style.display = 'none';
        if (pageBackground) pageBackground.style.animation = 'none';
        if (mobileActions && window.matchMedia('(max-width: 600px)').matches) {
            mobileActions.style.display = 'flex';
        }
    }
    if (resultsView) resultsView.style.display = 'block';
    if (infoBtn) infoBtn.style.display = 'flex';
};

/** Build a table row (HTML) for a new stock */
function buildRow(data) {
    const preferredOrder = [
        "Symbol", "Price", "Dividend Yield", "P/E Ratio",
        "ROCE", "Interest Coverage", "Gross Margin", "Net Margin",
        "Cash Conversion Ratio (FCF)", "Gross Profit / Assets", "Score"
    ];
    const classMap = {
        "Price": "price",
        "Dividend Yield": "dividendYield",
        "P/E Ratio": "peRatio",
        "ROCE": "roce",
        "Interest Coverage": "interestCov",
        "Gross Margin": "grossMargin",
        "Net Margin": "netMargin",
        "Cash Conversion Ratio (FCF)": "ccr",
        "Gross Profit / Assets": "gpAssets",
        "Score": "score"
    };
    let row = `<tr id="row-${data.Symbol}" data-company="${data["Company Name"] || ''}" data-country="${data.Country || ''}">`;
    // Symbol
    row += `<td>${data.Symbol || 'N/A'}</td>`;
    // Company and country
    const company = data["Company Name"] || 'N/A';
    const country = data.Country || '';
    row += `<td><div>${company}</div><div class="country-sub">${country}</div></td>`;
    preferredOrder.slice(1).forEach(key => {
        let val = data[key] || "N/A";
        switch (key) {
            case "ROCE": val = colorMetric(val, 15, 5); break;
            case "Interest Coverage": val = colorMetric(val, 10, 3); break;
            case "Gross Margin": val = colorMetric(val, 30, 15); break;
            case "Net Margin": val = colorMetric(val, 15, 5); break;
            case "Cash Conversion Ratio (FCF)": val = colorMetric(val, 90, 70); break;
            case "Gross Profit / Assets": val = colorMetric(val, 30, 10); break;
            case "Dividend Yield": val = colorMetric(val, 3, 1); break;
            case "Score":
                const num = parseFloat(String(val).replace('/100', '')) || 0;
                val = createScoreDonut(num);
                break;
        }
        const cls = classMap[key] || key.toLowerCase().replace(/\s+|\//g, '_');
        row += `<td data-label="${key}" class="col-${cls}">${val}</td>`;
    });
    row += `<td class="ai-cell">
        <button class="ai-button" onclick="runAIForRow('${data.Symbol}', this)">
            ▶
        </button>
    </td>`;

    row += `<td class="delete-cell"><button class="delete-button" onclick="removeRow('${data.Symbol}')">❌</button></td>`;
    row += "</tr>";
    return row;
}

/** Color code metrics based on thresholds */
function colorMetric(value, good, okay) {
    if (!value || value === "N/A") return value;
    let number = parseFloat(value.replace(/[%x]/g, ''));
    if (isNaN(number)) return value;
    let color = "red";
    if (number >= good) color = "#28a745";
    else if (number >= okay) color = "orange";
    return `<span style="color: ${color}">${value}</span>`;
}

/** Color code score with thresholds */
function colorScore(value) {
    let number = parseFloat(value.replace("/100", ""));
    if (isNaN(number)) return value;
    let color = number >= 80 ? "#28a745" : number >= 50 ? "orange" : "red";
    return `<span style="color: ${color}">${value}</span>`;
}

/** Create SVG donut for a given score */
function createScoreDonut(score) {
    return (
        `<div class="score-donut" data-score="${score}">` +
        `<svg viewBox="0 0 40 40" style="overflow: visible">` +
        `<circle class="bg" cx="15" cy="20" r="14" />` +
        `<circle class="progress" cx="15" cy="20" r="14" />` +
        `<text x="15" y="20" text-anchor="middle" dominant-baseline="middle">${score}</text>` +
        `</svg>` +
        `</div>`
    );
}

/** Animate and color a score donut */
function updateScoreDonut(wrapper, score) {
    const circle = wrapper.querySelector('circle.progress');
    const text = wrapper.querySelector('text');
    if (!circle || !text) return;
    const radius = circle.r.baseVal.value;
    const circumference = 2 * Math.PI * radius;
    circle.style.strokeDasharray = `${circumference}`;
    const offset = circumference - (score / 100) * circumference;
    circle.style.strokeDashoffset = offset;
    const color = score >= 80 ? '#28a745' : score >= 50 ? 'orange' : 'red';
    circle.style.stroke = color;
    text.style.fill = color;
    text.textContent = score;
    wrapper.dataset.score = score;
}

// ==== QUOTES ====

// Inspirational quotes list
const quotes = [
    `“Be fearful when others are greedy and greedy when others are fearful.” – Warren Buffett`,
    `“The intelligent investor is a realist who sells to optimists and buys from pessimists.” – Benjamin Graham`,
    `“Know what you own, and know why you own it.” – Peter Lynch`,
    `“Don’t look for the needle in the haystack. Just buy the haystack!” – John C. Bogle`,
    `“The big money is not in the buying or selling, but in the waiting.” – Charlie Munger`,
    `“The stock market is never obvious. It is designed to fool most of the people, most of the time.” – Jesse Livermore`,
    `“The stock market is filled with individuals who know the price of everything, but the value of nothing.” – Philip Fisher`,
    `“It’s not whether you’re right or wrong that’s important, but how much money you make when you’re right and how much you lose when you’re wrong.” – George Soros`,
    `“In life and business, there are no guarantees. So you have to bet on yourself.” – Carl Icahn`,
    `“He who lives by the crystal ball will eat shattered glass.” – Ray Dalio`
];

// Shuffle array in place (Fisher-Yates)
function shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}
shuffle(quotes);

let currentQuoteIndex = 0;
const quoteContainer = document.getElementById('quote-container');

/** Show a quote with fade effect */
function showQuote(index) {
    quoteContainer.style.opacity = 0;
    setTimeout(() => {
        quoteContainer.innerHTML = quotes[index];
        quoteContainer.style.opacity = 1;
    }, 500);
}
/** Cycle quotes every 10 seconds */
function cycleQuotes() {
    showQuote(currentQuoteIndex);
    currentQuoteIndex = (currentQuoteIndex + 1) % quotes.length;
}
// Start quote cycle and fade in/out
cycleQuotes();
setInterval(() => {
    quoteContainer.style.opacity = 0;
    setTimeout(() => {
        cycleQuotes();
    }, 1000);
}, 10000);

// ==== TOAST NOTIFICATIONS ====

// Hide notification toast
function hideToast() {
    const toast = document.getElementById('toast');
    if (toast) toast.classList.remove('show');
}

// Show a notification message at the top
function showToast(msg) {
    const toast = document.getElementById('toast');
    const msgSpan = document.getElementById('toast-message');
    if (!toast || !msgSpan) return;
    msgSpan.textContent = msg;
    toast.classList.add('show');
    clearTimeout(showToast._timeout);
    showToast._timeout = setTimeout(hideToast, 10000);
}

// ==== EVENT HANDLERS ====

// Make number inputs in scoring modal update the donut
document.querySelectorAll('#weight-modal input[type="number"]').forEach(inp => {
    inp.addEventListener('input', updateWeightTotal);
});

// Click-outside-to-close for modals
enableClickOutsideToClose("ai-modal", "modal-content", closeModal);
enableClickOutsideToClose("weight-modal", "weight-modal-content", closeWeightModal);
