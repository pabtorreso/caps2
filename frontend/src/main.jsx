import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { Toaster } from 'react-hot-toast';
import router from './router'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Toaster
      position="top-right"
      reverseOrder={false}
      toastOptions={{
        style: {
          marginTop: "50px",
          borderRadius: "8px",
          background: "#fff",
          color: "#000",
          fontSize: "14px",
        },
      }}
    />
    <RouterProvider router={router} />
  </React.StrictMode>,
)
