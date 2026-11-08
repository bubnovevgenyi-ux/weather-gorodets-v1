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
  chartTitle: document.getElementById('chartTitle'),
  count: document.getElementById('pointCount'),
  averageWind: document.getElementById('averageWind'),
  maxGust: document.getElementById('maxGust'),
  temperatureRange: document.getElementById('temperatureRange'),
  updatedAt: document.getElementById('updatedAt'),
  demoRibbon: document.getElementById('demoRibbon'),
  sourceText: document.getElementById('cardSourceText'),
  sectionKicker: document.getElementById('sectionKicker'),
  sectionTitle: document.getElementById('sectionTitle')
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

function isDailyPeriod(period) {
  return period === '10_days' || period === '2_weeks';
}

function temperatureBand(row) {
  const single = row.temperature_c == null ? null : Number(row.temperature_c);
  const low = row.temperature_min_c == null ? single : Number(row.temperature_min_c);
  const high = row.temperature_max_c == null ? single : Number(row.temperature_max_c);
  return { low: low, high: high };
}

function chartTemperature(row, daily) {
  const band = temperatureBand(row);
  if (daily && band.low != null && band.high != null) return (band.low + band.high) / 2;
  return Number(row.temperature_c);
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

function formatDay(dateValue, options) {
  if (!dateValue) return '';
  const date = new Date(String(dateValue) + 'T12:00:00');
  if (Number.isNaN(date.valueOf())) return String(dateValue);
  return new Intl.DateTimeFormat('ru-RU', Object.assign({
    timeZone: 'Europe/Moscow'
  }, options || {})).format(date);
}

function formatHourlyDate(records) {
  const ts = Number(records[0] && records[0].timestamp);
  if (!Number.isFinite(ts)) return '';
  return new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Moscow', weekday: 'long', day: 'numeric', month: 'long'
  }).format(new Date(ts * 1000));
}

function formatPeriodDate(records, daily) {
  if (!daily) return formatHourlyDate(records);
  const first = formatDay(records[0].date, { day: 'numeric', month: 'long' });
  const last = formatDay(records[records.length - 1].date, { day: 'numeric', month: 'long' });
  return first === last ? first : first + ' — ' + last;
}

function renderTemperatureChart(records, daily) {
  const values = records.map(function (row) { return chartTemperature(row, daily); });
  const labels = records.map(function (row) {
    return daily ? formatDay(row.date, { day: 'numeric', month: 'short' }) : row.time;
  });
  const min = Math.min.apply(null, values);
  const max = Math.max.apply(null, values);
  const span = Math.max(1, max - min);
  const width = 1000, height = 95, left = 22, right = 978, top = 15, bottom = 72;
  const points = values.map(function (value, index) {
    const x = records.length === 1 ? width / 2 : left + (right - left) * index / (records.length - 1);
    const y = bottom - ((value - min) / span) * (bottom - top);
    return { x: x, y: y, value: value, label: labels[index] };
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
    marks += '<text x="' + point.x + '" y="' + (point.y - 12) + '" text-anchor="middle" fill="#4a7596" font-size="12" font-weight="700">' + (point.value > 0 ? '+' : '') + point.value.toFixed(1).replace(/\.0$/, '') + '°</text>';
    marks += '<text x="' + point.x + '" y="94" text-anchor="middle" fill="#9aabba" font-size="10">' + escapeHtml(point.label) + '</text>';
  });
  el.chart.innerHTML = '<svg viewBox="0 0 ' + width + ' ' + height + '" preserveAspectRatio="none" role="img" aria-label="Изменение температуры">' +
    '<defs><linearGradient id="tempFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#52b8e6" stop-opacity=".22"/><stop offset="1" stop-color="#52b8e6" stop-opacity="0"/></linearGradient></defs>' +
    guides + '<path d="' + area + '" fill="url(#tempFill)"/><path d="' + line + '" fill="none" stroke="#218ed0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>' + marks + '</svg>';
}

function renderPeriod(period) {
  const daily = isDailyPeriod(period);
  el.tabs.forEach(function (tab) {
    const active = tab.dataset.period === period;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
  });

  const periodData = forecastData.forecasts && forecastData.forecasts[period];
  const collectionKey = daily ? 'days' : 'hours';
  const records = periodData && periodData[collectionKey]
    ? Object.values(periodData[collectionKey]).sort(function (a, b) {
      return Number(a.timestamp) - Number(b.timestamp);
    })
    : [];

  if (!records.length) {
    el.panel.hidden = true;
    el.empty.hidden = false;
    const emptyLabels = {
      today: 'Нет данных на сегодня',
      tomorrow: 'Нет данных на завтра',
      '10_days': 'Нет данных прогноза на 10 дней',
      '2_weeks': 'Нет данных прогноза на 2 недели'
    };
    el.empty.querySelector('h2').textContent = emptyLabels[period] || 'Нет данных прогноза';
    return;
  }

  el.panel.hidden = false;
  el.empty.hidden = true;
  const bands = records.map(temperatureBand);
  const lows = bands.map(function (band) { return band.low; }).filter(Number.isFinite);
  const highs = bands.map(function (band) { return band.high; }).filter(Number.isFinite);
  const minTemp = Math.min.apply(null, lows);
  const maxTemp = Math.max.apply(null, highs);
  const winds = records.map(function (row) { return Number(row.wind_speed_ms); });
  const gusts = records.map(function (row) { return Number(row.wind_gust_ms); });
  const averageWind = winds.reduce(function (sum, value) { return sum + value; }, 0) / winds.length;
  const maxGust = Math.max.apply(null, gusts);
  const first = records[0];
  const firstBand = bands[0];
  const label = periodData.label || period;
  const firstTemperatureText = daily && firstBand.low != null && firstBand.high != null && firstBand.low !== firstBand.high
    ? signed(firstBand.low) + ' … ' + signed(firstBand.high)
    : signed(firstBand.low != null ? firstBand.low : first.temperature_c);

  el.icon.innerHTML = weatherSvg(first.sky);
  el.condition.textContent = first.sky || 'Погодные условия';
  el.date.textContent = label + ' · ' + formatPeriodDate(records, daily);
  el.temp.textContent = firstTemperatureText;
  el.temp.classList.toggle('is-range', daily && firstBand.low !== firstBand.high);
  el.range.innerHTML = 'Мин. ' + signed(minTemp) + ' <i></i> Макс. ' + signed(maxTemp);
  el.wind.textContent = averageWind.toFixed(1) + ' м/с';
  el.gust.textContent = 'Порывы до ' + maxGust.toFixed(1) + ' м/с';
  el.count.textContent = daily ? records.length + ' дней прогноза' : records.length + ' временных точек';
  el.averageWind.textContent = averageWind.toFixed(1) + ' м/с';
  el.maxGust.textContent = maxGust.toFixed(1) + ' м/с';
  el.temperatureRange.textContent = signed(minTemp) + ' … ' + signed(maxTemp);
  el.sourceText.textContent = daily ? 'Прогноз по дням' : 'Почасовой прогноз';
  el.sectionKicker.textContent = daily ? 'ПО ДНЯМ' : 'ПО ВРЕМЕНИ';
  el.sectionTitle.textContent = daily ? 'Прогноз на каждый день' : 'Изменение погоды';
  el.chartTitle.textContent = daily ? 'Дневная температура (середина диапазона)' : 'Температура воздуха';
  el.grid.classList.toggle('daily-grid', daily);

  let cards = '';
  records.forEach(function (row, index) {
    const band = bands[index];
    const temperatureText = daily && band.low != null && band.high != null && band.low !== band.high
      ? signed(band.low) + ' / ' + signed(band.high)
      : signed(band.low != null ? band.low : row.temperature_c);
    const dateOrTime = daily
      ? formatDay(row.date, { weekday: 'short', day: 'numeric', month: 'short' })
      : row.time;
    const direction = row.wind_direction ? ' · ' + escapeHtml(row.wind_direction) : '';
    cards += '<article class="hour-cell' + (daily ? ' day-cell' : '') + '">' +
      '<div class="hour-time">' + escapeHtml(dateOrTime) + '</div>' +
      '<div class="hour-icon" aria-hidden="true">' + weatherSvg(row.sky) + '</div>' +
      '<div class="hour-temp">' + temperatureText + '</div>' +
      '<div class="hour-sky">' + escapeHtml(row.sky || '—') + '</div>' +
      '<div class="hour-divider"></div>' +
      '<div class="hour-wind">Ветер ' + Number(row.wind_speed_ms).toFixed(0) + ' м/с' + direction + '</div>' +
      '<div class="hour-gust">Порывы ' + Number(row.wind_gust_ms).toFixed(0) + ' м/с</div>' +
      '</article>';
  });
  el.grid.innerHTML = cards;
  el.panel.setAttribute('aria-labelledby', 'tab-' + period.replace('_', '-'));
  renderTemperatureChart(records, daily);
}

async function init() {
  const isDemo = new URLSearchParams(location.search).get('demo') === '1';
  const dataUrl = isDemo ? 'demo_weather.json' : '/api/v1/forecast';
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
    el.updatedAt.textContent = 'API пока не отдаёт прогноз';
    forecastData = { forecasts: {} };
  }
  el.tabs.forEach(function (tab) {
    tab.addEventListener('click', function () { renderPeriod(tab.dataset.period); });
  });
  renderPeriod('today');
}

window.forecastUiReady = false;
init().finally(function () { window.forecastUiReady = true; });
