import axios from "@/services/axiosInstance";

export async function iniciarActualizacion() {
  return axios.post("/query/actualizar/iniciar");
}

export async function obtenerEstadoActualizacion() {
  return axios.get("/query/actualizar/estado");
}
