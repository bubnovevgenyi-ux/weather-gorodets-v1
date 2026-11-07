const el = {
  tabs: Array.from(document.querySelectorAll('.period-tab')),
  panel: document.getElementById('forecastPanel'),
  empty: document.getElementById('emptyState'),
  icon: document.getElementById('summaryIcon'),
  condition: document.getElementById('summaryCondition'),
  date: document.getElementById('summaryDate'),
  temp: document.getElementById('summaryTemp'),
  range: document.getElementById('summaryRange'),
  wind: document.getElementById('summaryWind'),
  gust: document.getElementById('summaryGust'),
  grid: document.getElementById('hourlyGrid'),
  chart: document.getElementById('temperatureChart'),
  count: document.getElementById('pointCount'),
  averageWind: document.getElementById('averageWind'),
  maxGust: document.getElementById('maxGust'),
  temperatureRange: document.getElementById('temperatureRange'),
  updatedAt: document.getElementById('updatedAt'),
  demoRibbon: document.getElementById('demoRibbon')
};

let forecastData = { forecasts: {} };

function escapeHtml(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
  });
}

function signed(value) {
  const n = Number(value);
  return (n > 0 ? '+' : '') + (Number.isInteger(n) ? n : n.toFixed(1)) + '°';
}

function weatherSvg(description) {
  const value = String(description || '').toLocaleLowerCase('ru-RU');
  const cloud = '<path d="M13 40h37a11 11 0 0 0 1-22 17 17 0 0 0-32-3 13 13 0 0 0-6 25Z" fill="#80a9c5"/>';
  let shape = cloud;
  if (value.includes('гроз')) {
    shape += '<path d="m34 35-8 11h7l-3 9 13-15h-8l4-5Z" fill="#f0b44e"/>';
  } else if (value.includes('снег')) {
    shape += '<g stroke="#45a8d8" stroke-width="2.4" stroke-linecap="round"><path d="M22 47v9m-4-7 8 5m0-5-8 5M43 47v9m-4-7 8 5m0-5-8 5"/></g>';
  } else if (value.includes('дожд') || value.includes('морос')) {
    shape += '<g stroke="#45a8d8" stroke-width="3" stroke-linecap="round"><path d="m23 46-3 6m15-6-3 6m15-6-3 6"/></g>';
  } else if (value.includes('ясно') || value.includes('солнеч')) {
    shape = '<circle cx="32" cy="26" r="15" fill="#f7bd55"/><g stroke="#f7bd55" stroke-width="3" stroke-linecap="round"><path d="M32 3v6M32 43v6M9 26h6M49 26h6M16 10l5 5m22 22 5 5m0-32-5 5M21 37l-5 5"/></g>';
  } else if (value.includes('перемен')) {
    shape = '<circle cx="43" cy="16" r="11" fill="#f7bd55"/>' + cloud;
  }
  return '<svg class="weather-svg" viewBox="0 0 64 58" aria-hidden="true">' + shape + '</svg>';
}

function formatDate(records) {
  const ts = Number(records[0] && records[0].timestamp);
  if (!Number.isFinite(ts)) return '';
  return new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Moscow', weekday: 'long', day: 'numeric', month: 'long'
  }).format(new Date(ts * 1000));
}

function renderTemperatureChart(records) {
  const values = records.map(function (row) { return Number(row.temperature_c); });
  const min = Math.min.apply(null, values);
  const max = Math.max.apply(null, values);
  const span = Math.max(1, max - min);
  const width = 1000, height = 95, left = 22, right = 978, top = 15, bottom = 72;
  const points = values.map(function (value, index) {
    const x = records.length === 1 ? width / 2 : left + (right - left) * index / (records.length - 1);
    const y = bottom - ((value - min) / span) * (bottom - top);
    return { x: x, y: y, value: value, label: records[index].time };
  });
  const line = points.map(function (point, index) {
    return (index ? 'L' : 'M') + point.x + ',' + point.y;
  }).join(' ');
  const last = points[points.length - 1];
  const first = points[0];
  const area = line + ' L' + last.x + ',' + (bottom + 9) + ' L' + first.x + ',' + (bottom + 9) + ' Z';
  let guides = '';
  for (let i = 0; i < 3; i += 1) {
    const y = top + i * (bottom - top) / 2;
    guides += '<line x1="' + left + '" y1="' + y + '" x2="' + right + '" y2="' + y + '" stroke="#eaf1f6" stroke-dasharray="4 7"/>';
  }
  let marks = '';
  points.forEach(function (point) {
    marks += '<circle cx="' + point.x + '" cy="' + point.y + '" r="5.5" fill="#fff" stroke="#1686ce" stroke-width="3"/>';
    marks += '<text x="' + point.x + '" y="' + (point.y - 12) + '" text-anchor="middle" fill="#4a7596" font-size="12" font-weight="700">' + (point.value > 0 ? '+' : '') + point.value + '°</text>';
    marks += '<text x="' + point.x + '" y="94" text-anchor="middle" fill="#9aabba" font-size="10">' + escapeHtml(point.label) + '</text>';
  });
  el.chart.innerHTML = '<svg viewBox="0 0 ' + width + ' ' + height + '" preserveAspectRatio="none" role="img" aria-label="Изменение температуры">' +
    '<defs><linearGradient id="tempFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#52b8e6" stop-opacity=".22"/><stop offset="1" stop-color="#52b8e6" stop-opacity="0"/></linearGradient></defs>' +
    guides + '<path d="' + area + '" fill="url(#tempFill)"/><path d="' + line + '" fill="none" stroke="#218ed0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>' + marks + '</svg>';
}

function renderPeriod(period) {
  el.tabs.forEach(function (tab) {
    const active = tab.dataset.period === period;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
  });
  const periodData = forecastData.forecasts && forecastData.forecasts[period];
  const records = periodData && periodData.hours
    ? Object.values(periodData.hours).sort(function (a, b) { return Number(a.timestamp) - Number(b.timestamp); })
    : [];

  if (!records.length) {
    el.panel.hidden = true;
    el.empty.hidden = false;
    el.empty.querySelector('h2').textContent = period === 'today' ? 'Нет данных на сегодня' : 'Нет данных на завтра';
    return;
  }

  el.panel.hidden = false;
  el.empty.hidden = true;
  const temps = records.map(function (row) { return Number(row.temperature_c); });
  const winds = records.map(function (row) { return Number(row.wind_speed_ms); });
  const gusts = records.map(function (row) { return Number(row.wind_gust_ms); });
  const minTemp = Math.min.apply(null, temps);
  const maxTemp = Math.max.apply(null, temps);
  const averageWind = winds.reduce(function (sum, value) { return sum + value; }, 0) / winds.length;
  const maxGust = Math.max.apply(null, gusts);
  const first = records[0];
  const label = periodData.label || (period === 'today' ? 'Погода сегодня' : 'Погода завтра');

  el.icon.innerHTML = weatherSvg(first.sky);
  el.condition.textContent = first.sky || 'Погодные условия';
  el.date.textContent = label + ' · ' + formatDate(records);
  el.temp.textContent = signed(first.temperature_c);
  el.range.innerHTML = 'Мин. ' + signed(minTemp) + ' <i></i> Макс. ' + signed(maxTemp);
  el.wind.textContent = averageWind.toFixed(1) + ' м/с';
  el.gust.textContent = 'Порывы до ' + maxGust.toFixed(1) + ' м/с';
  el.count.textContent = records.length + ' временных точек';
  el.averageWind.textContent = averageWind.toFixed(1) + ' м/с';
  el.maxGust.textContent = maxGust.toFixed(1) + ' м/с';
  el.temperatureRange.textContent = signed(minTemp) + ' … ' + signed(maxTemp);

  let cards = '';
  records.forEach(function (row) {
    cards += '<article class="hour-cell">' +
      '<div class="hour-time">' + escapeHtml(row.time) + '</div>' +
      '<div class="hour-icon" aria-hidden="true">' + weatherSvg(row.sky) + '</div>' +
      '<div class="hour-temp">' + signed(row.temperature_c) + '</div>' +
      '<div class="hour-sky">' + escapeHtml(row.sky || '—') + '</div>' +
      '<div class="hour-divider"></div>' +
      '<div class="hour-wind">Ветер ' + Number(row.wind_speed_ms).toFixed(0) + ' м/с</div>' +
      '<div class="hour-gust">Порывы ' + Number(row.wind_gust_ms).toFixed(0) + ' м/с</div>' +
      '</article>';
  });
  el.grid.innerHTML = cards;
  el.panel.setAttribute('aria-labelledby', period === 'today' ? 'tab-today' : 'tab-tomorrow');
  renderTemperatureChart(records);
}

async function init() {
  const isDemo = new URLSearchParams(location.search).get('demo') === '1';
  const dataUrl = isDemo ? 'demo_weather.json' : '../data/weather.json';
  try {
    const response = await fetch(dataUrl, { cache: 'no-store' });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    forecastData = await response.json();
    if (isDemo) {
      el.demoRibbon.hidden = false;
      el.updatedAt.textContent = 'Демонстрационные данные · макет интерфейса';
    } else {
      const updated = forecastData.fetched_at_utc ? new Date(forecastData.fetched_at_utc) : null;
      el.updatedAt.textContent = updated && !Number.isNaN(updated.valueOf())
        ? 'Получено ' + updated.toLocaleString('ru-RU')
        : 'Данные прогноза';
    }
  } catch (error) {
    console.warn('Weather JSON is not available:', error);
    el.updatedAt.textContent = 'Ожидает data/weather.json';
    forecastData = { forecasts: {} };
  }
  el.tabs.forEach(function (tab) {
    tab.addEventListener('click', function () { renderPeriod(tab.dataset.period); });
  });
  renderPeriod('today');
}

window.forecastUiReady = false;
init().finally(function () { window.forecastUiReady = true; });
