import React from 'react'
import { createRoot } from 'react-dom/client'
import WebApp from '@twa-dev/sdk'
import App from './App.jsx'
import './styles.css'

if (WebApp.initData) {
  WebApp.ready()
  WebApp.expand()
  document.documentElement.dataset.telegram = 'true'
  if (WebApp.colorScheme) document.documentElement.dataset.telegramTheme = WebApp.colorScheme
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App telegramUser={WebApp.initDataUnsafe?.user} />
  </React.StrictMode>,
)
