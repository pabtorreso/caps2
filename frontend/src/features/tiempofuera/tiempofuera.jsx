import { useEffect, useMemo, useState } from "react";
import axios from "@/services/axiosInstance";
import "@/styles/tiempofuera.css";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, LabelList,
  PieChart, Pie, Cell,
} from "recharts";

const COLORS = ["#60a5fa","#34d399","#f472b6","#fbbf24","#c084fc","#f87171","#22d3ee","#a3e635","#f59e0b","#fb7185"];

export default function TiempoFuera() {
  const [faenas, setFaenas] = useState([]);
  const [tipos, setTipos]   = useState([]);
  const [equipos, setEquipos] = useState([]);

  const [faenaSel, setFaenaSel] = useState("");
  const [tipoSel, setTipoSel]   = useState("");
  const [equipoSel, setEquipoSel] = useState("");

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const nfmt = (n, d=2) => (Number.isFinite(+n) ? (+n).toFixed(d) : "—");

  // faenas
  useEffect(() => {
    (async () => {
      try { const { data } = await axios.get("/query/tiempo-fuera/filters/faenas"); if (data.ok) setFaenas(data.data); }
      catch { /* toast ya lo maneja el interceptor */ }
    })();
  }, []);

  // tipos
  useEffect(() => {
    setTipoSel(""); setTipos([]); setEquipoSel(""); setEquipos([]); setRows([]); setErr("");
    if (!faenaSel) return;
    (async () => {
      try { const { data } = await axios.get("/query/tiempo-fuera/filters/tipos", { params:{ faena: faenaSel }}); if (data.ok) setTipos(data.data); }
      catch {}
    })();
  }, [faenaSel]);

  // equipos
  useEffect(() => {
    setEquipoSel(""); setEquipos([]); setRows([]); setErr("");
    if (!faenaSel || !tipoSel) return;
    (async () => {
      try { const { data } = await axios.get("/query/tiempo-fuera/filters/equipos", { params:{ faena: faenaSel, tipo: tipoSel }}); if (data.ok) setEquipos(data.data); }
      catch {}
    })();
  }, [tipoSel, faenaSel]);

  // datos
  useEffect(() => {
    setRows([]); setErr("");
    if (!faenaSel) return;
    const controller = new AbortController();
    (async () => {
      setLoading(true);
      try {
        const { data } = await axios.get("/query/tiempo-fuera", {
          params: { faena: faenaSel, tipo: tipoSel || "", equipo: equipoSel || "", limit: 1000, offset: 0 },
          signal: controller.signal,
          timeout: 120000,
        });
        if (data.ok) setRows(data.data || []); else setErr(data.error || "Error");
      } catch (e) { if (e.name !== "CanceledError") setErr(e.message || "Error"); }
      finally { setLoading(false); }
    })();
    return () => controller.abort();
  }, [faenaSel, tipoSel, equipoSel]);

  // KPIs
  const kpis = useMemo(() => {
    if (!rows.length) return { equipos: 0, periodos: 0, promedio: 0 };
    const equipos = rows.length;
    const periodos = rows.reduce((a,b) => a + (Number(b.total_periodos_fuera_servicio)||0), 0);
    const prom = rows.reduce((a,b)=> a + (Number(b.promedio_dias_fuera_servicio)||0), 0) / equipos;
    return { equipos, periodos, promedio: prom };
  }, [rows]);

  // Gráfico: Top 20 por promedio de días fuera
  const topProm = useMemo(() => {
    return [...rows]
      .filter(r => Number.isFinite(+r.promedio_dias_fuera_servicio))
      .sort((a,b)=> (+b.promedio_dias_fuera_servicio) - (+a.promedio_dias_fuera_servicio))
      .slice(0,20)
      .map(r => ({ equipo: r.equipo_codigo, prom: +r.promedio_dias_fuera_servicio }));
  }, [rows]);

  // Pie: participación por faena (si la lista trae varias faenas)
  const pieFaenas = useMemo(() => {
    const m = new Map();
    rows.forEach(r => m.set(r.faena || "—", (m.get(r.faena || "—")||0) + 1));
    return [...m.entries()].map(([faena, cant]) => ({ faena, cant }));
  }, [rows]);

  return (
    <div className="tf-page">
      <h2 className="tf-title">Tiempo fuera de servicio</h2>

      <div className="card tf-filters">
        <div className="f-item">
          <label>Faena</label>
          <select value={faenaSel} onChange={e=>setFaenaSel(e.target.value)}>
            <option value="">Selecciona faena…</option>
            {faenas.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div className="f-item">
          <label>Tipo de equipo</label>
          <select value={tipoSel} onChange={e=>setTipoSel(e.target.value)} disabled={!faenaSel || !tipos.length}>
            <option value="">Todos</option>
            {tipos.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div className="f-item">
          <label>Equipo</label>
          <select value={equipoSel} onChange={e=>setEquipoSel(e.target.value)} disabled={!tipoSel || !equipos.length}>
            <option value="">Todos</option>
            {equipos.map(eq => <option key={eq} value={eq}>{eq}</option>)}
          </select>
        </div>
      </div>

{faenaSel && (
  <>
    {/* Fila 1: KPIs + Donut */}
    <div className="kpi-donut-grid">
      <div className="card kpi-grid">
        <div className="kpi"><div className="kpi-label">Equipos evaluados</div><div className="kpi-value">{kpis.equipos}</div></div>
        <div className="kpi"><div className="kpi-label">Periodos totales</div><div className="kpi-value">{kpis.periodos}</div></div>
        <div className="kpi"><div className="kpi-label">Prom. días fuera</div><div className="kpi-value accent">{nfmt(kpis.promedio, 2)}</div></div>
      </div>

      <div className="card tf-chart">
        <div className="chart-header"><h3>Equipos por faena (muestra)</h3></div>
        <div className="chart-wrapper">
          {pieFaenas.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieFaenas} dataKey="cant" nameKey="faena" innerRadius={60} outerRadius={90}>
                  {pieFaenas.map((_,i)=>(<Cell key={i} fill={COLORS[i%COLORS.length]} />))}
                </Pie>
                <Tooltip
                  contentStyle={{ background:"#0b1220", border:"1px solid #1f2937", color:"#e5e7eb" }}
                  formatter={(v,n,p)=>[`${v} equipos`, p?.payload?.faena]}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className="empty small">Sin datos.</div>}
        </div>
      </div>
    </div>

    {/* Fila 2: Gráfico de barras (solo) */}
    <div className="card tf-chart tf-bar-card">
      <div className="chart-header"><h3>Top 20 – Promedio días fuera</h3></div>
      <div className="chart-wrapper">
        {topProm.length ? (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={topProm} margin={{top:6,right:8,left:0,bottom:36}}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="equipo" interval={0} angle={-30} textAnchor="end" height={44} tick={{ fontSize: 10, fill: "#cbd5e1" }} />
              <YAxis tick={{ fontSize: 10, fill: "#cbd5e1" }} />
              <Tooltip contentStyle={{ background:"#0b1220", border:"1px solid #1f2937", color:"#e5e7eb" }} />
              <Bar dataKey="prom" fill="#60a5fa" radius={[8,8,0,0]}>
                <LabelList dataKey="prom" position="top" formatter={(v)=>nfmt(v,2)} style={{ fill:"#cbd5e1", fontSize:10 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : <div className="empty small">Sin datos.</div>}
      </div>
    </div>
  </>
)}


      {loading && <div className="info">Cargando…</div>}
      {err && <div className="info error">{err}</div>}

      <div className="card tf-table-card">
        <div className="table-scroll">
          <table className="tf-table">
            <thead>
              <tr>
                <th>Equipo</th><th>Faena</th><th>Tipo</th>
                <th>Periodos fuera</th><th>Prom. días fuera</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r,i)=>(
                <tr key={`${r.equipo_codigo}-${i}`}>
                  <td className="mono">{r.equipo_codigo}</td>
                  <td>{r.faena || "—"}</td>
                  <td>{r.tipo_equipo || "—"}</td>
                  <td className="mono">{r.total_periodos_fuera_servicio ?? "—"}</td>
                  <td className="mono">{nfmt(r.promedio_dias_fuera_servicio,2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!loading && !err && rows.length===0 && <div className="empty">Selecciona filtros para ver datos.</div>}
      </div>
    </div>
  );
}
