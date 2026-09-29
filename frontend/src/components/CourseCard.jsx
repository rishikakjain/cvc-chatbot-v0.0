import React, { useState } from 'react'
import { useLang } from '../i18n'
import MailtoWarningDialog from './MailtoWarningDialog'

function SeatsGauge({ available, total, t }) {
  if (available == null) return null
  const pct = total > 0 ? Math.round((available / total) * 100) : 0
  const color = pct > 50 ? '#22c55e' : pct > 20 ? '#f59e0b' : '#ef4444'
  const label = pct > 50 ? t('card_seats_good') : pct > 20 ? t('card_seats_filling') : t('card_seats_full')
  return (
    <div className="cc-seats">
      <div className="cc-seats__bar-wrap">
        <div className="cc-seats__bar">
          <div className="cc-seats__fill" style={{ width: `${pct}%`, background: color }} />
        </div>
      </div>
      <div className="cc-seats__meta">
        <span className="cc-seats__count" style={{ color }}>{available}{total ? ` / ${total}` : ''} {t('card_seats')}</span>
        <span className="cc-seats__label" style={{ color }}>{label}</span>
      </div>
    </div>
  )
}

function GEChip({ tag, onSearch }) {
  const upper = tag.toUpperCase()
  let cls = 'cc-chip--csu'
  if (upper.startsWith('IGETC')) cls = 'cc-chip--igetc'
  else if (upper.startsWith('CAL-GETC') || upper.startsWith('CAL/GETC') || upper.startsWith('CALGETC')) cls = 'cc-chip--calgetc'
  else if (upper.startsWith('CSU')) cls = 'cc-chip--csu'
  return (
    <button
      className={`cc-chip cc-chip--btn ${cls}`}
      onClick={() => onSearch && onSearch(tag)}
      title={`Find equivalent courses at other colleges satisfying ${tag}`}
    >
      {tag}
      <svg className="cc-chip__search" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
    </button>
  )
}


export default function CourseCard({ course, index, isSaved, onSave, onSearchGE }) {
  const { t } = useLang()
  const { name, code, units, college, delivery, startDate, endDate, professor, seatsAvailable, seatsTotal, ge, note, isZtc, counselorEmail } = course
  const [showMailtoWarning, setShowMailtoWarning] = useState(false)

  const deliveryLower = (delivery || '').toLowerCase()
  // Use word-boundary check: "asynchronous" must not match sync chip
  const isAsync = deliveryLower.includes('async')
  const isSync = !isAsync && deliveryLower.includes('sync')

  return (
    <div className="cc">
      {/* Top accent bar */}
      <div className="cc__accent" />

      {/* Header row */}
      <div className="cc__header">
        <div className="cc__index">{index}</div>
        <div className="cc__title-block">
          <span className="cc__name">{name}</span>
          <div className="cc__sub">
            {code && <span className="cc__code">{code}</span>}
            {college && <span className="cc__college">@ {college}</span>}
          </div>
        </div>
        {units && <span className="cc__units">{units}<small>u</small></span>}
      </div>

      {/* GE + delivery + ZTC chips */}
      {((ge && ge.length > 0) || isAsync || isSync || isZtc) && (
        <div className="cc__chips">
          {ge && ge.map(tag => <GEChip key={tag} tag={tag} onSearch={onSearchGE} />)}
          {isZtc && (
            <span className="cc-chip cc-chip--ztc">
              <svg className="cc-chip__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
              ZTC
            </span>
          )}
          {isAsync && (
            <span className="cc-chip cc-chip--async">
              <svg className="cc-chip__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
              Async
            </span>
          )}
          {isSync && (
            <span className="cc-chip cc-chip--sync">
              <svg className="cc-chip__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
              Sync
            </span>
          )}
        </div>
      )}

      {/* Meta grid — always renders all four cells for consistent layout */}
      <div className="cc__grid">
        <div className="cc__cell">
          <svg className="cc__cell-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          <div className="cc__cell-body">
            <span className="cc__cell-label">{t('card_starts')}</span>
            <span className={`cc__cell-val${!startDate ? ' cc__cell-val--empty' : ''}`}>{startDate || '—'}</span>
          </div>
        </div>
        <div className="cc__cell">
          <svg className="cc__cell-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <div className="cc__cell-body">
            <span className="cc__cell-label">{t('card_ends')}</span>
            <span className={`cc__cell-val${!endDate ? ' cc__cell-val--empty' : ''}`}>{endDate || '—'}</span>
          </div>
        </div>
        <div className="cc__cell">
          <svg className="cc__cell-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          <div className="cc__cell-body">
            <span className="cc__cell-label">{t('card_instructor')}</span>
            <span className={`cc__cell-val${!professor ? ' cc__cell-val--empty' : ''}`}>{professor || '—'}</span>
          </div>
        </div>
        <div className="cc__cell">
          <svg className="cc__cell-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          <div className="cc__cell-body">
            <span className="cc__cell-label">{t('card_format')}</span>
            <span className={`cc__cell-val${!delivery ? ' cc__cell-val--empty' : ''}`}>{delivery || '—'}</span>
          </div>
        </div>
      </div>

      {/* Seats gauge */}
      <SeatsGauge available={seatsAvailable} total={seatsTotal} t={t} />

      {/* Note */}
      {note && (
        <div className="cc__note">
          <svg className="cc__note-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <span>{note}</span>
        </div>
      )}

      {/* Actions */}
      <div className="cc__actions">
        <button
          className="enroll-btn"
          onClick={() => window.open('https://cvc.edu', '_blank', 'noopener,noreferrer')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
            <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
          {t('enroll_btn')}
        </button>

        <button className={`save-btn${isSaved ? ' save-btn--saved' : ''}`} onClick={onSave} title={isSaved ? t('saved_btn') : t('save_btn')}>
          <svg viewBox="0 0 24 24" fill={isSaved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
          </svg>
          {isSaved ? t('saved_btn') : t('save_btn')}
        </button>
      </div>

      {/* Counselor reminder */}
      <div className="cc__counselor-note">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span>{t('counselor_note')}</span>
        {counselorEmail && (
          <button
            className="cc__counselor-email"
            type="button"
            onClick={() => setShowMailtoWarning(true)}
          >
            Contact Counselor
          </button>
        )}
      </div>

      {showMailtoWarning && (
        <MailtoWarningDialog
          href={`mailto:${counselorEmail}`}
          onClose={() => setShowMailtoWarning(false)}
        />
      )}
    </div>
  )
}
