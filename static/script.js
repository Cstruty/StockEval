// Fetch stock suggestions as user types and display clickable suggestions
async function searchTicker() {
    const query = document.getElementById("search").value;
    const suggestionsDiv = document.getElementById("suggestions");
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
        item.innerText = `${stock.Name} (${stock.Symbol})`;
        item.onclick = () => {
            document.getElementById("search").value = '';
            showResults();
            evaluateStock(stock.Symbol);
            suggestionsDiv.innerHTML = '';
        };
        suggestionsDiv.appendChild(item);
    });
}
function evaluateRawTicker() {
  const input = document.getElementById('raw-ticker-input');
  const ticker = input.value.trim().toUpperCase();
  if (!ticker) {
    alert('Please enter a ticker symbol.');
    return;
  }
  // Clear raw ticker input field after submitting
  input.value = '';
  // Show the results view
  showResults();
  // Call your existing evaluateStock function to add it to watchlist
  evaluateStock(ticker);
}


// Fetch detailed evaluation for a stock and add row if not duplicate
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
        document.getElementById("watchlist-body").appendChild(rowNode);
    } catch (err) {
        console.error("Evaluation failed:", err);
    }
}

// Run AI qualitative analysis for a single stock row, update button accordingly
async function runAIForRow(symbol, btn) {
    btn.disabled = true;
    btn.innerHTML = `<img src="static/icons/loading.gif" alt="Loading" style="width:16px; height:16px;">`;
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
        btn.innerText = "View";
        btn.disabled = false;
        btn.dataset.analysis = cleanText;
        btn.onclick = () => showModal(`${symbol} AI Analysis`, cleanText);
    } catch (err) {
        alert(`Error running AI for ${symbol}`);
        console.error(err);
        btn.innerText = "Retry";
        btn.disabled = false;
    }
}

// Run AI qualitative analysis for all stocks and update buttons
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
        data.forEach(item => {
            resultMap[item.Symbol] = item.Qualitative;
        });
        rows.forEach(row => {
            const symbol = row.id.replace("row-", "");
            const btn = row.querySelector(".ai-button");
            if (resultMap[symbol]) {
                btn.innerText = "View";
                btn.disabled = false;
                const cleanText = resultMap[symbol].replace(/<br\s*\/?>/gi, "<br>");
                btn.dataset.analysis = cleanText;
                btn.onclick = () => showModal(`${symbol} AI Analysis`, cleanText);
            } else {
                btn.innerText = "N/A";
                btn.disabled = true;
            }
        });
    } catch (err) {
        alert("Error running AI analysis.");
        console.error(err);
    }
}

// Import stocks from Excel file and add them if not present
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
    };
    reader.readAsArrayBuffer(file);
}

// Export watchlist table and AI qualitative analysis to Excel
function exportToExcel() {
    const originalTable = document.getElementById("watchlist-table");
    const clonedTable = originalTable.cloneNode(true);

    // Remove last "Delete" column from header and body
    const headerRow = clonedTable.querySelector("thead tr");
    if (headerRow) {
        headerRow.removeChild(headerRow.lastElementChild);
    }

    // Remove the "Qualitative Analysis" column (assumed second last)
    // Find header cells to identify the correct index to remove
    const headers = Array.from(headerRow.cells);
    let aiColIndex = headers.findIndex(th => th.textContent.trim().toLowerCase() === "qualitative analysis");
    if (aiColIndex === -1) {
        // fallback: assume it's second last column before "Delete"
        aiColIndex = headers.length - 1; // If delete column was last and removed, last column now is AI analysis
    }

    // Remove AI analysis column from header row
    if (headerRow.cells[aiColIndex]) {
        headerRow.removeChild(headerRow.cells[aiColIndex]);
    }

    // Remove AI analysis column from all body rows
    clonedTable.querySelectorAll("tbody tr").forEach(row => {
        if (row.cells[aiColIndex]) {
            row.removeChild(row.cells[aiColIndex]);
        }
        // Also remove last "Delete" column (already done earlier, but just in case)
        if (row.lastElementChild) {
            row.removeChild(row.lastElementChild);
        }
    });

    const wb = XLSX.utils.book_new();
    const watchlistSheet = XLSX.utils.table_to_sheet(clonedTable);
    XLSX.utils.book_append_sheet(wb, watchlistSheet, "Watchlist");

    // Prepare AI analysis data separately
    const aiRows = [["Ticker", "Qualitative Analysis"]];
    document.querySelectorAll("#watchlist-body tr").forEach(row => {
        const symbol = row.id.replace("row-", "");
        const btn = row.querySelector(".ai-button");
        let analysis = btn?.dataset?.analysis;
        if (analysis) {
            // Clean HTML tags and convert breaks to newlines
            analysis = analysis
                .replace(/<br\s*\/?>/gi, '\n')
                .replace(/<\/p>\s*<p>/gi, '\n')
                .replace(/<[^>]+>/g, '')
                .trim()
                .replace(/\n+/g, '\n');
            const lines = analysis.split('\n');
            aiRows.push([symbol, lines[0]]);
            for (let i = 1; i < lines.length; i++) {
                aiRows.push(["", lines[i]]);
            }
            aiRows.push(["", ""]); // spacing row
        }
    });

    if (aiRows.length > 1) {
        const aiSheet = XLSX.utils.aoa_to_sheet(aiRows);
        XLSX.utils.book_append_sheet(wb, aiSheet, "Qualitative Analysis");
    }

    XLSX.writeFile(wb, "watchlist.xlsx");
}


// Show modal popup with title and content
function showModal(title, content) {
    const modal = document.getElementById("ai-modal");
    const container = document.getElementById("modal-content");
    container.innerHTML = `<h3>${title}</h3><p>${content}</p>`;
    modal.style.display = "flex";
}

// Close the modal popup
function closeModal() {
    document.getElementById("ai-modal").style.display = "none";
}

// Close modal if clicking outside content
document.getElementById("ai-modal").addEventListener("click", function (e) {
    const content = document.getElementById("modal-content");
    if (!content.contains(e.target)) {
        closeModal();
    }
});

// Transition from initial view to results view, show export button
window.showResults = function () {
    const initialView = document.getElementById('initial-view');
    const resultsView = document.getElementById('results-view');
    const exportBtn = document.getElementById('export-btn');
    const quoteContainer = document.getElementById('quote-container');
    const pageBackground = document.getElementById("page-background");

    if (initialView) {
        initialView.classList.remove('expanded');
        initialView.classList.add('shrunk');
        if (exportBtn) exportBtn.style.display = 'inline-flex';
        if (quoteContainer) quoteContainer.style.display = 'none';
        if (pageBackground) pageBackground.style.animation = 'none';
    }
    if (resultsView) resultsView.style.display = 'block';
};

// Generate HTML row for watchlist table with color-coded metrics
function buildRow(data) {
    const preferredOrder = [
        "Symbol", "Company Name", "Price", "Dividend Yield", "P/E Ratio",
        "ROCE", "Interest Coverage", "Gross Margin", "Net Margin",
        "Cash Conversion Ratio (FCF)", "Gross Profit / Assets", "Score"
    ];

    let row = `<tr id="row-${data.Symbol}">`;

    preferredOrder.forEach(key => {
        let val = data[key] || "N/A";
        switch (key) {
            case "ROCE": val = colorMetric(val, 15, 5); break;
            case "Interest Coverage": val = colorMetric(val, 10, 3); break;
            case "Gross Margin": val = colorMetric(val, 30, 15); break;
            case "Net Margin": val = colorMetric(val, 15, 5); break;
            case "Cash Conversion Ratio (FCF)": val = colorMetric(val, 90, 70); break;
            case "Gross Profit / Assets": val = colorMetric(val, 30, 10); break;
            case "Dividend Yield": val = colorMetric(val, 3, 1); break;
            case "Score": val = colorScore(val); break;
        }
        row += `<td>${val}</td>`;
    });

    row += `<td><button class="ai-button" onclick="runAIForRow('${data.Symbol}', this)">Run</button></td>`;
    row += `<td><button onclick="removeRow('${data.Symbol}')">❌</button></td>`;
    row += "</tr>";
    return row;
}

// Remove a stock row from the watchlist table by symbol
function removeRow(symbol) {
    const row = document.getElementById(`row-${symbol}`);
    if (row) row.remove();
}

// Color code metric value based on thresholds
function colorMetric(value, good, okay) {
    if (!value || value === "N/A") return value;
    let number = parseFloat(value.replace(/[%x]/g, ''));
    if (isNaN(number)) return value;
    let color = "red";
    if (number >= good) color = "#28a745";
    else if (number >= okay) color = "orange";
    return `<span style="color: ${color}">${value}</span>`;
}

// Color code score with thresholds
function colorScore(value) {
    let number = parseFloat(value.replace("/100", ""));
    if (isNaN(number)) return value;
    let color = number >= 80 ? "#28a745" : number >= 50 ? "orange" : "red";
    return `<span style="color: ${color}">${value}</span>`;
}
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

// Shuffle function - Fisher-Yates
function shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

// Shuffle quotes at start
shuffle(quotes);

let currentQuoteIndex = 0;
const quoteContainer = document.getElementById('quote-container');

function showQuote(index) {
    quoteContainer.style.opacity = 0;
    setTimeout(() => {
        quoteContainer.innerHTML = quotes[index];
        quoteContainer.style.opacity = 1;
    }, 500);
}

function cycleQuotes() {
    showQuote(currentQuoteIndex);
    currentQuoteIndex = (currentQuoteIndex + 1) % quotes.length;
}

cycleQuotes();
setInterval(() => {
    quoteContainer.style.opacity = 0;
    setTimeout(() => {
        cycleQuotes();
    }, 1000); // fade out 1s, fade in 0.5s inside showQuote
}, 10000); // every 10 seconds
