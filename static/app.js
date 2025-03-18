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


// second-page.js

$(document).ready(function() {
    // Retrieve the stock ticker from localStorage
    const stock = localStorage.getItem('stock');

    if (stock) {
        // Call the ticker function with the retrieved stock
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
    updatePrice();
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
        window.location.href = '/new/'+stock;  // Redirect to the details page
    });

    startUpdateCycle();
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
