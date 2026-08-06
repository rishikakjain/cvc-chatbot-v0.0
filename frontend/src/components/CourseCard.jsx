import React from 'react'
import { useLang } from '../i18n'

function SeatsBar({ available, total }) {
  if (available == null) return null
  const pct = total > 0 ? Math.round((available / total) * 100) : 0
  const color = pct > 50 ? '#22c55e' : pct > 20 ? '#f59e0b' : '#ef4444'
  return (
    <div className="course-card__seats-bar-wrap">
      <div className="course-card__seats-bar">
        <div className="course-card__seats-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="course-card__seats-label" style={{ color }}>
        {available} seats left{total ? ` / ${total}` : ''}
      </span>
    </div>
  )
}

function buildCounselorMailto(course) {
  const { name, code, college, units, startDate, professor, ge, delivery } = course
  const geList = ge && ge.length ? ge.join(', ') : 'not listed'
  const subject = encodeURIComponent(
    `Articulation Check – ${name}${code ? ` (${code})` : ''} via CVC`
  )
  const body = encodeURIComponent(
`Hello,

I found a course through the California Virtual Campus (CVC) that I would like to take, and I need your help verifying whether it satisfies my GE or transfer requirements at our college.

COURSE DETAILS
──────────────────────────────
Course:       ${name}${code ? ` (${code})` : ''}
Offered by:   ${college || 'CVC partner college'}
Units:        ${units || 'N/A'}
Delivery:     ${delivery || 'N/A'}
Start Date:   ${startDate || 'N/A'}
Instructor:   ${professor || 'N/A'}
GE Tags:      ${geList}
──────────────────────────────

My questions:
1. Does this course satisfy any GE or major requirements at our college?
2. Is there an articulation agreement between our college and ${college || 'the teaching college'} for this course?
3. Do I need approval or any additional steps before enrolling through CVC?

I can enroll directly at cvc.edu once I have your confirmation. Thank you!`
  )
  return `mailto:?subject=${subject}&body=${body}`
}

export default function CourseCard({ course, index, isSaved, onSave }) {
  const { t } = useLang()
  const { name, code, units, college, delivery, startDate, professor, seatsAvailable, seatsTotal, ge, note } = course

  const isAsync = (delivery || '').toLowerCase().includes('async')
  const isSync = (delivery || '').toLowerCase().includes('sync')

  return (
    <div className="course-card">
      <div className="course-card__header">
        <div className="course-card__index">{index}</div>
        <div className="course-card__title-wrap">
          <span className="course-card__name">{name}</span>
          {code && <span className="course-card__code">{code}</span>}
          {college && <span className="course-card__college">{college}</span>}
        </div>
        {units && <span className="course-card__units">{units} units</span>}
      </div>

      <div className="course-card__chips">
        {ge && ge.map(tag => {
          const upper = tag.toUpperCase()
          let cls = 'course-card__chip--ge'
          if (upper.startsWith('IGETC')) cls = 'course-card__chip--igetc'
          else if (upper.startsWith('CAL-GETC') || upper.startsWith('CAL/GETC') || upper.startsWith('CALGETC')) cls = 'course-card__chip--calgetc'
          return <span key={tag} className={`course-card__chip ${cls}`}>{tag}</span>
        })}
        {isAsync && <span className="course-card__chip course-card__chip--async">Async</span>}
        {isSync && <span className="course-card__chip course-card__chip--sync">Sync</span>}
      </div>

      <div className="course-card__meta">
        {startDate && (
          <div className="course-card__meta-row">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            {startDate}
          </div>
        )}
        {professor && (
          <div className="course-card__meta-row">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
            </svg>
            {professor}
          </div>
        )}
      </div>

      <SeatsBar available={seatsAvailable} total={seatsTotal} />

      {note && <p className="course-card__note">{note}</p>}

      <div className="course-card__actions">
        <button
          className="enroll-btn"
          onClick={() => window.open('https://cvc.edu', '_blank', 'noopener,noreferrer')}
          title={`Enroll in ${name} at cvc.edu`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
            <polyline points="15 3 21 3 21 9"/>
            <line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
          {t('enroll_btn')}
        </button>

        <a
          className="counselor-btn"
          href={buildCounselorMailto(course)}
          title="Email your home counselor to verify articulation"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
            <polyline points="22,6 12,13 2,6"/>
          </svg>
          Ask Counselor
        </a>

        <button
          className={`save-btn${isSaved ? ' save-btn--saved' : ''}`}
          onClick={onSave}
          title={isSaved ? 'Remove from saved' : 'Save this course'}
        >
          <svg viewBox="0 0 24 24" fill={isSaved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
          </svg>
          {isSaved ? 'Saved' : 'Save'}
        </button>
      </div>
    </div>
  )
}
