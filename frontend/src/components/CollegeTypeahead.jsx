import React, { useState, useRef, useEffect, useCallback } from 'react'
import { CA_COLLEGES } from '../data/colleges'

const MAX_SUGGESTIONS = 8

function score(college, query) {
  const c = college.toLowerCase()
  const q = query.toLowerCase().trim()
  if (!q) return 0
  if (c === q) return 100
  if (c.startsWith(q)) return 90
  // Any word in the college name starts with the query
  if (c.split(' ').some(w => w.startsWith(q))) return 80
  // Substring match
  if (c.includes(q)) return 70
  return 0
}

function getSuggestions(query) {
  if (!query || query.trim().length < 1) return []
  return CA_COLLEGES
    .map(c => ({ name: c, s: score(c, query) }))
    .filter(x => x.s > 0)
    .sort((a, b) => b.s - a.s || a.name.localeCompare(b.name))
    .slice(0, MAX_SUGGESTIONS)
    .map(x => x.name)
}

export default function CollegeTypeahead({ value, onChange, onSelect, placeholder, disabled }) {
  const [suggestions, setSuggestions] = useState([])
  const [activeIdx, setActiveIdx] = useState(-1)
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)

  useEffect(() => {
    const results = getSuggestions(value)
    setSuggestions(results)
    setOpen(results.length > 0)
    setActiveIdx(-1)
  }, [value])

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handleDown(e) {
      if (!wrapRef.current?.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleDown)
    return () => document.removeEventListener('mousedown', handleDown)
  }, [open])

  function handleKeyDown(e) {
    if (e.key === 'ArrowDown') {
      if (!open || !suggestions.length) return
      e.preventDefault()
      setActiveIdx(i => Math.min(i + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      if (!open || !suggestions.length) return
      e.preventDefault()
      setActiveIdx(i => Math.max(i - 1, -1))
    } else if (e.key === 'Enter' && open && suggestions.length > 0) {
      // Always pick from the dropdown when it's open — use highlighted item or fall back to top result
      e.preventDefault()
      pick(suggestions[activeIdx >= 0 ? activeIdx : 0])
    } else if (e.key === 'Escape') {
      setOpen(false)
      setActiveIdx(-1)
    }
  }

  function pick(name) {
    onSelect(name)
    setOpen(false)
    setSuggestions([])
    setActiveIdx(-1)
  }

  // Highlight matched portion of suggestion
  function highlight(text, query) {
    const idx = text.toLowerCase().indexOf(query.toLowerCase().trim())
    if (idx < 0 || !query.trim()) return text
    return (
      <>
        {text.slice(0, idx)}
        <strong>{text.slice(idx, idx + query.trim().length)}</strong>
        {text.slice(idx + query.trim().length)}
      </>
    )
  }

  return (
    <div className="typeahead-wrap" ref={wrapRef}>
      <input
        className="quick-reply-input"
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={open}
      />
      {open && suggestions.length > 0 && (
        <ul className="typeahead-list" role="listbox">
          {suggestions.map((name, i) => (
            <li
              key={name}
              className={`typeahead-item${i === activeIdx ? ' typeahead-item--active' : ''}`}
              role="option"
              aria-selected={i === activeIdx}
              onMouseDown={e => { e.preventDefault(); pick(name) }}
              onMouseEnter={() => setActiveIdx(i)}
            >
              {highlight(name, value)}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
