var tickers = JSON.parse(localStorage.getItem('tickers')) || [];
var lastPrices = {};
var counter = 13;

function startUpdateCycle() {
    updatePrices();
    setInterval(function() {
        counter--;
        $('#counter').text(counter);
        if (counter <= 0) {
            updatePrices();
            counter = 13;
        }
    }, 1000);
}




// =======================
// Prediction + Chart (new.html)
// =======================
(function () {
  function getTickerFromPage() {
    try {
      const t = (document.body && document.body.dataset && document.body.dataset.ticker) || "";
      if (t && String(t).trim()) return String(t).trim().toUpperCase();
    } catch (e) {}

    // fallback: /predict/TICKER
    try {
      const parts = (window.location.pathname || "").split("/").filter(Boolean);
      const idx = parts.indexOf("predict");
      if (idx >= 0 && parts[idx + 1]) return decodeURIComponent(parts[idx + 1]).toUpperCase();
    } catch (e) {}

    // fallback localStorage
    try {
      const s = localStorage.getItem("stock");
      if (s) return String(s).trim().toUpperCase();
    } catch (e) {}

    return "";
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
    if (el) el.textContent = val.toFixed(2);
  }

  let priceChart = null;

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

    const labels = Array.from({ length: n + m }, (_, i) => i + 1);
    const actualSeries = actual.concat(Array.from({ length: m }, () => null));
    const predSeries = Array.from({ length: n }, () => null).concat(
      predicted.length ? predicted : [null]
    );

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
            borderWidth: 2,
          },
          {
            label: `${ticker} (Predicted)`,
            data: predSeries,
            tension: 0.25,
            pointRadius: 2,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { x: { display: true }, y: { display: true } },
      },
    });
  }

  async function fetchAndRenderPrediction() {
    const ticker = getTickerFromPage();
    if (!ticker) return;

    const err = document.getElementById("chartError");
    if (err) err.textContent = "";

    const url = (window.PREDICT_API_URL || "").trim();
    if (!url) {
      if (err) err.textContent = "Prediction API URL not set";
      return;
    }

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
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

      // Supports API Gateway payload from your Python Lambda:
      // { ticker, last_60_actual: [...], predicted: [...], next_price: n }
      // and also the older shape:
      // { ticker, actual_prices: [...], predicted_prices: [...] }
      const actual = safeNums(data.last_60_actual || data.actual_prices || data.actual || []);
      const predicted = safeNums(data.predicted || data.predicted_prices || []);

      const next =
        Number.isFinite(data.next_price) ? Number(data.next_price) :
        Number.isFinite(data.predicted_next_close) ? Number(data.predicted_next_close) :
        (predicted.length ? predicted[predicted.length - 1] : NaN);

      if (Number.isFinite(next)) setNextDayPrediction(next);

      if (!actual.length) {
        if (err) err.textContent = "No actual prices returned";
        return;
      }

      renderPriceChart(ticker, actual, predicted.length ? predicted : (Number.isFinite(next) ? [next] : []));
    } catch (e) {
      if (err) err.textContent = "Failed to call prediction API";
      console.error(e);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    // Only run on the details page
    if (document.getElementById("priceChart") && document.getElementById("nextDayPrediction")) {
      fetchAndRenderPrediction();
    }
  });
})();

function getTickerFromUrl() {
    // supports routes like /predict/AAPL
    try {
        const parts = (window.location.pathname || "").split("/").filter(Boolean);
        const idx = parts.indexOf("predict");
        if (idx >= 0 && parts[idx + 1]) return decodeURIComponent(parts[idx + 1]);
    } catch (e) {}
    return null;
}

// second-page.js

$(document).ready(function() {
    // Retrieve the stock ticker from localStorage (or from URL like /predict/AAPL)
    const stock = localStorage.getItem('stock') || getTickerFromUrl();

    if (stock) {
        // Show quote box (prediction/chart is handled by the IIFE above on DOMContentLoaded)
        ticker(stock);
    }
});

// Function to display the stock information
function ticker(ticker) {
    $('#details').append(`
        <div id="${ticker}" class="box">
            <h2>${ticker}</h2><br>
            <p id="${ticker}-price"></p><br>
            <p id="${ticker}-pct"></p>
        </div>
    `);

    // Optionally, clear the stored stock after use
    localStorage.removeItem('stock');

    // Call updatePrices to fetch and display the latest prices
    updatePrice(ticker);
}

function updatePrice(ticker) {
    $.ajax({
        url: '/get_stock_data',
        type: 'POST',
        data: JSON.stringify({ 'ticker': ticker.replace(/\$/g, '').toUpperCase() }),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json',
        success: function (data) {
            if (data.error) {
                console.error(`Error fetching ${ticker}: ${data.error}`);
                return;
            }

            var changePercent = ((data.currentPrice - data.openPrice) / data.openPrice) * 100;
            var colorClass = changePercent <= -2 ? 'dark-red' : changePercent < 0 ? 'red' : changePercent <= 2 ? 'green' : 'dark-green';

            $(`#${ticker}-price`).text(`$${data.currentPrice.toFixed(2)}`);
            $(`#${ticker}-pct`).text(`${changePercent.toFixed(2)}%`);
            $(`#${ticker}-price, #${ticker}-pct`).removeClass('dark-red red green dark-green').addClass(colorClass);
        },
        error: function (xhr, status, error) {
            console.error(`Error fetching ${ticker}: ${xhr.responseText}`);
        }
    });
}


$(document).ready(function(){
    // Only run the grid logic on pages that actually have the grid
    if (!document.getElementById('tickers-grid')) return;

    tickers.forEach(function(ticker){
        addTickerToGrid(ticker);
    });

    updatePrices();

    $('#add-ticker-form').submit(function(e){
        e.preventDefault();
        var newTicker = $('#new-ticker').val().toUpperCase();
        if(!tickers.includes(newTicker)){
            tickers.push(newTicker);
            localStorage.setItem('tickers', JSON.stringify(tickers))
            addTickerToGrid(newTicker)
        }
        $('#new-ticker').val('');
        updatePrices();
        window.location.href = '/middle';
    });

    $('#tickers-grid').on('click', '.remove-btn', function(){
        var tickerToRemove = $(this).data('ticker');
        tickers = tickers.filter(t => t !== tickerToRemove);
        localStorage.setItem('tickers', JSON.stringify(tickers))
        $('#' + tickerToRemove).remove();
    }); 

    $('#tickers-grid').on('click', '.detail', function(){
        var stock = $(this).data('ticker');
        // Store the selected stock symbol in localStorage
        localStorage.setItem('stock', stock);
        // Redirect to second-page.html
        window.location.href = '/predict/'+stock;  // Redirect to the details page
    });

    if (document.getElementById('counter')) {
        startUpdateCycle();
    }
});

function addTickerToGrid(ticker) {
    $('#tickers-grid').append(`<div id="${ticker}" 
        class="stock-box"> 
        <h2>${ticker}</h2><br> 
        <p id="${ticker}-price"></p> <br> 
        <p id="${ticker}-pct"></p><br>
        <button class="detail" data-ticker="${ticker}">detail</button> 
        <button class="remove-btn" data-ticker="${ticker}">X</button></div>`);
}

function updatePrices() {
    tickers.forEach(function(ticker) {
        $.ajax({
            url: '/get_stock_data',
            type: 'POST',
            data: JSON.stringify({'ticker': ticker}),
            contentType: 'application/json; charset=utf-8',
            dataType: 'json',
            success: function(data) {
                var changePercent = ((data.currentPrice - data.openPrice) / data.openPrice) * 100;
                var colorClass;
                if (changePercent <= -2) {
                    colorClass = 'dark-red'
                } else if (changePercent < 0) {
                    colorClass = 'red'
                } else if (changePercent <= 2) {
                    colorClass = 'green'
                } else {
                    colorClass = 'dark-green'
                }

                $(`#${ticker}-price`).text(`$${data.currentPrice.toFixed(2)}`);
                $(`#${ticker}-pct`).text(`${changePercent.toFixed(2)}%`);
                $(`#${ticker}-price`).removeClass('dark-red red green dark-green').addClass(colorClass);
                $(`#${ticker}-pct`).removeClass('dark-red red green dark-green').addClass(colorClass);

                var flashClass;
                if (lastPrices[ticker] > data.currentPrice) {
                    flashClass = 'red-flash';
                } else if (lastPrices[ticker] < data.currentPrice) {
                    flashClass = 'green-flash';
                }

                lastPrices[ticker] = data.currentPrice;

                $('#' + ticker).addClass(flashClass); 
                setTimeout(function() { 
                    $('#' + ticker).removeClass(flashClass); 
                }, 1000);
            }
        });
    });
}
