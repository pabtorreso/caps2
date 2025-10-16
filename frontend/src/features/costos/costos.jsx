import { useEffect, useMemo, useState } from "react";
import axios from "@/services/axiosInstance";
import "@/styles/costos.css";
import {
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
  PieChart, Pie, Cell,
} from "recharts";

/** Paleta */
const CHART_COLORS = ["#60a5fa","#34d399","#f472b6","#fbbf24","#c084fc","#f87171","#22d3ee","#a3e635","#f59e0b","#fb7185"];

export default function Costos() {
  // ==== filtros ====
  const [faenas, setFaenas] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [equipos, setEquipos] = useState([]);

  const [faenaSel, setFaenaSel] = useState("");
  const [tipoSel, setTipoSel] = useState("");
  const [equipoSel, setEquipoSel] = useState("");

  // ==== data ====
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ==== helpers ====
  const safe = (v) => (v ?? "—");
  const fmtMoney = (n) =>
    (typeof n === "number" && isFinite(n))
      ? n.toLocaleString(undefined, { style: "currency", currency: "CLP", maximumFractionDigits: 0 })
      : "—";
  const parseDate = (v) => (v ? new Date(v) : null);

  // Escoge el mejor monto disponible por fila (factura > OC > neto > item)
  const filaMonto = (r) => {
    const vals = [
      Number(r.compra_monto_total_factura),
      Number(r.compra_valor_total),
      Number(r.compra_monto_neto),
      Number(r.compra_monto_item),
    ].map((x) => (isFinite(x) ? x : 0));
    return Math.max(...vals, 0);
  };

  // ==== cargar filtros ====
  useEffect(() => {
    (async () => {
      try {
        // Endpoint sugerido: adapta si tu backend usa otro path
        const { data } = await axios.get("/query/costos/filters/faenas");
        if (data?.ok) setFaenas(data.data);
      } catch (e) { console.error(e); }
    })();
  }, []);

  useEffect(() => {
    setTipoSel(""); setTipos([]);
    setEquipoSel(""); setEquipos([]);
    setRows([]);

    if (!faenaSel) return;
    (async () => {
      try {
        const { data } = await axios.get("/query/costos/filters/tipos", { params: { faena: faenaSel } });
        if (data?.ok) setTipos(data.data);
      } catch (e) { console.error(e); }
    })();
  }, [faenaSel]);

  useEffect(() => {
    setEquipoSel(""); setEquipos([]);
    setRows([]);

    if (!faenaSel || !tipoSel) return;
    (async () => {
      try {
        const { data } = await axios.get("/query/costos/filters/equipos", {
          params: { faena: faenaSel, tipo: tipoSel },
        });
        if (data?.ok) setEquipos(data.data);
      } catch (e) { console.error(e); }
    })();
  }, [faenaSel, tipoSel]);

  // ==== cargar tabla ====
  useEffect(() => {
    setRows([]); setError("");
    if (!faenaSel || !equipoSel) return;

    const controller = new AbortController();
    (async () => {
      setLoading(true);
      try {
        // Endpoint sugerido: /query/costos -> devuelve filas compatibles con la query compartida
        const { data } = await axios.get("/query/costos", {
          params: { faena: faenaSel, equipo: equipoSel, limit: 1000, offset: 0 },
          signal: controller.signal,
        });
        if (data?.ok) setRows(data.data || []);
        else setError(data?.error || "Error desconocido");
      } catch (err) {
        if (err.name !== "CanceledError") setError(err?.message || "Error de conexión");
      } finally { setLoading(false); }
    })();

    return () => controller.abort();
  }, [faenaSel, equipoSel]);

  // ==== KPIs ====
  const kpis = useMemo(() => {
    const total = rows.reduce((s, r) => s + filaMonto(r), 0);
    const solicitudes = new Set(rows.map((r) => r.compra_numero_solicitud).filter(Boolean)).size;
    const otms = new Set(rows.map((r) => r.otm_numero).filter(Boolean)).size;
    const promPorOTM = otms ? total / otms : 0;
    return { total, solicitudes, otms, promPorOTM };
  }, [rows]);

  // ==== chart: Top 10 proveedores por gasto ====
  const topProveedores = useMemo(() => {
    const map = new Map();
    rows.forEach((r) => {
      const prov = r.nombre_proveedor || "Sin proveedor";
      map.set(prov, (map.get(prov) || 0) + filaMonto(r));
    });
    return [...map.entries()]
      .map(([proveedor, gasto]) => ({ proveedor, gasto }))
      .sort((a, b) => b.gasto - a.gasto)
      .slice(0, 10);
  }, [rows]);

  // ==== chart: Distribución por cuenta contable ====
  const cuentasDistrib = useMemo(() => {
    const map = new Map();
    rows.forEach((r) => {
      const key = r.descripcion_cuenta || r.id_cuenta || "Sin cuenta";
      map.set(key, (map.get(key) || 0) + filaMonto(r));
    });
    const arr = [...map.entries()].map(([name, value]) => ({ name, value }));
    arr.sort((a, b) => b.value - a.value);
    const top = arr.slice(0, 8);
    const rest = arr.slice(8);
    const otros = rest.reduce((s, x) => s + x.value, 0);
    return otros ? [...top, { name: "Otros", value: otros }] : top;
  }, [rows]);

  // ==== chart: Gasto por mes (últimos 12) ====
  const gastoPorMes = useMemo(() => {
    const map = new Map();
    rows.forEach((r) => {
      const d = parseDate(r.compra_fecha_solicitud) || parseDate(r.compra_fecha_factura);
      if (!d) return;
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      map.set(key, (map.get(key) || 0) + filaMonto(r));
    });
    const arr = [...map.entries()]
      .map(([mes, total]) => ({ mes, total }))
      .sort((a, b) => (a.mes < b.mes ? -1 : 1))
      .slice(-12);
    return arr;
  }, [rows]);

  return (
    <div className="costos-page">
      <h2 className="costos-title">Costos e Insumos</h2>

      {/* Filtros */}
      <div className="card cst-filters">
        <div className="f-item">
          <label>Faena</label>
          <select value={faenaSel} onChange={(e) => setFaenaSel(e.target.value)}>
            <option value="">Selecciona faena…</option>
            {faenas.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div className="f-item">
          <label>Tipo de equipo</label>
          <select
            value={tipoSel}
            onChange={(e) => setTipoSel(e.target.value)}
            disabled={!faenaSel || !tipos.length}
          >
            <option value="">Selecciona tipo…</option>
            {tipos.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div className="f-item">
          <label>Equipo</label>
          <select
            value={equipoSel}
            onChange={(e) => setEquipoSel(e.target.value)}
            disabled={!tipoSel || !equipos.length}
          >
            <option value="">Selecciona equipo…</option>
            {equipos.map((e) => <option key={e} value={e}>{e}</option>)}
          </select>
        </div>
      </div>

      {/* KPIs */}
      {(faenaSel && equipoSel) && (
        <div className="cst-kpi-grid">
          <div className="card kpi kpi-main">
            <div className="kpi-label">Gasto total</div>
            <div className="kpi-value">{fmtMoney(kpis.total)}</div>
            <div className="kpi-sub">
              {kpis.otms ? `OTMs: ${kpis.otms} • Prom/OTM: ${fmtMoney(kpis.promPorOTM)}` : "—"}
            </div>
          </div>
          <div className="card kpi">
            <div className="kpi-label"># Solicitudes</div>
            <div className="kpi-value small">{kpis.solicitudes}</div>
            <div className="kpi-sub">Con ítems vinculados</div>
          </div>
        </div>
      )}

      {/* Gráficos */}
      {(faenaSel && equipoSel) && (
        <div className="cst-charts-grid">
          <div className="card cst-chart">
            <div className="cst-chart-title">Top 10 proveedores por gasto</div>
            <div className="cst-chart-wrap">
              {topProveedores.length ? (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={topProveedores} margin={{ top: 6, right: 8, left: 0, bottom: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="proveedor" interval={0} angle={-30} textAnchor="end" height={46} tick={{ fontSize: 10, fill: "#cbd5e1" }} />
                    <YAxis tick={{ fontSize: 10, fill: "#cbd5e1" }} />
                    <Tooltip formatter={(v) => fmtMoney(v)} contentStyle={{ background: "#0b1220", border: "1px solid #1f2937", color: "#e5e7eb" }} />
                    <Bar dataKey="gasto" fill="#60a5fa" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <div className="empty small">Sin datos.</div>}
            </div>
          </div>

          <div className="card cst-chart">
            <div className="cst-chart-title">Distribución por cuenta contable</div>
            <div className="cst-chart-wrap">
              {cuentasDistrib.length ? (
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Legend verticalAlign="bottom" height={40} />
                    <Tooltip formatter={(v) => fmtMoney(v)} contentStyle={{ background: "#0b1220", border: "1px solid #1f2937", color: "#e5e7eb" }} />
                    <Pie data={cuentasDistrib} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
                      {cuentasDistrib.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              ) : <div className="empty small">Sin datos.</div>}
            </div>
          </div>

          <div className="card cst-chart cst-span2">
            <div className="cst-chart-title">Gasto por mes</div>
            <div className="cst-chart-wrap">
              {gastoPorMes.length ? (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={gastoPorMes} margin={{ top: 6, right: 8, left: 0, bottom: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="mes" tick={{ fontSize: 10, fill: "#cbd5e1" }} />
                    <YAxis tick={{ fontSize: 10, fill: "#cbd5e1" }} />
                    <Tooltip formatter={(v) => fmtMoney(v)} contentStyle={{ background: "#0b1220", border: "1px solid #1f2937", color: "#e5e7eb" }} />
                    <Bar dataKey="total" fill="#34d399" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <div className="empty small">Sin datos.</div>}
            </div>
          </div>
        </div>
      )}

      {/* Estado */}
      {loading && <div className="info">Cargando…</div>}
      {error && <div className="info error">{error}</div>}

      {/* Tabla */}
      <div className="card cst-table-card">
        <div className="table-scroll">
          <table className="rep-table">
            <thead>
              <tr>
                <th>OTM</th>
                <th>Equipo</th>
                <th>Proveedor</th>
                <th>Cuenta</th>
                <th>Solicitud</th>
                <th>OC</th>
                <th>Factura</th>
                <th>Fecha Sol.</th>
                <th>Monto</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={`${r.id_programa_otm}-${r.compra_numero_solicitud || i}`}>
                  <td className="mono">{r.otm_numero}</td>
                  <td className="mono">{r.equipo_codigo}</td>
                  <td className="wrap">{safe(r.nombre_proveedor)}</td>
                  <td className="wrap">{safe(r.descripcion_cuenta || r.id_cuenta)}</td>
                  <td className="mono">{safe(r.compra_numero_solicitud)}</td>
                  <td className="mono">{safe(r.compra_orden)}</td>
                  <td className="mono">{safe(r.compra_monto_total_factura ? "Sí" : "—")}</td>
                  <td className="mono">
                    {(() => {
                      const d = parseDate(r.compra_fecha_solicitud) || parseDate(r.compra_fecha_factura);
                      return d ? d.toLocaleString() : "—";
                    })()}
                  </td>
                  <td className="mono">{fmtMoney(filaMonto(r))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!loading && !error && rows.length === 0 && (
          <div className="empty">Selecciona faena, tipo y equipo para ver datos.</div>
        )}
      </div>
    </div>
  );
}
