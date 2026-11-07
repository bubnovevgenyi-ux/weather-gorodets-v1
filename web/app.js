const elements = {
  tabs: [...document.querySelectorAll(".period-tab")],
  panel: document.getElementById("forecastPanel"),
  empty: document.getElementById("emptyState"),
  icon: document.getElementById("summaryIcon"),
  condition: document.getElementById("summaryCondition"),
  date: document.getElementById("summaryDate"),
  temp: document.getElementById("summaryTemp"),
  range: document.getElementById("summaryRange"),
  wind: document.getElementById("summaryWind"),
  gust: document.getElementById("summaryGust"),
  grid: document.getElementById("hourlyGrid"),
  chart: document.getElementById("temperatureChart"),
  count: document.getElementById("pointCount"),
  averageWind: document.getElementById("averageWind"),
  maxGust: document.getElementById("maxGust"),
  temperatureRange: document.getElementById("temperatureRange"),
  updatedAt: document.getElementById("updatedAt"),
  demoRibbon: document.getElementById("demoRibbon")
};

let forecastData = null;
let activePeriod = "today";

function conditionSvg(description = "") {
  const value = description.toLocaleLowerCase("ru-RU");
  const cloud = '<path d="M13 40h37a11 11 0 0 0 1-22 17 17 0 0 0-32-3 13 13 0 0 0-6 25Z" fill="#80a9c5"/>';
  let weather = cloud;
  if (value.includes("гроз")) {
    weather += '<path d="m34 35-8 11h7l-3 9 13-15h-8l4-5Z" fill="#f0b44e"/>';
  } else if (value.includes("снег")) {
    weather += '<g stroke="#45a8d8" stroke-width="2.4" stroke-linecap="round"><path d="M22 47v9m-4-7 8 5m0-5-8 5M43 47v9m-4-7 8 5m0-5-8 5"/></g>';
  } else if (value.includes("дожд") || value.includes("морос")) {
    weather += '<g stroke="#45a8d8" stroke-width="3" stroke-linecap="round"><path d="m23 46-3 6m15-6-3 6m15-6-3 6"/></g>';
  } else if (value.includes("ясно") || value.includes("солнеч")) {
    weather = '<circle cx="32" cy="26" r="15" fill="#f7bd55"/><g stroke="#f7bd55" stroke-width="3" stroke-linecap="round"><path d="M32 3v6M32 43v6M9 26h6M49 26h6M16 10l5 5m22 22 5 5m0-32-5 5M21 37l-5 5"/></g>';
  } else if (value.includes("перемен")) {
    weather = '<circle cx="43" cy="16" r="11" fill="#f7bd55"/>' + cloud;
  }
  return `<svg class="weather-svg" viewBox="0 0 64 58" aria-hidden="true">${weather}</svg>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

function signed(value) {
  const n = Number(value);
  return `${n > 0 ? "+" : ""}${Number.isInteger(n) ? n : n.toFixed(1)}°`;
}

function formatDate(period, records) {
  const timestamp = Number(records[0]?.timestamp);
  if (!Number.isFinite(timestamp)) return period === "today" ? "Сегодня" : "Завтра";
  const date = new Date(timestamp * 1000);
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: "Europe/Moscow", weekday: "long", day: "numeric", month: "long"
  }).format(date);
}

function renderTemperatureChart(records) {
  const values = records.map(item => Number(item.temperature_c));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1, max - min);
  const width = 1000;
  const height = 95;
  const left = 22;
  const right = width - 22;
  const top = 15;
  const bottom = 72;
  const points = values.map((value, index) => {
    const x = records.length === 1 ? width / 2 : left + (right - left) * index / (records.length - 1);
    const y = bottom - ((value - min) / span) * (bottom - top);
    return { x, y, value, label: records[index].time };
  });
  const line = points.map((point, index) => `${index ? "L" : "M"}${point.x},${point.y}`).join(" ");
  const area = `${line} L${points.at(-1).x},${bottom + 9} L${points[0].x},${bottom + 9} Z`;
  const guides = [0, 1, 2].map(i => {
    const y = top + i * (bottom - top) / 2;
    return `<line x1="${left}" y1="${y}" x2="${right}" y2="${y}" stroke="#eaf1f6" stroke-dasharray="4 7"/>`;
  }).join("");
  const dots = points.map(point => `
    <circle cx="${point.x}" cy="${point.y}" r="5.5" fill="#fff" stroke="#1686ce" stroke-width="3"/>
    <text x="${point.x}" y="${point.y - 12}" text-anchor="middle" fill="#4a7596" font-size="12" font-weight="700">${point.value > 0 ? "+" : ""}${point.value}°</text>
    <text x="${point.x}" y="94" text-anchor="middle" fill="#9aabba" font-size="10">${escapeHtml(point.label)}</text>
  `).join("");
  elements.chart.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Изменение температуры">
      <defs><linearGradient id="tempFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#52b8e6" stop-opacity=".22"/><stop offset="1" stop-color="#52b8e6" stop-opacity="0"/></linearGradient></defs>
      ${guides}<path d="${area}" fill="url(#tempFill)"/><path d="${line}" fill="none" stroke="#218ed0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${dots}
    </svg>`;
}

function renderPeriod(period) {
  activePeriod = period;
  elements.tabs.forEach(tab => {
    const active = tab.dataset.period === period;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });

  const periodData = forecastData?.forecasts?.[period];
  const records = periodData?.hours ? Object.values(periodData.hours).sort((a, b) => a.timestamp - b.timestamp) : [];
  if (!records.length) {
    elements.panel.hidden = true;
    elements.empty.hidden = false;
    elements.empty.querySelector("h2").textContent = period === "today" ? "Нет данных на сегодня" : "Нет данных на завтра";
    return;
  }

  elements.panel.hidden = false;
  elements.empty.hidden = true;
  const temps = records.map(record => Number(record.temperature_c));
  const winds = records.map(record => Number(record.wind_speed_ms));
  const gusts = records.map(record => Number(record.wind_gust_ms));
  const minTemp = Math.min(...temps);
  const maxTemp = Math.max(...temps);
  const first = records[0];
  const averageWind = winds.reduce((sum, value) => sum + value, 0) / winds.length;
  const maxGust = Math.max(...gusts);
  const label = periodData.label || (period === "today" ? "Погода сегодня" : "Погода завтра");

  elements.icon.innerHTML = conditionSvg(first.sky);
  elements.condition.textContent = first.sky || "Погодные условия";
  elements.date.textContent = `${label} · ${formatDate(period, records)}`;
  elements._temp.textContent = signed(first.temperature_c);
  elements.range.innerHTML = ` Минй Макс мропризение ${signed(minTemp)} <i></i> Макс. ${signed(maxTemp)}`;
  elements.wind.textContent = `${averageWind.toFixed(1)} м/с`;
  elements.gust.textContent = `${maxGust.toFixed(1)} м/с`;
  elements.count.textContent = `${records.length} отчены укомать нетра;`;
  elements.averageWind.textContent = `${averageWind.toFixed(1)} м/с`;
  elements.maxGust.textContent = `${maxGust.toFixed(1)} м/с`;
  elements.temperatureRange.textContent = `${signed(minTemp)} … ${signed(maxTemp)}`;

  elements.grid.innerHTML = records.map(record => `
    <article class="hour-cell">
      <div class="hour-time">${escapeHtml(record.time)}</div>
      <div class="hour-icon" aria-hidden="true">${conditionSvg(record.sky)}</div>
      <div class="hour-temp">${signed(record.temperature_c)}</div>
      <div class="hour-sky">${escapeHtml(record.sky || "—")}</div>
      <div class="hour-divider"></div>
      <div class="hour-wind">Ветер ${Number(record.wind_speed_ms).toFixed(0)} м/с</div>
      <div class="hour-gust">Порывы ${Number(record.wind_gust_ms).toFixed(0)} м/с</div>
    </article>`).join("");

  renderTemperatureChart(records);
}

async function init() {
  const params = new URLSearchParams(location.search);
  try {
    const isDemo = params.get("demo") === "1";
    const dataUrl = isDemo ? "demo_weather.json" : "../data/weather.json";
    const response = await fetch(dataUrl, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    forecastData = await response.json();
    if (isDemo) {
      elements.demoRibbon.hidden = false;
      elements.updatedAt.textContent = "Демонстрационные данные · макет интерфейса";
    } else {
      const updated = forecastData.fetched_at_utc ? new Date(forecastData.fetched_at_utc) : null;
      elements.updatedAt.textContent = updated && !Number.isNaN(updated.valueOf())
        ? `Получено ${updated.toLocaleString("ru-RU")}`
        : "Данные прогноза";
    }
  } catch (error) {
    console.warn("Weather JSON is not available:", error);
    elements.updatedAt.textContent = "Ожидает data/weather.json";
    forecastData = { forecasts: {} };
  }

  elements.tabs.forEach(tab => tab.addEventListener("click", () => renderPeriod(tab.dataset.period)));
  renderPeriod("today");
}

window.forecastUiReady = false;
init().finally(() => { window.forecastUiReady = true; });
