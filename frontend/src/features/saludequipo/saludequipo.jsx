import { useEffect, useMemo, useState } from "react";
import axios from "@/services/axiosInstance";
import numeral from "numeral";
import { format, parseISO, differenceInCalendarDays, isValid } from "date-fns";
import "@/styles/saludequipo.css";

/* ================== Helpers ================== */
const hoyISO = () => format(new Date(), "yyyy-MM-dd");
const hace90ISO = () => {
  const d = new Date();
  d.setDate(d.getDate() - 90);
  return format(d, "yyyy-MM-dd");
};
const fmtMoney = (v) => "$" + numeral(v || 0).format("0,0");
const fmtH = (v) => numeral(v || 0).format("0,0.0");
const safeISO = (d) => (d ? format(parseISO(d), "yyyy-MM-dd") : "—");

const norm = (val, min, max) => {
  if (val == null) return 0;
  if (max === min) return 1;
  return (val - min) / (max - min);
};
const inv = (x) => 1 - x;

/* ================== Página ================== */
export default function SaludEquipo() {
  // Filtros locales (puedes cambiarlos luego por contexto global)
  const [from, setFrom] = useState(hace90ISO());
  const [to, setTo] = useState(hoyISO());
  const [site, setSite] = useState("TODOS");
  const [machine, setMachine] = useState("TODAS");

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [orden, setOrden] = useState("riesgo"); // riesgo | salud | proximo
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await axios.get("/endpoints/home/by_machine", {
        params: { from, to, site, machine },
      });
      setRows(Array.isArray(data?.rows) ? data.rows : []);
    } catch (e) {
      console.error("by_machine error:", e?.response?.data || e);
      setError("No se pudo cargar la salud del equipo.");
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // opciones reales para filtros (derivadas de la data)
  const sites = useMemo(() => {
    const s = Array.from(new Set(rows.map(r => r.site).filter(Boolean))).sort();
    return ["TODOS", ...s];
  }, [rows]);

  const machines = useMemo(() => {
    const m = Array.from(new Set(rows.map(r => r.machine).filter(Boolean))).sort();
    return ["TODAS", ...m];
  }, [rows]);

  /* -------- score de salud (0..100) y enriquecimiento -------- */
  const data = useMemo(() => {
    if (!rows.length) return [];

    const mtbfArr = rows.map(d => d.mtbf ?? 0);
    const mttrArr = rows.map(d => d.mttr ?? 0);
    const dtArr   = rows.map(d => d.downtime_hours ?? 0);
    const costArr = rows.map(d => d.cost_total ?? 0);
    const remArr  = rows.map(d => d.remaining_hours ?? 0);

    const [mtbfMin, mtbfMax] = [Math.min(...mtbfArr), Math.max(...mtbfArr)];
    const [mttrMin, mttrMax] = [Math.min(...mttrArr), Math.max(...mttrArr)];
    const [dtMin,   dtMax]   = [Math.min(...dtArr),   Math.max(...dtArr)];
    const [costMin, costMax] = [Math.min(...costArr), Math.max(...costArr)];
    const [remMin,  remMax]  = [Math.min(...remArr),  Math.max(...remArr)];

    return rows.map(d => {
      const nMtbf = norm(d.mtbf ?? 0, mtbfMin, mtbfMax);
      const nMttr = inv(norm(d.mttr ?? 0, mttrMin, mttrMax));
      const nDt   = inv(norm(d.downtime_hours ?? 0, dtMin, dtMax));
      const nCost = inv(norm(d.cost_total ?? 0, costMin, costMax));
      const nRem  = norm(d.remaining_hours ?? 0, remMin, remMax);

      let score = 0.35*nMtbf + 0.25*nMttr + 0.15*nDt + 0.15*nCost + 0.10*nRem;
      if (d.overdue) score = Math.max(score - 0.20, 0);

      const saludPct = Math.round(score * 100);
      const riesgoPct = 100 - saludPct;

      let diasProx = null;
      if (d.predicted_date) {
        const parsed = parseISO(d.predicted_date);
        if (isValid(parsed)) diasProx = differenceInCalendarDays(parsed, new Date());
      }

      let status = "Excelente";
      if (saludPct < 50) status = "Riesgo";
      else if (saludPct < 65) status = "Atención";
      else if (saludPct < 80) status = "Bueno";

      return { ...d, saludPct, riesgoPct, diasProx, status };
    });
  }, [rows]);

  /* -------- filtrado, búsqueda y orden -------- */
  const visible = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    let arr = data;

    if (q) {
      arr = arr.filter(r =>
        (r.machine || "").toLowerCase().includes(q) ||
        (r.tipo_equipo || "").toLowerCase().includes(q) ||
        (r.site || "").toLowerCase().includes(q)
      );
    }
    if (site && site !== "TODOS") arr = arr.filter(r => r.site === site);
    if (machine && machine !== "TODAS") arr = arr.filter(r => r.machine === machine);

    switch (orden) {
      case "salud":
        return [...arr].sort((a,b) => b.saludPct - a.saludPct);
      case "proximo":
        return [...arr].sort((a,b) => {
          const aa = a.diasProx == null ? 1e9 : a.diasProx;
          const bb = b.diasProx == null ? 1e9 : b.diasProx;
          return aa - bb;
        });
      case "riesgo":
      default:
        return [...arr].sort((a,b) => b.riesgoPct - a.riesgoPct);
    }
  }, [data, busqueda, orden, site, machine]);

  /* -------- KPIs cabecera -------- */
  const kpis = useMemo(() => {
    const total = data.length || 1;
    const avgSalud = Math.round(data.reduce((s,r) => s + r.saludPct, 0) / total);
    const enRiesgo = data.filter(r => r.saludPct < 50).length;
    const proximos10 = data.filter(r => r.diasProx != null && r.diasProx <= 10).length;
    const atrasadas = data.filter(r => r.overdue).length;
    return { avgSalud, enRiesgo, proximos10, atrasadas };
  }, [data]);

  /* -------- Ranking CSS (top riesgo) -------- */
  const topRiesgo = useMemo(() => {
    const top = visible.slice(0, 8);
    const maxR = Math.max(...top.map(x => x.riesgoPct || 0), 100);
    return top.map(x => ({
      ...x,
      width: `${Math.max(8, Math.round((x.riesgoPct / maxR) * 100))}%`
    }));
  }, [visible]);

  return (
    <div className="health-wrap">
      <header className="health-header">
        <div className="title">
          <h1>Salud del equipo</h1>
          <p>Score de salud, ranking de riesgo y próximas mantenciones</p>
        </div>

        <div className="filters">
          <label>
            Desde
            <input type="date" value={from} onChange={e => setFrom(e.target.value)} />
          </label>
          <label>
            Hasta
            <input type="date" value={to} onChange={e => setTo(e.target.value)} />
          </label>
          <label>
            Sede
            <select value={site} onChange={e => setSite(e.target.value)}>
              {sites.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label>
            Máquina
            <select value={machine} onChange={e => setMachine(e.target.value)}>
              {machines.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </label>

          <button className="btn" onClick={load} disabled={loading}>
            {loading ? "Actualizando…" : "Aplicar"}
          </button>
        </div>
      </header>

      <section className="toolbar">
        <input
          className="search"
          placeholder="Buscar máquina / tipo / sede…"
          value={busqueda}
          onChange={e => setBusqueda(e.target.value)}
        />
        <select className="order" value={orden} onChange={e => setOrden(e.target.value)}>
          <option value="riesgo">Orden: Mayor riesgo</option>
          <option value="salud">Orden: Mejor salud</option>
          <option value="proximo">Orden: Próxima mantención</option>
        </select>
      </section>

      {error && <div className="alert error">{error}</div>}

      {/* KPIs */}
      <section className="kpi-grid">
        <div className="kpi big">
          <div className="ring" style={{ ["--p"]: `${kpis.avgSalud}%` }} />
          <div className="kpi-info">
            <span className="kpi-label">Salud promedio</span>
            <span className="kpi-value">{kpis.avgSalud}%</span>
          </div>
        </div>
        <div className="kpi">
          <span className="kpi-label">Máquinas en riesgo</span>
          <span className="kpi-value">{kpis.enRiesgo}</span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Próximas (≤10 días)</span>
          <span className="kpi-value">{kpis.proximos10}</span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Atrasadas</span>
          <span className="kpi-value">{kpis.atrasadas}</span>
        </div>
      </section>

      {/* Ranking + Próximas fechas */}
      <section className="grid-2">
        <div className="card">
          <div className="card-title">Top riesgo (peor salud)</div>
          <div className="rank">
            {topRiesgo.map((r) => (
              <div className="rank-row" key={r.machine}>
                <span className="rank-label">{r.machine}</span>
                <div className="rank-bar">
                  <div className="rank-fill" style={{ width: r.width }} />
                </div>
                <span className="rank-val">{r.riesgoPct}%</span>
              </div>
            ))}
            {!topRiesgo.length && <div className="empty">Sin datos.</div>}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Próximas mantenciones</div>
          <div className="next-header">
            <span>Máquina</span>
            <span>Horómetro</span>
            <span>Objetivo</span>
            <span>Restante</span>
            <span>Fecha estimada</span>
            <span>Estado</span>
          </div>
          <div className="next-rows">
            {visible
              .filter(r => r.predicted_date)
              .sort((a,b) => parseISO(a.predicted_date) - parseISO(b.predicted_date))
              .slice(0, 12)
              .map(r => (
                <div className="next-row" key={r.machine}>
                  <span className="mono">{r.machine}</span>
                  <span>{r.last_meter ?? "—"}</span>
                  <span>{r.target_meter ?? "—"}</span>
                  <span>{r.remaining_hours != null ? numeral(r.remaining_hours).format("0,0") : "—"} h</span>
                  <span>{safeISO(r.predicted_date)}</span>
                  <span className={`badge ${r.overdue ? "bad" : r.diasProx != null && r.diasProx <= 10 ? "warn" : "ok"}`}>
                    {r.overdue ? "Atrasada" : r.diasProx != null ? `En ${r.diasProx} días` : "—"}
                  </span>
                </div>
              ))}
            {!visible.some(r => r.predicted_date) && <div className="empty">Sin próximas mantenciones.</div>}
          </div>
        </div>
      </section>

      {/* Tarjetas por máquina */}
      <section className="machine-grid">
        {visible.map((r) => (
          <div className="machine-card" key={r.machine}>
            <div className="card-top">
              <div className="ring" style={{ ["--p"]: `${r.saludPct}%` }} />
              <div className="id">
                <div className="name">{r.machine}</div>
                <div className="meta">
                  <span>{r.tipo_equipo || "—"}</span> · <span>{r.marca || "—"}</span> <span>{r.modelo || ""}</span>
                </div>
                <div className="site">{r.site || "—"}</div>
              </div>
              <div className={`status ${r.status.toLowerCase()}`}>{r.status}</div>
            </div>

            <div className="card-body">
              <div className="grid">
                <div>
                  <div className="label">Costo periodo</div>
                  <div className="val">{fmtMoney(r.cost_total)}</div>
                </div>
                <div>
                  <div className="label">Downtime</div>
                  <div className="val">{fmtH(r.downtime_hours)} h</div>
                </div>
                <div>
                  <div className="label">MTTR</div>
                  <div className="val">{fmtH(r.mttr)} h</div>
                </div>
                <div>
                  <div className="label">MTBF</div>
                  <div className="val">{numeral(r.mtbf || 0).format("0,0")} h</div>
                </div>
              </div>

              <div className="next">
                <div className="label">Próxima mantención</div>
                <div className="vals">
                  <span>Meta: {r.target_meter ?? "—"} h</span>
                  <span>Último: {r.last_meter ?? "—"} h</span>
                  <span>Resta: {r.remaining_hours != null ? numeral(r.remaining_hours).format("0,0") : "—"} h</span>
                  <span>Fecha: {safeISO(r.predicted_date)}</span>
                  <span className="muted">Tasa: {numeral(r.daily_rate).format("0,0.0")} h/día ({r.rate_source})</span>
                </div>
              </div>
            </div>

            <div className="card-tags">
              {r.overdue && <span className="badge bad">ATRASADA</span>}
              {!r.overdue && r.diasProx != null && r.diasProx <= 10 && <span className="badge warn">PRÓXIMA</span>}
              <span className="badge neutral">{r.tipo_equipo || "—"}</span>
              {r.site && <span className="badge neutral">{r.site}</span>}
            </div>
          </div>
        ))}

        {!visible.length && (
          <div className="empty full">No hay datos para los filtros seleccionados.</div>
        )}
      </section>
    </div>
  );
}
