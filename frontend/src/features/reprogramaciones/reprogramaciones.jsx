import axios from "@/services/axiosInstance";
import "@/styles/reprogramaciones.css";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell, Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis, YAxis,
} from "recharts";

/* ===== Modal Full-Screen (JSX) ===== */
function Modal({ open, onClose, title = "", children }) {
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (e) => e.key === "Escape" && onClose && onClose();
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div className="modal modal-full" role="dialog" aria-modal="true" aria-label={title || "Detalle"} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>
        <div className="modal-content">{children}</div>
        <div className="modal-footer">
          <button className="btn ghost" onClick={onClose}>Cerrar</button>
        </div>
      </div>
    </div>
  );
}

const DONUT_COLORS = ["#60a5fa","#34d399","#f472b6","#fbbf24","#c084fc","#f87171","#22d3ee","#a3e635","#f59e0b","#fb7185"];

export default function Reprogramaciones() {
  // === estados ===
  const [faenas, setFaenas]   = useState([]);
  const [tipos, setTipos]     = useState([]);      // [{desc, ids: number[], equipos_count}]
  const [equipos, setEquipos] = useState([]);

  const [faenaId, setFaenaId]   = useState("");   // number | ""
  const [tipoIds, setTipoIds]   = useState([]);   // number[]
  const [tipoDesc, setTipoDesc] = useState("");   // string (solo para mostrar)
  const [equipoId, setEquipoId] = useState("");   // number | ""

  const [rows, setRows] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  const [detalleOpen, setDetalleOpen] = useState(false);
  const [detalleRow, setDetalleRow] = useState(null);
  const abrirDetalle = (row) => { setDetalleRow(row); setDetalleOpen(true); };
  const cerrarDetalle = () => { setDetalleOpen(false); setDetalleRow(null); };

  const [chartMode, setChartMode] = useState("bar");

  const safe = (v) => (v ?? "—");
  const fmt  = (v) => (v ? new Date(v).toLocaleString() : "—");

  // helper para normalizar arrays {id, desc}
  const toList = (arr) =>
    (arr ?? [])
      .map((x) => ({ id: Number(x.id), desc: String(x.desc) }))
      .filter((x) => Number.isFinite(x.id) && x.desc);

  // 1) faenas
  useEffect(() => {
    (async () => {
      try {
        const { data } = await axios.get("/query/reprogramaciones/filters/faenas");
        if (data?.ok) setFaenas(toList(data.data));
      } catch (e) {
        console.error(e);
      }
    })();
  }, []);

  // 2) tipos por faena
  useEffect(() => {
    // reset dependientes
    setTipoDesc(""); setTipoIds([]); setTipos([]);
    setEquipoId(""); setEquipos([]);
    setRows([]); setError("");
    if (faenaId === "") return;

    (async () => {
      try {
        const { data } = await axios.get("/query/reprogramaciones/filters/tipos", {
          params: { faena_id: faenaId },
        });
        if (data?.ok) {
          setTipos((data?.data ?? []).map(t => ({
            desc: String(t.desc),
            ids:  (t.ids || []).map(Number),
            equipos_count: Number(t.equipos_count || 0),
          })));
        }
      } catch (e) { console.error(e); }
    })();
  }, [faenaId]);

  // 3) equipos por faena + tipo(s)
  useEffect(() => {
    setEquipoId(""); setEquipos([]);
    setRows([]); setError("");
    if (faenaId === "" || !tipoIds.length) return;

    (async () => {
      try {
        const { data } = await axios.get("/query/reprogramaciones/filters/equipos", {
          params: { faena_id: faenaId, tipo_ids: tipoIds.join(",") },
        });
        if (data?.ok) setEquipos(toList(data.data));
      } catch (e) { console.error(e); }
    })();
  }, [tipoIds, faenaId]);

  // 4) resultados cuando hay los 3 seleccionados
  useEffect(() => {
    setRows([]); setError("");
    if (faenaId === "" || !tipoIds.length || equipoId === "") return;

    const controller = new AbortController();
    (async () => {
      setCargando(true);
      try {
        const { data } = await axios.get("/query/reprogramaciones", {
          params: {
            faena_id: faenaId,
            tipo_ids: tipoIds.join(","),   // <— múltiple
            equipo_id: equipoId,
            limit: 1000,
            offset: 0
          },
          signal: controller.signal,
        });
        if (data?.ok) setRows(data.data);
        else setError(data?.error || "Error desconocido");
      } catch (err) {
        if (err?.name !== "CanceledError") setError(err?.message || "Error de conexión");
      } finally {
        setCargando(false);
      }
    })();
    return () => controller.abort();
  }, [faenaId, tipoIds, equipoId]);

  // === KPIs / gráficos ===
  const promedioReprog = useMemo(() => {
    if (!rows.length) return 0;
    const porOTM = new Map();
    rows.forEach((r) => {
      const prev = porOTM.get(r.otm_numero) ?? 0;
      porOTM.set(r.otm_numero, Math.max(prev, Number(r.reprogramaciones_cantidad || 0)));
    });
    const vals = [...porOTM.values()];
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    return Number.isFinite(avg) ? avg : 0;
  }, [rows]);

  const chartData = useMemo(() => {
    const porOTM = new Map();
    rows.forEach((r) => {
      const curr = porOTM.get(r.otm_numero) ?? 0;
      porOTM.set(r.otm_numero, Math.max(curr, Number(r.reprogramaciones_cantidad || 0)));
    });
    return [...porOTM.entries()].map(([otm, rep]) => ({ otm, rep }))
      .sort((a, b) => b.rep - a.rep).slice(0, 20);
  }, [rows]);

  const motivosData = useMemo(() => {
    if (!rows.length) return [];
    const map = new Map();
    rows.forEach((r) => {
      const key = (r.reprogramaciones_motivo || "Sin motivo").trim();
      map.set(key, (map.get(key) || 0) + 1);
    });
    const arr = [...map.entries()].map(([name, value]) => ({ name, value }));
    arr.sort((a,b) => b.value - a.value);
    const top = arr.slice(0,8);
    const rest = arr.slice(8);
    const otros = rest.reduce((s, x) => s + x.value, 0);
    return otros ? [...top, { name: "Otros", value: otros }] : top;
  }, [rows]);

  return (
    <div className="rep-page">
      <h2 className="rep-title">Reprogramaciones</h2>

      {/* Filtros */}
      <div className="card rep-filters">
        <div className="f-item">
          <label>Faena</label>
          <select value={faenaId} onChange={(e) => setFaenaId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Selecciona faena…</option>
            {faenas.map((f) => <option key={f.id} value={f.id}>{f.desc}</option>)}
          </select>
        </div>

        <div className="f-item">
          <label>Tipo de equipo</label>
          <select
            value={tipoDesc}
            onChange={(e) => {
              const desc = e.target.value;
              setTipoDesc(desc || "");
              const found = tipos.find(t => t.desc === desc);
              setTipoIds(found ? found.ids : []);
              setEquipoId(""); setEquipos([]); setRows([]); setError("");
            }}
            disabled={faenaId === "" || !tipos.length}
          >
            <option value="">Selecciona tipo…</option>
            {tipos.map((t) => (
              <option key={t.desc} value={t.desc}>
                {t.desc}{t.equipos_count ? ` (${t.equipos_count})` : ""}
              </option>
            ))}
          </select>
        </div>

        <div className="f-item">
          <label>Equipo</label>
          <select
            value={equipoId}
            onChange={(e) => setEquipoId(e.target.value ? Number(e.target.value) : "")}
            disabled={(!tipoIds.length) || !equipos.length}
          >
            <option value="">Selecciona equipo…</option>
            {equipos.map((e) => <option key={e.id} value={e.id}>{e.desc}</option>)}
          </select>
        </div>
      </div>

      {(faenaId !== "" && tipoIds.length && equipoId !== "") && (
        <div className="kpi-chart-grid">
          <div className="card kpi-card">
            <div className="kpi-label">Prom. reprogramaciones por OTM</div>
            <div className="kpi-value">{promedioReprog.toFixed(2)}</div>
            <div className="kpi-sub">
              {rows.length ? `OTMs consideradas: ${new Set(rows.map(r => r.otm_numero)).size}` : "—"}
            </div>
          </div>

          <div className="card rep-chart">
            <div className="chart-header">
              <h3>
                {chartMode === "bar"
                  ? "Top 20 OTM por reprogramaciones"
                  : "Distribución por motivo de no cumplimiento"}
              </h3>

              <select
                className="chart-mode"
                value={chartMode}
                onChange={(e) => setChartMode(e.target.value === "donut" ? "donut" : "bar")}
              >
                <option value="bar">Barras</option>
                <option value="donut">Torta/Donut</option>
              </select>
            </div>

            <div className="chart-wrapper">
              {chartMode === "bar" ? (
                chartData.length ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 28 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="otm" angle={-45} textAnchor="end" interval={0} height={44} tick={{ fontSize: 10, fill: "#cbd5e1" }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#cbd5e1" }} />
                      <Tooltip contentStyle={{ background: "#0b1220", border: "1px solid #1f2937", color: "#e5e7eb" }} />
                      <Bar dataKey="rep" fill="#60a5fa" radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div className="empty small">No hay datos para el gráfico.</div>
              ) : (
                motivosData.length ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Tooltip contentStyle={{ background: "#0b1220", border: "1px solid #1f2937", color: "#e5e7eb" }} />
                      <Legend verticalAlign="bottom" height={36} />
                      <Pie data={motivosData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                        {motivosData.map((_, i) => <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />)}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                ) : <div className="empty small">No hay datos para el gráfico.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {cargando && <div className="info">Cargando…</div>}
      {error && <div className="info error">{error}</div>}

      <div className="card rep-table-card">
        <div className="table-scroll">
          <table className="rep-table">
            <thead>
              <tr>
                <th>OTM</th><th>Equipo</th><th>Faena</th>
                <th># Reprog.</th><th>F. Prog. Orig.</th><th>F. Inicio Real</th><th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={`${r.id_programa_otm}-${i}`}>
                  <td className="mono">{r.otm_numero}</td>
                  <td className="mono">{r.equipo_codigo}</td>
                  <td>{r.faena_nombre}</td>
                  <td className="mono">{r.reprogramaciones_cantidad}</td>
                  <td className="mono">{fmt(r.reg_fecha_programada_original)}</td>
                  <td className="mono">{fmt(r.reg_fecha_inicio_real)}</td>
                  <td><button className="btn tiny" onClick={() => abrirDetalle(r)}>Ver detalles</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!cargando && !error && rows.length === 0 && (
          <div className="empty">Selecciona faena, tipo y equipo para ver datos.</div>
        )}
      </div>

      <Modal open={detalleOpen && !!detalleRow} onClose={cerrarDetalle} title={`Detalle OTM ${detalleRow?.otm_numero ?? ""}`}>
        <div className="modal-grid">
          <div className="sec">
            <h4>Identificación</h4>
            <dl>
              <dt>ID Programa</dt><dd className="mono">{detalleRow?.id_programa_otm}</dd>
              <dt>OTM</dt><dd className="mono">{detalleRow?.otm_numero}</dd>
              <dt>Cód. Tarea</dt><dd className="mono">{detalleRow?.otm_codigo_tarea}</dd>
              <dt>Programador</dt><dd>{safe(detalleRow?.otm_usuario_programador)}</dd>
            </dl>
          </div>

          <div className="sec">
            <h4>Equipo</h4>
            <dl>
              <dt>Código</dt><dd className="mono">{detalleRow?.equipo_codigo}</dd>
              <dt>Tipo</dt><dd>{safe(detalleRow?.equipo_tipo)}</dd>
              <dt>Marca</dt><dd>{safe(detalleRow?.equipo_marca)}</dd>
              <dt>Modelo</dt><dd>{safe(detalleRow?.equipo_modelo)}</dd>
            </dl>
          </div>

          <div className="sec">
            <h4>Faena / Actividad</h4>
            <dl>
              <dt>Faena</dt><dd>{safe(detalleRow?.faena_nombre)}</dd>
              <dt>Cód. Interno</dt><dd className="mono">{safe(detalleRow?.faena_codigo_interno)}</dd>
              <dt>Actividad</dt><dd>{safe(detalleRow?.actividad_nombre)}</dd>
              <dt>Tipo Act.</dt><dd>MANTENIMIENTO</dd>
              <dt>Estado Act.</dt><dd>{safe(detalleRow?.actividad_estado)}</dd>
            </dl>
          </div>

          <div className="sec">
            <h4>Fechas</h4>
            <dl>
              <dt>F. Límite</dt><dd className="mono">{fmt(detalleRow?.otm_fecha_limite)}</dd>
              <dt>F. Ejecución</dt><dd className="mono">{fmt(detalleRow?.otm_fecha_ejecucion)}</dd>
              <dt>Inicio Prog.</dt><dd className="mono">{fmt(detalleRow?.otm_fecha_hora_inicio)}</dd>
              <dt>Fin Prog.</dt><dd className="mono">{fmt(detalleRow?.otm_fecha_hora_fin)}</dd>
              <dt>F. Prog. Orig.</dt><dd className="mono">{fmt(detalleRow?.reg_fecha_programada_original)}</dd>
              <dt>F. Inicio Real</dt><dd className="mono">{fmt(detalleRow?.reg_fecha_inicio_real)}</dd>
            </dl>
          </div>

          <div className="sec sec-span2">
            <h4>Reprogramaciones / Insumos</h4>
            <dl>
              <dt># Reprogramaciones</dt><dd className="mono">{detalleRow?.reprogramaciones_cantidad}</dd>
              <dt>Motivo no cumplimiento</dt><dd className="wrap">{safe(detalleRow?.reprogramaciones_motivo)}</dd>
              <dt>Disp. Insumos</dt><dd>{safe(detalleRow?.otm_disponibilidad_insumos)}</dd>
              <dt>Instrucciones</dt><dd className="wrap">{safe(detalleRow?.otm_instrucciones_especiales)}</dd>
            </dl>
          </div>
        </div>
      </Modal>
    </div>
  );
}
