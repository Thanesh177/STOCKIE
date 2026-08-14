// static/app.js
var tickers = JSON.parse(localStorage.getItem("tickers")) || [];
var lastPrices = {};
var counter = 13;
var priceChart = null;
const TICKER_PATTERN = /^[A-Z0-9][A-Z0-9.\-^=]{0,14}$/;

function normalizeTicker(value) {
    const ticker = String(value || "").trim().toUpperCase();
    return TICKER_PATTERN.test(ticker) ? ticker : null;
}

function getTickerFromUrl() {
    try {
        const parts = (window.location.pathname || "").split("/").filter(Boolean);
        const idx = parts.indexOf("predict");
        if (idx >= 0 && parts[idx + 1]) {
            return decodeURIComponent(parts[idx + 1]).toUpperCase();
        }
    } catch (e) {}
    return null;
}

function startUpdateCycle() {
    updatePrices();
    setInterval(function () {
        counter--;
        $("#counter").text(counter);
        if (counter <= 0) {
            updatePrices();
            counter = 13;
        }
    }, 1000);
}

function addTickerToGrid(ticker) {
    const safeTicker = normalizeTicker(ticker);
    if (!safeTicker) return;
    $("#tickers-grid .empty-state").remove();
    const box = $("<div>", { id: safeTicker, class: "stock-box" });
    box.append($("<h2>").text(safeTicker));
    box.append($("<p>", { id: `${safeTicker}-price`, text: "Loading…" }));
    box.append($("<p>", { id: `${safeTicker}-pct` }));
    box.append($("<button>", { class: "detail", "data-ticker": safeTicker, text: "View details →" }));
    box.append($("<button>", { class: "remove-btn", "data-ticker": safeTicker, text: "X" }));
    $("#tickers-grid").append(box);
}

function updatePrice(ticker) {
    $.ajax({
        url: "/get_stock_data",
        type: "POST",
        data: JSON.stringify({ ticker: ticker.replace(/\$/g, "").toUpperCase() }),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            if (data.error) {
                console.error(`Error fetching ${ticker}: ${data.error}`);
                return;
            }

            var changePercent = ((data.currentPrice - data.openPrice) / data.openPrice) * 100;
            var colorClass =
                changePercent <= -2 ? "dark-red" :
                changePercent < 0 ? "red" :
                changePercent <= 2 ? "green" :
                "dark-green";

            $(`#${ticker}-price`).text(`$${data.currentPrice.toFixed(2)}`);
            $(`#${ticker}-pct`).text(`${changePercent.toFixed(2)}%`);
            $(`#${ticker}-price, #${ticker}-pct`)
                .removeClass("dark-red red green dark-green")
                .addClass(colorClass);
        },
        error: function (xhr) {
            console.error(`Error fetching ${ticker}: ${xhr.responseText}`);
        }
    });
}

function updatePrices() {
    tickers.forEach(function (ticker) {
        $.ajax({
            url: "/get_stock_data",
            type: "POST",
            data: JSON.stringify({ ticker: ticker }),
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            success: function (data) {
                if (data.error) {
                    console.error(`Error fetching ${ticker}: ${data.error}`);
                    return;
                }

                var changePercent = ((data.currentPrice - data.openPrice) / data.openPrice) * 100;
                var colorClass;

                if (changePercent <= -2) {
                    colorClass = "dark-red";
                } else if (changePercent < 0) {
                    colorClass = "red";
                } else if (changePercent <= 2) {
                    colorClass = "green";
                } else {
                    colorClass = "dark-green";
                }

                $(`#${ticker}-price`).text(`$${data.currentPrice.toFixed(2)}`);
                $(`#${ticker}-pct`).text(`${changePercent.toFixed(2)}%`);
                $(`#${ticker}-price`).removeClass("dark-red red green dark-green").addClass(colorClass);
                $(`#${ticker}-pct`).removeClass("dark-red red green dark-green").addClass(colorClass);

                var flashClass;
                if (lastPrices[ticker] > data.currentPrice) {
                    flashClass = "red-flash";
                } else if (lastPrices[ticker] < data.currentPrice) {
                    flashClass = "green-flash";
                }

                lastPrices[ticker] = data.currentPrice;

                if (flashClass) {
                    $(`#${ticker}-price, #${ticker}-pct`).addClass(flashClass);
                    setTimeout(function () {
                        $(`#${ticker}-price, #${ticker}-pct`).removeClass(flashClass);
                    }, 650);
                }
            },
            error: function (xhr) {
                console.error(`Error fetching ${ticker}: ${xhr.responseText}`);
            }
        });
    });
}

function renderDetailsBox(ticker) {
    if (!document.getElementById("details")) return;
    if (document.getElementById(`${ticker}-price`)) return;

    const safeTicker = normalizeTicker(ticker);
    if (!safeTicker) return;
    $("#details").append(
        $("<div>", { id: safeTicker, class: "box" })
            .append($("<strong>").text(safeTicker))
            .append($("<strong>", { id: `${safeTicker}-price`, text: "—" }))
            .append($("<p>", { id: `${safeTicker}-pct` }))
    );

    updatePrice(ticker);
}

function safeNums(arr) {
    if (!Array.isArray(arr)) return [];
    return arr
        .map((v) => (typeof v === "string" ? Number(v) : v))
        .filter((v) => Number.isFinite(v));
}

function setNextDayPrediction(val) {
    if (!Number.isFinite(val)) return;
    const el = document.getElementById("nextDayPrediction");
    if (el) el.textContent = formatCurrency(val);
}

function formatCurrency(value) {
    return new Intl.NumberFormat("en-US", {
        style: "currency", currency: "USD", maximumFractionDigits: 2
    }).format(value);
}

function renderPriceChart(ticker, actual, predicted) {
    const canvas = document.getElementById("priceChart");
    if (!canvas) return;

    const err = document.getElementById("chartError");

    if (typeof Chart === "undefined") {
        if (err) err.textContent = "Chart.js not loaded";
        return;
    }

    const ctx = canvas.getContext("2d");
    const n = actual.length;
    const m = Math.max(predicted.length, 1);

    const labels = Array.from({ length: n + m }, (_, i) =>
        i < n ? `T${i - n + 1}` : `Forecast ${i - n + 1}`
    );
    const actualSeries = actual.concat(Array.from({ length: m }, () => null));
    const predSeries = Array.from({ length: Math.max(n - 1, 0) }, () => null)
        .concat(n ? [actual[n - 1]] : [])
        .concat(predicted.length ? predicted : [null]);

    if (priceChart) priceChart.destroy();

    priceChart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: `${ticker} (Actual)`,
                    data: actualSeries,
                    tension: 0.25,
                    pointRadius: 0,
                    borderWidth: 2.2,
                    borderColor: "#72d8ff",
                    backgroundColor: "rgba(114,216,255,.08)",
                    fill: true
                },
                {
                    label: `${ticker} (Predicted)`,
                    data: predSeries,
                    tension: 0.25,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    borderWidth: 2.2,
                    borderDash: [7, 5],
                    borderColor: "#5ee4c0",
                    backgroundColor: "#5ee4c0"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: "index" },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#0b141a", borderColor: "#385260", borderWidth: 1,
                    titleColor: "#b8c7cd", bodyColor: "#e6f5f8", padding: 11,
                    callbacks: { label: (context) => `${context.dataset.label}: ${formatCurrency(context.parsed.y)}` }
                }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: "#70828c", maxTicksLimit: 7, font: { size: 10 } } },
                y: { grid: { color: "rgba(145,177,191,.12)" }, ticks: { color: "#70828c", callback: (value) => `$${Number(value).toFixed(0)}`, font: { size: 10 } } }
            }
        }
    });

    const last = actual[n - 1];
    const next = predicted[0];
    const change = Number.isFinite(last) && Number.isFinite(next) ? ((next - last) / last) * 100 : null;
    const meta = document.getElementById("chartMeta");
    const predictionMeta = document.getElementById("predictionMeta");
    if (meta && Number.isFinite(last)) {
        meta.innerHTML = `<span>LAST CLOSE <b>${formatCurrency(last)}</b></span>${change !== null ? `<span>MODEL DELTA <b class="${change >= 0 ? "green" : "red"}">${change >= 0 ? "+" : ""}${change.toFixed(2)}%</b></span>` : ""}<span>HORIZON <b>${predicted.length} SESSION${predicted.length === 1 ? "" : "S"}</b></span>`;
    }
    if (predictionMeta && change !== null) {
        predictionMeta.textContent = `Model projection: ${change >= 0 ? "up" : "down"} ${Math.abs(change).toFixed(2)}% from the latest observed close. Informational only—not investment advice.`;
    }
}

async function fetchAndRenderPrediction() {
    const ticker =
        (document.body.dataset.ticker || "").trim().toUpperCase() ||
        getTickerFromUrl() ||
        (localStorage.getItem("stock") || "").trim().toUpperCase();

    if (!ticker) return;

    const err = document.getElementById("chartError");
    if (err) err.textContent = "";

    const url = (window.PREDICT_API_URL || "/predict").trim();

    try {
        const resp = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ticker: ticker })
        });

        const text = await resp.text();
        let data;

        try {
            data = JSON.parse(text);
        } catch {
            if (err) err.textContent = "Prediction API returned non-JSON";
            return;
        }

        if (!resp.ok) {
            if (err) err.textContent = data.error || data.message || "Prediction API error";
            return;
        }

        const actual = safeNums(data.last_60_actual || data.actual_prices || data.actual || []);
        const predicted = safeNums(data.predicted || data.predicted_prices || []);
        const next =
            Number.isFinite(data.next_price) ? Number(data.next_price) :
            Number.isFinite(data.predicted_next_close) ? Number(data.predicted_next_close) :
            (predicted.length ? predicted[predicted.length - 1] : NaN);

        if (Number.isFinite(next)) {
            setNextDayPrediction(next);
        }

        if (!actual.length) {
            if (err) err.textContent = "No actual prices returned";
            return;
        }

        renderPriceChart(
            ticker,
            actual,
            predicted.length ? predicted : (Number.isFinite(next) ? [next] : [])
        );
    } catch (e) {
        if (err) err.textContent = "Failed to call prediction API";
        console.error(e);
    }
}

function initHome() {
    const form = document.getElementById("add-ticker-form");
    const input = document.getElementById("new-ticker");
    const hasGrid = document.getElementById("tickers-grid");

    if (!form || !input || hasGrid) return;

    $(form).on("submit", function (e) {
        e.preventDefault();

        const newTicker = normalizeTicker(input.value);
        if (!newTicker) return;

        if (!tickers.includes(newTicker)) {
            tickers.push(newTicker);
            localStorage.setItem("tickers", JSON.stringify(tickers));
        }

        localStorage.setItem("stock", newTicker);
        input.value = "";
        window.location.href = "/middle";
    });
}

function initMiddle() {
    const grid = document.getElementById("tickers-grid");
    if (!grid) return;

    tickers.forEach(function (ticker) {
        addTickerToGrid(ticker);
    });

    updatePrices();

    $("#add-ticker-form").on("submit", function (e) {
        e.preventDefault();

        const newTicker = normalizeTicker($("#new-ticker").val());
        if (!newTicker) return;

        if (!tickers.includes(newTicker)) {
            tickers.push(newTicker);
            localStorage.setItem("tickers", JSON.stringify(tickers));
            addTickerToGrid(newTicker);
            updatePrice(newTicker);
        }

        $("#new-ticker").val("");
    });

    $("#tickers-grid").on("click", ".remove-btn", function () {
        const tickerToRemove = $(this).data("ticker");
        tickers = tickers.filter((t) => t !== tickerToRemove);
        localStorage.setItem("tickers", JSON.stringify(tickers));
        $("#" + tickerToRemove).remove();
        if (!tickers.length) {
            $("#tickers-grid").append('<div class="empty-state"><b>Build your watchlist</b>Add a stock symbol above to see live pricing and forecasts.</div>');
        }
    });

    $("#tickers-grid").on("click", ".detail", function () {
        const stock = $(this).data("ticker");
        localStorage.setItem("stock", stock);
        window.location.href = "/predict/" + encodeURIComponent(stock);
    });

    if (document.getElementById("counter")) {
        startUpdateCycle();
    }
}

function initPredict() {
    const hasDetails = document.getElementById("details");
    if (!hasDetails) return;

    const stock =
        (document.body.dataset.ticker || "").trim().toUpperCase() ||
        localStorage.getItem("stock") ||
        getTickerFromUrl();

    if (stock) {
        renderDetailsBox(stock);
    }

    if (document.getElementById("priceChart") && document.getElementById("nextDayPrediction")) {
        fetchAndRenderPrediction();
    }
}

$(document).ready(function () {
    initHome();
    initMiddle();
    initPredict();
});
