import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'cvc-theme'
const FONT_SIZE_KEY = 'cvc-font-size'
export const FONT_SIZE_MIN = 12
export const FONT_SIZE_MAX = 20
export const FONT_SIZE_DEFAULT = 15

function getSystemPreference() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme)
}

const ThemeContext = createContext(null)

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) || getSystemPreference()
  })

  const [fontSize, setFontSizeState] = useState(() => {
    const stored = parseInt(localStorage.getItem(FONT_SIZE_KEY))
    return isNaN(stored) ? FONT_SIZE_DEFAULT : stored
  })

  useEffect(() => { applyTheme(theme) }, [theme])

  const setTheme = useCallback((t) => {
    setThemeState(t)
    localStorage.setItem(STORAGE_KEY, t)
  }, [])

  const toggleTheme = useCallback(() => {
    setThemeState(prev => {
      const next = prev === 'dark' ? 'light' : 'dark'
      localStorage.setItem(STORAGE_KEY, next)
      return next
    })
  }, [])

  const setFontSize = useCallback((v) => {
    const clamped = Math.min(FONT_SIZE_MAX, Math.max(FONT_SIZE_MIN, v))
    setFontSizeState(clamped)
    localStorage.setItem(FONT_SIZE_KEY, clamped)
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, fontSize, setFontSize }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
