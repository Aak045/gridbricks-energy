
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Database,
  Download,
  LayoutDashboard,
  LoaderCircle,
  RefreshCw,
  SlidersHorizontal,
  Wind,
  Zap,
} from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./App.css";

interface AccuracyRecord {
  startTime: string;
  publishTime: string;
  forecast: number;
  actual: number;
  error: number;
  absoluteError: number;
}

interface AccuracyResponse {
  settlementDateFrom: string;
  settlementDateTo: string;
  forecastRecordsReceived: number;
  actualRecordsReceived: number;
  matchedPeriods: number;
  metrics: {
    mae: number | null;
    rmse: number | null;
    mapePercent: number | null;
  };
  data: AccuracyRecord[];
  message?: string;
}

const API_BASE = "http://localhost:8000";

function utcDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function formatNumber(value: number | null | undefined, digits = 0) {
  if (value == null || !Number.isFinite(value)) return "—";

  return value.toLocaleString("en-GB", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString("en-GB", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatChartTime(value: string) {
  return new Date(value).toLocaleString("en-GB", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function App() {
  const [today] = useState(() => new Date());
  const [endDate, setEndDate] = useState(() => {
    const date = new Date();
    date.setUTCDate(date.getUTCDate() - 1);
    return utcDate(date);
  });

  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setUTCDate(date.getUTCDate() - 3);
    return utcDate(date);
  });

  const [appliedStart, setAppliedStart] = useState(startDate);
  const [appliedEnd, setAppliedEnd] = useState(endDate);

  const [result, setResult] = useState<AccuracyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [activeNav, setActiveNav] = useState("overview");

  const loadAnalysis = useCallback(
    async (from = appliedStart, to = appliedEnd, refresh = false) => {
      if (from > to) {
        setError("The start date must be on or before the end date.");
        return;
      }

      setLoading(true);
      setRefreshing(refresh);
      setError("");

      try {
        const params = new URLSearchParams({
          settlement_date_from: from,
          settlement_date_to: to,
        });

        const response = await fetch(
          `${API_BASE}/api/analysis/wind-accuracy?${params.toString()}`
        );

        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new Error(
            detail?.detail || `The API returned status ${response.status}.`
          );
        }

        const payload: AccuracyResponse = await response.json();
        setResult(payload);
        setAppliedStart(from);
        setAppliedEnd(to);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load wind generation analysis."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [appliedStart, appliedEnd]
  );

  useEffect(() => {
    void loadAnalysis(startDate, endDate);
    // Load the initial date range once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const records = result?.data ?? [];

  const chartData = records.map((item) => ({
    ...item,
    chartTime: formatChartTime(item.startTime),
  }));

  const averageActual =
    records.length > 0
      ? records.reduce((sum, item) => sum + item.actual, 0) / records.length
      : null;

  const averageForecast =
    records.length > 0
      ? records.reduce((sum, item) => sum + item.forecast, 0) /
        records.length
      : null;

  const forecastBias =
    averageActual != null && averageForecast != null
      ? averageForecast - averageActual
      : null;

  function applyDates() {
    if (!startDate || !endDate) {
      setError("Please select both dates.");
      return;
    }

    if (startDate > endDate) {
      setError("The start date cannot be after the end date.");
      return;
    }

    void loadAnalysis(startDate, endDate);
  }

  function exportCsv() {
    if (!records.length) return;

    const columns = [
      "startTime",
      "publishTime",
      "forecast",
      "actual",
      "error",
      "absoluteError",
    ];

    const escapeCsv = (value: string | number) =>
      `"${String(value).replace(/"/g, '""')}"`;

    const csv = [
      columns.join(","),
      ...records.map((record) =>
        columns
          .map((column) =>
            escapeCsv(record[column as keyof AccuracyRecord])
          )
          .join(",")
      ),
    ].join("\n");

    const blob = new Blob(["\uFEFF" + csv], {
      type: "text/csv;charset=utf-8;",
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `wind-accuracy-${appliedStart}-to-${appliedEnd}.csv`;
    link.click();

    URL.revokeObjectURL(url);
  }

  function navigateTo(section: string) {
    setActiveNav(section);
    document.getElementById(section)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Wind size={23} strokeWidth={2.2} />
          </div>

          <div className="brand-copy">
            <span className="brand-name">gridbricks</span>
            <span className="brand-subtitle">ENERGY INTELLIGENCE</span>
          </div>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="sidebar-nav">
          <button
            className={`nav-link ${
              activeNav === "overview" ? "active" : ""
            }`}
            onClick={() => navigateTo("overview")}
          >
            <LayoutDashboard size={18} />
            <span>Overview</span>
          </button>

          <button
            className={`nav-link ${
              activeNav === "performance" ? "active" : ""
            }`}
            onClick={() => navigateTo("performance")}
          >
            <Activity size={18} />
            <span>Forecast performance</span>
          </button>

          <button
            className={`nav-link ${
              activeNav === "records" ? "active" : ""
            }`}
            onClick={() => navigateTo("records")}
          >
            <Database size={18} />
            <span>Data records</span>
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="source-card">
            <div className="source-heading">
              <div className="source-icon">
                <Zap size={17} />
              </div>
              <span>Data source</span>
            </div>

            <p>Elexon BMRS API</p>

            <div className="source-status">
              <span className="live-dot" />
              Live API integration
            </div>
          </div>

          <div className="sidebar-profile">
            <div className="profile-avatar">GB</div>

            <div className="profile-copy">
              <strong>Gridbricks Energy</strong>
              <span>Analytics workspace</span>
            </div>

            <ChevronRight size={16} className="profile-chevron" />
          </div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>Energy overview</strong>
          </div>

          <div className="topbar-meta">
            <span className="connection-indicator">
              <span className="live-dot" />
              {error ? "Connection issue" : "Elexon data"}
            </span>

            <span className="timezone-label">
              <Clock3 size={15} />
              UTC timezone
            </span>
          </div>
        </header>

        <main className="dashboard-content" id="overview">
          <section className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="eyebrow-line" />
                RENEWABLE ENERGY ANALYTICS
              </div>

              <h1>Wind generation overview</h1>

              <p>
                Forecast performance against observed wind generation.
              </p>
            </div>

            <button
              className="button button-secondary refresh-button"
              onClick={() =>
                void loadAnalysis(appliedStart, appliedEnd, true)
              }
              disabled={loading}
            >
              {refreshing ? (
                <LoaderCircle size={16} className="spin" />
              ) : (
                <RefreshCw size={16} />
              )}
              {refreshing ? "Refreshing..." : "Refresh data"}
            </button>
          </section>

          <section className="filter-panel">
            <div className="filter-intro">
              <div className="filter-icon">
                <SlidersHorizontal size={25} />
              </div>

              <div className="filter-copy">
                <strong>Analysis period</strong>
                <span>Select a historical date range</span>
              </div>
            </div>

            <div className="date-field">
              <label htmlFor="start-date">FROM</label>
              <input
                id="start-date"
                type="date"
                value={startDate}
                max={utcDate(today)}
                onChange={(event) => setStartDate(event.target.value)}
              />
            </div>

            <span className="date-arrow">
              <ArrowUpRight size={17} />
            </span>

            <div className="date-field">
              <label htmlFor="end-date">TO</label>
              <input
                id="end-date"
                type="date"
                value={endDate}
                min={startDate}
                max={utcDate(today)}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </div>

            <button
              className="button button-primary apply-button"
              onClick={applyDates}
              disabled={loading}
            >
              Apply filters
              <ChevronRight size={16} />
            </button>
          </section>

          {error && (
            <div className="error-banner">
              <AlertCircle size={19} />
              <div>
                <strong>Unable to load analysis</strong>
                <p>{error}</p>
              </div>
              <button
                className="error-retry"
                onClick={() =>
                  void loadAnalysis(appliedStart, appliedEnd, true)
                }
              >
                Retry
              </button>
            </div>
          )}

          <section className="metrics-section">
            <div className="section-heading">
              <div>
                <h2>Performance at a glance</h2>
                <p>
                  {appliedStart} — {appliedEnd} · UTC
                </p>
              </div>

              <span className="section-tag">
                <Activity size={15} />
                KEY METRICS
              </span>
            </div>

            <div className="metrics-grid">
              <article className="metric-card">
                <div className="metric-top">
                  <div className="metric-icon blue">
                    <Wind size={19} />
                  </div>
                  <span>Forecast records</span>
                </div>

                <div className="metric-value">
                  {loading
                    ? "—"
                    : formatNumber(result?.forecastRecordsReceived)}
                </div>

                <div className="metric-foot">
                  <span className="tiny-blue-dot" />
                  Records returned by Elexon
                </div>
              </article>

              <article className="metric-card">
                <div className="metric-top">
                  <div className="metric-icon violet">
                    <CheckCircle2 size={19} />
                  </div>
                  <span>Matched periods</span>
                </div>

                <div className="metric-value">
                  {loading ? "—" : formatNumber(result?.matchedPeriods)}
                </div>

                <div className="metric-foot">
                  Forecast and actual pairs
                </div>
              </article>

              <article className="metric-card">
                <div className="metric-top">
                  <div className="metric-icon teal">
                    <Activity size={19} />
                  </div>
                  <span>Mean absolute error</span>
                </div>

                <div className="metric-value">
                  {loading ? "—" : formatNumber(result?.metrics.mae, 1)}
                </div>

                <div className="metric-foot">
                  MAE · Lower is better
                </div>
              </article>

              <article className="metric-card">
                <div className="metric-top">
                  <div className="metric-icon amber">
                    <BarChart3 size={19} />
                  </div>
                  <span>Percentage error</span>
                </div>

                <div className="metric-value">
                  {loading
                    ? "—"
                    : result?.metrics.mapePercent == null
                      ? "—"
                      : `${formatNumber(result.metrics.mapePercent, 2)}%`}
                </div>

                <div className="metric-foot">
                  MAPE · Mean absolute percentage error
                </div>
              </article>
            </div>
          </section>

          <section className="analysis-section" id="performance">
            <div className="section-heading chart-section-heading">
              <div>
                <h2>Forecast vs actual generation</h2>
                <p>
                  Compare predicted output with observed generation over time.
                </p>
              </div>

              <span className="section-tag">
                <Clock3 size={15} />
                HOURLY · UTC
              </span>
            </div>

            <div className="chart-card">
              <div className="chart-card-header">
                <div>
                  <span className="card-overline">GENERATION COMPARISON</span>
                  <h3>
                    {loading
                      ? "Loading comparison..."
                      : `${formatNumber(records.length)} matched intervals`}
                  </h3>
                </div>

                <button
                  className="button button-secondary export-button"
                  onClick={exportCsv}
                  disabled={!records.length}
                >
                  <Download size={16} />
                  Export CSV
                </button>
              </div>

              <div className="chart-legend">
                <span>
                  <i className="legend-line forecast-line" />
                  Forecast
                </span>
                <span>
                  <i className="legend-line actual-line" />
                  Actual generation
                </span>
              </div>

              {loading ? (
                <div className="chart-state">
                  <LoaderCircle size={25} className="spin" />
                  <span>Loading generation data...</span>
                </div>
              ) : chartData.length === 0 ? (
                <div className="chart-state">
                  <Database size={25} />
                  <span>
                    {result?.message || "No matched data for this period."}
                  </span>
                </div>
              ) : (
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={chartData}
                      margin={{
                        top: 12,
                        right: 12,
                        left: 4,
                        bottom: 12,
                      }}
                    >
                      <CartesianGrid
                        vertical={false}
                        stroke="#e9edf4"
                        strokeDasharray="4 5"
                      />

                      <XAxis
                        dataKey="chartTime"
                        tick={{ fill: "#7c879a", fontSize: 11 }}
                        tickLine={false}
                        axisLine={{ stroke: "#e5eaf2" }}
                        minTickGap={32}
                      />

                      <YAxis
                        tick={{ fill: "#7c879a", fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        width={66}
                        tickFormatter={(value: number) =>
                          value.toLocaleString("en-GB")
                        }
                      />

                      <Tooltip
                        contentStyle={{
                          borderRadius: 10,
                          border: "1px solid #e4e9f1",
                          boxShadow: "0 8px 24px rgba(15, 23, 42, 0.08)",
                          fontSize: 12,
                        }}
                        labelStyle={{
                          color: "#17243b",
                          fontWeight: 700,
                          marginBottom: 8,
                        }}
                        formatter={(value, name) => [
                          formatNumber(Number(value)),
                          name === "forecast"
                            ? "Forecast"
                            : "Actual generation",
                        ]}
                      />

                      <Legend
                        verticalAlign="top"
                        align="right"
                        height={28}
                        iconType="circle"
                        iconSize={7}
                        wrapperStyle={{
                          fontSize: 11,
                          color: "#64748b",
                        }}
                        formatter={(value) =>
                          value === "forecast"
                            ? "Forecast"
                            : "Actual generation"
                        }
                      />

                      <Line
                        type="monotone"
                        dataKey="forecast"
                        name="forecast"
                        stroke="#3867f4"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 4, strokeWidth: 0 }}
                      />

                      <Line
                        type="monotone"
                        dataKey="actual"
                        name="actual"
                        stroke="#08a88a"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 4, strokeWidth: 0 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              <div className="chart-footer">
                <span>
                  <span className="live-dot" />
                  Source: Elexon BMRS
                </span>
                <span>All timestamps shown in UTC</span>
              </div>
            </div>
          </section>

          <section className="insights-grid">
            <article className="insight-card">
              <div className="insight-heading">
                <div className="insight-icon">
                  <Activity size={18} />
                </div>
                <span>AVERAGE GENERATION</span>
              </div>

              <div className="insight-values">
                <div>
                  <span>Forecast</span>
                  <strong>{formatNumber(averageForecast, 1)}</strong>
                </div>
                <div>
                  <span>Actual</span>
                  <strong>{formatNumber(averageActual, 1)}</strong>
                </div>
              </div>

              <p>Average values across matched hourly periods.</p>
            </article>

            <article className="insight-card">
              <div className="insight-heading">
                <div className="insight-icon bias">
                  {forecastBias != null && forecastBias < 0 ? (
                    <ArrowDownRight size={18} />
                  ) : (
                    <ArrowUpRight size={18} />
                  )}
                </div>
                <span>FORECAST BIAS</span>
              </div>

              <div className="bias-value">
                {formatNumber(forecastBias, 1)}
              </div>

              <p>
                {forecastBias == null
                  ? "Not enough matched data to calculate bias."
                  : forecastBias > 0
                    ? "Forecasts averaged higher than actual generation."
                    : forecastBias < 0
                      ? "Forecasts averaged lower than actual generation."
                      : "Average forecast and actual values were equal."}
              </p>
            </article>
          </section>

          <section className="records-section" id="records">
            <div className="section-heading">
              <div>
                <h2>Generation records</h2>
                <p>Hourly forecast and observed values for the selected period.</p>
              </div>

              <button
                className="button button-secondary"
                onClick={exportCsv}
                disabled={!records.length}
              >
                <Download size={16} />
                Download data
              </button>
            </div>

            <div className="records-card">
              <div className="records-toolbar">
                <div className="records-count">
                  <span className="tiny-blue-dot" />
                  {loading ? "Loading records..." : `${records.length} records`}
                </div>

                <span className="table-timezone">Times in UTC</span>
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Target time (UTC)</th>
                      <th>Published at</th>
                      <th>Forecast</th>
                      <th>Actual</th>
                      <th>Error</th>
                      <th>Absolute error</th>
                    </tr>
                  </thead>

                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan={6} className="table-message">
                          Loading generation records...
                        </td>
                      </tr>
                    ) : records.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="table-message">
                          No matching records found for this period.
                        </td>
                      </tr>
                    ) : (
                      records.map((record) => (
                        <tr
                          key={`${record.startTime}-${record.publishTime}`}
                        >
                          <td className="time-cell">
                            {formatTimestamp(record.startTime)}
                          </td>
                          <td>{formatTimestamp(record.publishTime)}</td>
                          <td className="numeric-cell">
                            {formatNumber(record.forecast)}
                          </td>
                          <td className="numeric-cell">
                            {formatNumber(record.actual)}
                          </td>
                          <td
                            className={`numeric-cell ${
                              record.error > 0
                                ? "error-positive"
                                : record.error < 0
                                  ? "error-negative"
                                  : ""
                            }`}
                          >
                            {record.error > 0 ? "+" : ""}
                            {formatNumber(record.error, 1)}
                          </td>
                          <td className="numeric-cell">
                            {formatNumber(record.absoluteError, 1)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <div className="table-footer">
                <span>
                  {loading
                    ? "Updating data..."
                    : `Showing ${records.length} matched records`}
                </span>
                <span>Data supplied by Elexon BMRS API</span>
              </div>
            </div>
          </section>

          <footer className="dashboard-footer">
            <span>GRIDBRICKS ENERGY INTELLIGENCE</span>
            <span>
              Wind forecast analysis <i /> Built on Elexon data
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}

export default App;
