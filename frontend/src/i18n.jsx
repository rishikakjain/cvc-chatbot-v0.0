import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import translations from './translations'

export const LANGUAGES = [
  { code: 'en', flag: '🇺🇸', label: 'English' },
  { code: 'es', flag: '🇲🇽', label: 'Español' },
  { code: 'vi', flag: '🇻🇳', label: 'Tiếng Việt' },
  { code: 'zh', flag: '🇨🇳', label: '中文' },
  { code: 'tl', flag: '🇵🇭', label: 'Filipino' },
]

const STORAGE_KEY = 'cvc-lang'
const DEFAULT_LANG = 'en'

function detectBrowserLang() {
  const nav = navigator.language || navigator.userLanguage || DEFAULT_LANG
  const code = nav.split('-')[0].toLowerCase()
  return LANGUAGES.find(l => l.code === code) ? code : DEFAULT_LANG
}

const I18nContext = createContext(null)

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) || detectBrowserLang()
  })

  const setLang = useCallback((code) => {
    setLangState(code)
    localStorage.setItem(STORAGE_KEY, code)
  }, [])

  // t(key) returns the translated string for the current language,
  // falling back to English if the key is missing.
  const t = useCallback((key) => {
    return (translations[lang] && translations[lang][key]) ||
           translations[DEFAULT_LANG][key] ||
           key
  }, [lang])

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useLang() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useLang must be used within I18nProvider')
  return ctx
}
