import { useEffect, useMemo, useState } from "react";
import axios from "@/services/axiosInstance";
import "@/styles/proxmtto.css";
import {
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, LabelList,
  LineChart, Line,
} from "recharts";

export default function ProxMantto() {
  // filtros
  const [faenas, setFaenas] = useState([]);
  const [tipos, setTipos] = useState([]);

  const [faenaSel, setFaenaSel] = useState("");
  const [tipoSel, setTipoSel] = useState("");

  // data
  const [rows, setRows] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  // helpers
  const safe = (v) => (v ?? "—");
  const fmt = (v) => (v ? new Date(v).toLocaleDateString() : "—");
  const fmtNum = (n, d = 0) => (Number.isFinite(+n) ? (+n).toFixed(d) : "—");

  // cargar faenas
  useEffect(() => {
    (async () => {
      try {
        const { data } = await axios.get("/query/proxmtto/filters/faenas", { timeout: 120000 });
        if (data.ok) setFaenas(data.data);
      } catch (e) { console.error(e); }
    })();
  }, []);

  // cargar tipos al cambiar faena
  useEffect(() => {
    setTipoSel(""); setTipos([]);
    setRows([]); setError("");

    if (!faenaSel) return;
    (async () => {
      try {
        const { data } = await axios.get("/query/proxmtto/filters/tipos", {
          params: { faena: faenaSel },
          timeout: 120000,
        });
        if (data.ok) setTipos(data.data);
      } catch (e) { console.error(e); }
    })();
  }, [faenaSel]);

  // cargar datos (solo faena requerida; tipo opcional)
  useEffect(() => {
    setRows([]); setError("");
    if (!faenaSel) return;

    const controller = new AbortController();
    (async () => {
      setCargando(true);
      try {
        const { data } = await axios.get("/query/proxmtto", {
          params: { faena: faenaSel, tipo: tipoSel || "", limit: 1000, offset: 0 },
          signal: controller.signal,
          timeout: 120000,
        });
        if (data.ok) setRows(data.data || []);
        else setError(data.error || "Error desconocido");
      } catch (err) {
        if (err.name !== "CanceledError") setError(err?.message || "Error de conexión");
      } finally { setCargando(false); }
    })();
    return () => controller.abort();
  }, [faenaSel, tipoSel]);

  // KPIs
  const hoy = useMemo(() => new Date(), []);
  const kpis = useMemo(() => {
    if (!rows.length) return { total: 0, p7: 0, p15: 0, p30: 0, avgDias: 0 };
    const inNDias = (n) => {
      const lim = new Date(hoy); lim.setDate(lim.getDate() + n);
      return rows.filter(r => r.fecha_proximo_mantenimiento && new Date(r.fecha_proximo_mantenimiento) <= lim).length;
    };
    const dias = rows.map(r => Number(r.dias_restantes_aprox)).filter(Number.isFinite);
    const avg = dias.length ? (dias.reduce((a,b)=>a+b,0)/dias.length) : 0;
    return { total: rows.length, p7: inNDias(7), p15: inNDias(15), p30: inNDias(30), avgDias: avg };
  }, [rows, hoy]);

  // Barras por semana
  const barrasSemana = useMemo(() => {
    if (!rows.length) return [];
    const map = new Map();
    const toKey = (d) => {
      const dt = new Date(d);
      const tmp = new Date(Date.UTC(dt.getFullYear(), dt.getMonth(), dt.getDate()));
      const dayNum = (tmp.getUTCDay() + 6) % 7;
      tmp.setUTCDate(tmp.getUTCDate() - dayNum + 3);
      const firstThursday = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 4));
      const week = 1 + Math.round(((tmp - firstThursday)/86400000 - 3 + ((firstThursday.getUTCDay()+6)%7))/7);
      const y = tmp.getUTCFullYear();
      return `${y}-W${String(week).padStart(2,"0")}`;
    };
    rows.forEach(r => {
      if (!r.fecha_proximo_mantenimiento) return;
      const key = toKey(r.fecha_proximo_mantenimiento);
      map.set(key, (map.get(key) || 0) + 1);
    });
    return [...map.entries()].map(([wk, count]) => ({ semana: wk, equipos: count }))
      .sort((a,b) => a.semana.localeCompare(b.semana));
  }, [rows]);

  // Línea top críticos
  const lineaCriticos = useMemo(() => {
    return [...rows]
      .filter(r => Number.isFinite(+r.dias_restantes_aprox))
      .sort((a,b) => (+a.dias_restantes_aprox) - (+b.dias_restantes_aprox))
      .slice(0, 20)
      .map((r, idx) => ({ idx: idx + 1, equipo: r.equipo_codigo, dias: Number(r.dias_restantes_aprox) }));
  }, [rows]);

  return (
    <div className="pm-page">
      <h2 className="pm-title">Próximo Mantenimiento</h2>

      {/* Filtros */}
      <div className="card pm-filters">
        <div className="f-item">
          <label>Faena</label>
          <select value={faenaSel} onChange={(e) => setFaenaSel(e.target.value)}>
            <option value="">Selecciona faena…</option>
            {faenas.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div className="f-item">
          <label>Tipo de equipo (opcional)</label>
          <select
            value={tipoSel}
            onChange={(e) => setTipoSel(e.target.value)}
            disabled={!faenaSel || !tipos.length}
          >
            <option value="">Todos</option>
            {tipos.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      {/* KPI + gráficos */}
      {faenaSel && (
        <div className="kpi-chart-grid">
          <div className="card kpi-grid">
            <div className="kpi"><div className="kpi-label">Equipos evaluados</div><div className="kpi-value">{kpis.total}</div></div>
            <div className="kpi"><div className="kpi-label">Próx. ≤ 7 días</div><div className="kpi-value accent">{kpis.p7}</div></div>
            <div className="kpi"><div className="kpi-label">Próx. ≤ 15 días</div><div className="kpi-value">{kpis.p15}</div></div>
            <div className="kpi"><div className="kpi-label">Próx. ≤ 30 días</div><div className="kpi-value">{kpis.p30}</div></div>
            <div className="kpi"><div className="kpi-label">Prom. días restantes</div><div className="kpi-value">{fmtNum(kpis.avgDias, 1)}</div></div>
          </div>

          <div className="card pm-chart">
            <div className="chart-header"><h3>Equipos por semana de próximo mantenimiento</h3></div>
            <div className="chart-wrapper">
              {barrasSemana.length ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={barrasSemana} margin={{ top: 4, right: 8, left: 0, bottom: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="semana" interval={0} angle={-30} textAnchor="end" height={40} tick={{ fontSize: 10, fill: "#cbd5e1" }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#cbd5e1" }} />
                    <Tooltip contentStyle={{ background: "#0b1220", border: "1px solid #1f2937", color: "#e5e7eb" }} />
                    <Bar dataKey="equipos" fill="#60a5fa" radius={[8,8,0,0]}>
                      <LabelList dataKey="equipos" position="top" style={{ fill: "#cbd5e1", fontSize: 10 }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : <div className="empty small">Sin datos suficientes.</div>}
            </div>
          </div>

          <div className="card pm-chart">
            <div className="chart-header"><h3>Top 20 equipos más críticos (menos días restantes)</h3></div>
            <div className="chart-wrapper">
              {lineaCriticos.length ? (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={lineaCriticos} margin={{ top: 6, right: 8, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="idx" tick={{ fontSize: 10, fill: "#cbd5e1" }} />
                    <YAxis tick={{ fontSize: 10, fill: "#cbd5e1" }} />
                    <Tooltip
                      contentStyle={{ background: "#0b1220", border: "1px solid #1f2937", color: "#e5e7eb" }}
                      formatter={(v, n, p) => [`${v} días`, `Equipo ${p.payload.equipo}`]}
                      labelFormatter={(l) => `Ranking #${l}`}
                    />
                    <Line type="monotone" dataKey="dias" stroke="#34d399" strokeWidth={2} dot={{ r: 2 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : <div className="empty small">Sin datos suficientes.</div>}
            </div>
          </div>
        </div>
      )}

      {/* Estados */}
      {cargando && <div className="info">Cargando…</div>}
      {error && <div className="info error">{error}</div>}

      {/* Tabla */}
      <div className="card pm-table-card">
        <div className="table-scroll">
          <table className="pm-table">
            <thead>
              <tr>
                <th>Equipo</th>
                <th>Faena</th>
                <th>Horo. último mant.</th>
                <th>F. último mant.</th>
                <th>Prom. horas entre mant.</th>
                <th>Prom. horas diarias</th>
                <th>Días restantes</th>
                <th>F. próximo mant.</th>
                <th>Horo. estimado próximo</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={`${r.equipo_codigo}-${i}`}>
                  <td className="mono">{r.equipo_codigo}</td>
                  <td>{safe(r.faena)}</td>
                  <td className="mono">{fmtNum(r.horometro_ultimo_mantenimiento)}</td>
                  <td className="mono">{fmt(r.fecha_ultimo_mantenimiento)}</td>
                  <td className="mono">{fmtNum(r.promedio_horas_entre_mantenimientos)}</td>
                  <td className="mono">{fmtNum(r.promedio_horas_trabajadas_diarias, 2)}</td>
                  <td className="mono">{fmtNum(r.dias_restantes_aprox, 1)}</td>
                  <td className="mono">{fmt(r.fecha_proximo_mantenimiento)}</td>
                  <td className="mono">{fmtNum(r.horometro_estimado_proximo_mantenimiento)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!cargando && !error && rows.length === 0 && (
          <div className="empty">Selecciona faena (y opcionalmente tipo) para ver datos.</div>
        )}
      </div>
    </div>
  );
}
