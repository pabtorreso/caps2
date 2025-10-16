import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import logo from "@/assets/iconos/Indemin-logo.png";
import "@/styles/login.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faEye, faEyeSlash } from "@fortawesome/free-solid-svg-icons";
import Spinner from "@/components/spinner";
import axios from "@/services/axiosInstance";
import { iniciarActualizacion, obtenerEstadoActualizacion } from "@/services/actualizarService";
import dayjs from "dayjs";
import "dayjs/locale/es";

dayjs.locale("es");

function Login() {
  const [email, setEmail] = useState("");
  const [pin, setPin] = useState("");
  const [showPin, setShowPin] = useState(false);
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Fondo de la vista
  useEffect(() => {
    document.body.classList.add("login-bg");
    return () => document.body.classList.remove("login-bg");
  }, []);

  // Cargar "remember me"
  useEffect(() => {
    const remembered = localStorage.getItem("rememberMe") === "true";
    if (remembered) {
      setEmail(localStorage.getItem("email") || "");
      setRemember(true);
    }
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return toast.error("Correo inválido");
    }
    if (!/^\d{4}$/.test(pin)) {
      return toast.error("El PIN debe tener 4 dígitos");
    }

    setLoading(true);

    try {
      const res = await axios.post("/login", { email, password: pin });
      const data = res.data;

      if (res.status === 200) {
        toast.success("Login exitoso");

        // Persistencia básica
        localStorage.setItem("token", data.token);
        localStorage.setItem("id_usuario", data.user.id_usuario);
        localStorage.setItem("userEmail", data.user.email);
        localStorage.setItem("usuario", JSON.stringify(data.user));

        // Expiración (2 horas = 7200000 ms)
        const expiresAt = Date.now() + 2 * 60 * 60 * 1000;
        localStorage.setItem("expires_at", String(expiresAt));

        // Remember me
        if (remember) {
          localStorage.setItem("rememberMe", "true");
          localStorage.setItem("email", email);
        } else {
          localStorage.removeItem("rememberMe");
          localStorage.removeItem("email");
        }

// Iniciar ETL en segundo plano
const toastId = toast.loading("Actualizando datos...");
try {
  await iniciarActualizacion();

  // Polling del estado hasta finalizar o hasta timeout
  const startTs = Date.now();
  const timeoutMs = 8 * 60 * 1000; // 8 minutos
  const intervalId = window.setInterval(async () => {
    try {
      // ⬇️ el backend devuelve el estado DIRECTO
      const resEstado = await obtenerEstadoActualizacion();
      const estado = resEstado?.data;   // ✅ no .estado

      // Si aún ejecutando o sin estado, continuar (con timeout)
      if (!estado || estado.status === "ejecutando") {
        if (Date.now() - startTs > timeoutMs) {
          window.clearInterval(intervalId);
          toast.error("La actualización excedió el tiempo de espera", { id: toastId });
        }
        return;
      }

      // Cortar polling al salir de 'ejecutando'
      window.clearInterval(intervalId);

      if (estado.status === "completado") {
        // ⬇️ usar 'ultimo_fin' (no 'fin')
        const fecha = estado.ultimo_fin
          ? dayjs(estado.ultimo_fin).format("DD/MM/YYYY HH:mm")
          : dayjs().format("DD/MM/YYYY HH:mm");

        toast.success(`Datos actualizados • ${fecha}`, { id: toastId });

        if (estado.ultimo_fin) {
          localStorage.setItem("ultima_actualizacion", estado.ultimo_fin);
        }
      } else if (estado.status === "error") {
        // Puedes mostrar más detalle con estado.mensaje si quieres
        toast.error("Error al actualizar datos", { id: toastId });
        console.error(estado.mensaje);
      } else {
        toast.dismiss(toastId);
      }
    } catch (e) {
      window.clearInterval(intervalId);
      toast.error("No se pudo consultar el estado de actualización", { id: toastId });
      console.error(e);
    }
  }, 3000);

  // Por si el componente se desmonta antes de completar:
  const clearOnUnload = () => window.clearInterval(intervalId);
  window.addEventListener("beforeunload", clearOnUnload, { once: true });

} catch (e) {
  toast.error("No se pudo iniciar la actualización");
  console.error(e);
}

        // Navegar al home. Los toasts y el polling continúan en segundo plano.
        navigate("/", { replace: true });
      } else {
        toast.error(data.message || "Credenciales inválidas");
      }
    } catch (error) {
      toast.error("Error al conectarse al servidor");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      {loading && <Spinner />}
      <div className="box-area">
        <div className="login-left">
          <img src={logo} alt="Logo Indemin" />
        </div>

        <div className="login-right">
          <h2>Bienvenido</h2>

          <form onSubmit={handleLogin} noValidate>
            {/* Email */}
            <div className="mb-3">
              <label htmlFor="email" className="form-label">Correo</label>
              <input
                id="email"
                name="email"
                type="email"
                className="form-control"
                placeholder="correo@empresa.cl"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                aria-required="true"
              />
            </div>

            {/* PIN */}
            <div className="mb-3 input-group pin-input-group">
              <label htmlFor="pin" className="form-label visually-hidden">PIN</label>
              <input
                id="pin"
                name="pin"
                type={showPin ? "text" : "password"}
                className="form-control pin-input"
                placeholder="PIN de 4 dígitos"
                maxLength={4}
                inputMode="numeric"
                autoComplete="one-time-code"
                value={pin}
                onChange={(e) => /^\d{0,4}$/.test(e.target.value) && setPin(e.target.value)}
                required
                aria-required="true"
              />
              <button
                type="button"
                className="toggle-visibility"
                onClick={() => setShowPin((s) => !s)}
                aria-label={showPin ? "Ocultar PIN" : "Mostrar PIN"}
                title={showPin ? "Ocultar PIN" : "Mostrar PIN"}
              >
                <FontAwesomeIcon icon={showPin ? faEyeSlash : faEye} />
              </button>
            </div>

            {/* Remember me */}
            <div className="form-check mb-3">
              <input
                id="rememberMe"
                name="rememberMe"
                type="checkbox"
                className="form-check-input"
                checked={remember}
                onChange={() => setRemember((r) => !r)}
              />
              <label className="form-check-label" htmlFor="rememberMe">
                Recuérdame
              </label>
            </div>

            <button type="submit" className="btn-custom" disabled={loading}>
              {loading ? "Ingresando..." : "Ingresar"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Login;
