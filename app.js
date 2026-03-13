/* ═══════════════════════════════════════════════════════════════
   Élephante Stock Analyzer — Core JavaScript
   ═══════════════════════════════════════════════════════════════ */

// ── Sidebar Toggle ──────────────────────────────────────────

document.getElementById('sidebarToggle').addEventListener('click', function () {
    document.getElementById('sidebar').classList.toggle('open');
});

document.querySelector('.content-area').addEventListener('click', function () {
    document.getElementById('sidebar').classList.remove('open');
});


// ── Global Search ───────────────────────────────────────────

const globalSearch = document.getElementById('globalSearch');
const searchResults = document.getElementById('searchResults');
let searchTimeout = null;

globalSearch.addEventListener('input', function () {
    clearTimeout(searchTimeout);
    const query = this.value.trim();

    if (query.length < 1) {
        searchResults.classList.remove('active');
        return;
    }

    searchTimeout = setTimeout(() => {
        fetch(`/api/search?q=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(data => {
                if (!data.length) {
                    searchResults.classList.remove('active');
                    return;
                }
                searchResults.innerHTML = data.map(item => `
                    <div class="search-result-item" onclick="window.location.href='/stock/${item.symbol}'">
                        <span class="sr-symbol">${item.symbol}</span>
                        <span class="sr-name">${item.name}</span>
                    </div>
                `).join('');
                searchResults.classList.add('active');
            });
    }, 250);
});

globalSearch.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
        const query = this.value.trim().toUpperCase();
        if (query) {
            window.location.href = `/stock/${query}`;
        }
    }
    if (e.key === 'Escape') {
        searchResults.classList.remove('active');
        this.blur();
    }
});

document.addEventListener('click', function (e) {
    if (!e.target.closest('.sidebar-search')) {
        searchResults.classList.remove('active');
    }
});

document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        globalSearch.focus();
    }
});


// ── Quick Trade Modal ───────────────────────────────────────

let quickTradeType = 'stock';
let qtOptChainCache = null;

function openQuickTrade() {
    document.getElementById('quickTradeModal').classList.add('active');
    document.getElementById('tradeTicker').focus();
}

function closeQuickTrade() {
    document.getElementById('quickTradeModal').classList.remove('active');
    document.getElementById('tradePreview').innerHTML = '';
}

function setQuickTradeType(type, btn) {
    quickTradeType = type;
    document.querySelectorAll('#quickTradeModal .toggle-group:first-of-type .toggle-btn')
        .forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('stockTradeFields').style.display = type === 'stock' ? 'block' : 'none';
    document.getElementById('optionTradeFields').style.display = type === 'option' ? 'block' : 'none';
    document.getElementById('tradePreview').innerHTML = '';

    if (type === 'option') {
        const ticker = document.getElementById('tradeTicker').value.trim().toUpperCase();
        if (ticker) loadQuickOptExpirations();
    }
}

document.getElementById('tradeTicker').addEventListener('input', function () {
    updateQuickTradePreview();
    if (quickTradeType === 'option') loadQuickOptExpirations();
});
document.getElementById('tradeQuantity').addEventListener('input', updateQuickTradePreview);
document.getElementById('tradeAction').addEventListener('change', function() {
    updateQuickTradePreview();
    updateOrderHint();
});

function loadQuickOptExpirations() {
    const ticker = document.getElementById('tradeTicker').value.trim().toUpperCase();
    const sel = document.getElementById('qtOptExp');
    if (!ticker) {
        sel.innerHTML = '<option value="">Enter ticker first</option>';
        return;
    }
    sel.innerHTML = '<option value="">Loading...</option>';
    fetch(`/api/stock/${ticker}/options/expirations`)
        .then(r => r.json())
        .then(data => {
            if (!data.length) {
                sel.innerHTML = '<option value="">No options</option>';
                return;
            }
            sel.innerHTML = data.map(d => `<option value="${d}">${d}</option>`).join('');
            loadQuickOptStrikes();
        });
}

function loadQuickOptStrikes() {
    const ticker = document.getElementById('tradeTicker').value.trim().toUpperCase();
    const exp = document.getElementById('qtOptExp').value;
    const sel = document.getElementById('qtOptStrike');
    if (!ticker || !exp) return;

    sel.innerHTML = '<option value="">Loading...</option>';
    fetch(`/api/stock/${ticker}/options?expiration=${exp}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                sel.innerHTML = '<option value="">Error</option>';
                return;
            }
            qtOptChainCache = data;
            const optType = document.getElementById('qtOptType').value;
            const side = optType === 'CALL' ? data.calls : data.puts;
            sel.innerHTML = side.map(o => {
                const itm = o.itm ? ' (ITM)' : '';
                return `<option value="${o.strike}">$${o.strike.toFixed(2)}${itm} — Ask $${o.ask.toFixed(2)}</option>`;
            }).join('');
        });
}

document.getElementById('qtOptType')?.addEventListener('change', loadQuickOptStrikes);

function updateQuickTradePreview() {
    if (quickTradeType !== 'stock') return;
    const ticker = document.getElementById('tradeTicker').value.trim().toUpperCase();
    const qty = parseFloat(document.getElementById('tradeQuantity').value) || 0;
    const action = document.getElementById('tradeAction').value;
    const preview = document.getElementById('tradePreview');

    if (!ticker || !qty) {
        preview.innerHTML = '';
        return;
    }

    fetch(`/api/stock/${ticker}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                preview.innerHTML = `<p class="error-text" style="font-size: 0.82rem;">${data.error}</p>`;
                return;
            }
            const total = qty * data.price;
            preview.innerHTML = `
                <div class="trade-estimate">
                    <div class="estimate-line">
                        <span>${action} ${qty} ${data.symbol} @ $${data.price.toFixed(2)}</span>
                        <strong>$${formatNumber(total)}</strong>
                    </div>
                </div>`;
        })
        .catch(() => { preview.innerHTML = ''; });
}

function onOrderTypeChange() {
    const ot = document.getElementById('tradeOrderType').value;
    const triggerFields = document.getElementById('orderTriggerFields');
    const triggerPriceGroup = document.getElementById('triggerPriceGroup');
    const trailPercentGroup = document.getElementById('trailPercentGroup');

    if (ot === 'MARKET') {
        triggerFields.style.display = 'none';
    } else {
        triggerFields.style.display = 'block';
        if (ot === 'TRAILING_STOP') {
            triggerPriceGroup.style.display = 'none';
            trailPercentGroup.style.display = 'block';
        } else {
            triggerPriceGroup.style.display = 'block';
            trailPercentGroup.style.display = 'none';
        }
    }
    updateOrderHint();
}

function updateOrderHint() {
    const ot = document.getElementById('tradeOrderType').value;
    const action = document.getElementById('tradeAction').value;
    const hint = document.getElementById('orderHint');
    if (!hint) return;

    const hints = {
        'STOP_LOSS': action === 'SELL'
            ? 'Automatically sells when the price drops to your trigger price to limit losses.'
            : 'Automatically buys when the price rises to your trigger price.',
        'TAKE_PROFIT': action === 'SELL'
            ? 'Automatically sells when the price rises to your trigger price to lock in gains.'
            : 'Automatically buys when the price drops to your trigger price.',
        'TRAILING_STOP': 'Follows the price upward and triggers a sell if the price drops by the trail percentage from its peak.',
        'MARKET': '',
    };
    hint.textContent = hints[ot] || '';
    hint.style.display = hints[ot] ? 'block' : 'none';
}

function executeTrade() {
    const ticker = document.getElementById('tradeTicker').value.trim().toUpperCase();
    const notes = document.getElementById('tradeNotes').value.trim();
    const btn = document.getElementById('executeTrade');

    if (!ticker) {
        showToast('Please enter a ticker', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner-sm"></div> Executing...';

    if (quickTradeType === 'option') {
        const optType = document.getElementById('qtOptType').value;
        const action = document.getElementById('qtOptAction').value;
        const exp = document.getElementById('qtOptExp').value;
        const strike = parseFloat(document.getElementById('qtOptStrike').value);
        const contracts = parseInt(document.getElementById('qtOptContracts').value);

        if (!exp || !strike || !contracts) {
            showToast('Please fill out all options fields', 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> Execute Trade';
            return;
        }

        fetch('/api/options/trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, option_type: optType, strike, expiration: exp, action, contracts, notes })
        })
            .then(r => r.json())
            .then(data => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Execute Trade';
                if (data.success) {
                    showToast(data.message, 'success');
                    closeQuickTrade();
                    if (typeof loadPortfolioSnapshot === 'function') loadPortfolioSnapshot();
                    if (typeof loadRecentTrades === 'function') loadRecentTrades();
                } else {
                    showToast(data.error, 'error');
                }
            })
            .catch(err => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Execute Trade';
                showToast('Trade failed: ' + err.message, 'error');
            });
    } else {
        const action = document.getElementById('tradeAction').value;
        const quantity = parseFloat(document.getElementById('tradeQuantity').value);
        const orderType = document.getElementById('tradeOrderType').value;

        if (!quantity) {
            showToast('Please enter a quantity', 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> Execute Trade';
            return;
        }

        if (orderType !== 'MARKET') {
            const triggerPrice = parseFloat(document.getElementById('tradeTriggerPrice').value) || null;
            const trailPercent = parseFloat(document.getElementById('tradeTrailPercent').value) || null;

            if (orderType !== 'TRAILING_STOP' && !triggerPrice) {
                showToast('Please enter a trigger price', 'error');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Execute Trade';
                return;
            }
            if (orderType === 'TRAILING_STOP' && !trailPercent) {
                showToast('Please enter a trail percentage', 'error');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Execute Trade';
                return;
            }

            fetch('/api/orders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticker, action, quantity, order_type: orderType,
                    trigger_price: triggerPrice, trail_percent: trailPercent, notes
                })
            })
                .then(r => r.json())
                .then(data => {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-check"></i> Execute Trade';
                    if (data.success) {
                        showToast(data.message, 'success');
                        closeQuickTrade();
                        document.getElementById('tradeTicker').value = '';
                        document.getElementById('tradeQuantity').value = '';
                        document.getElementById('tradeNotes').value = '';
                        document.getElementById('tradeOrderType').value = 'MARKET';
                        onOrderTypeChange();
                        if (typeof loadActiveOrders === 'function') loadActiveOrders();
                    } else {
                        showToast(data.error, 'error');
                    }
                })
                .catch(err => {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-check"></i> Execute Trade';
                    showToast('Order failed: ' + err.message, 'error');
                });
            return;
        }

        fetch('/api/trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, action, quantity, notes })
        })
            .then(r => r.json())
            .then(data => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Execute Trade';
                if (data.success) {
                    showToast(data.message, 'success');
                    closeQuickTrade();
                    document.getElementById('tradeTicker').value = '';
                    document.getElementById('tradeQuantity').value = '';
                    document.getElementById('tradeNotes').value = '';
                    if (typeof loadPortfolioSnapshot === 'function') loadPortfolioSnapshot();
                    if (typeof loadRecentTrades === 'function') loadRecentTrades();
                } else {
                    showToast(data.error, 'error');
                }
            })
            .catch(err => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Execute Trade';
                showToast('Trade failed: ' + err.message, 'error');
            });
    }
}

document.getElementById('quickTradeModal').addEventListener('click', function (e) {
    if (e.target === this) closeQuickTrade();
});

document.getElementById('addWatchlistModal')?.addEventListener('click', function (e) {
    if (e.target === this) this.classList.remove('active');
});


// ── Toast Notifications ─────────────────────────────────────

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const icons = { success: 'check-circle', error: 'exclamation-circle', info: 'info-circle' };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fas fa-${icons[type] || 'info-circle'}"></i> ${message}`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}


// ── Number Formatting ───────────────────────────────────────

function formatNumber(num) {
    if (num === null || num === undefined) return '0.00';
    return parseFloat(num).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatLargeNumber(num) {
    if (!num) return 'N/A';
    if (num >= 1e12) return (num / 1e12).toFixed(2) + 'T';
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
    return num.toLocaleString();
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}


// ── Market Status ───────────────────────────────────────────

function updateMarketStatus() {
    const now = new Date();
    const ny = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const day = ny.getDay();
    const hours = ny.getHours();
    const minutes = ny.getMinutes();
    const time = hours * 60 + minutes;

    const statusEl = document.getElementById('marketStatus');
    const isWeekday = day >= 1 && day <= 5;
    const isOpen = isWeekday && time >= 570 && time < 960; // 9:30 AM - 4:00 PM ET

    if (isOpen) {
        statusEl.className = 'market-status open';
        statusEl.querySelector('.status-text').textContent = 'Market Open';
    } else {
        statusEl.className = 'market-status closed';
        const nextOpen = getNextMarketOpen(ny);
        statusEl.querySelector('.status-text').textContent = `Market Closed · Opens ${nextOpen}`;
    }
}

function getNextMarketOpen(now) {
    const day = now.getDay();
    const hours = now.getHours();
    const time = hours * 60 + now.getMinutes();

    if (day >= 1 && day <= 5 && time < 570) {
        return 'today 9:30 AM ET';
    }

    let daysUntilMonday;
    if (day === 0) daysUntilMonday = 1;
    else if (day === 6) daysUntilMonday = 2;
    else if (time >= 960) {
        daysUntilMonday = day === 5 ? 3 : 1;
        if (daysUntilMonday === 1) return 'tomorrow 9:30 AM ET';
    } else {
        return 'today 9:30 AM ET';
    }

    if (daysUntilMonday <= 1) return 'tomorrow 9:30 AM ET';
    return `Monday 9:30 AM ET`;
}

updateMarketStatus();
setInterval(updateMarketStatus, 60000);
