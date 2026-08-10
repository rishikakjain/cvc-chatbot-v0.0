import React from 'react'
import ReactMarkdown from 'react-markdown'
import CourseCard from './CourseCard'
import { parseMessageContent } from './parseCourses'

function CourseInfoFooter() {
  return (
    <div className="course-info-footer">
      <div className="course-info-footer__item">
        <svg className="course-info-footer__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/>
        </svg>
        <div>
          <span className="course-info-footer__label">Financial Aid</span>
          <span className="course-info-footer__text">After enrolling at cvc.edu, select "Request to use Federal Financial Aid" on the confirmation page. Your home college reviews eligibility — you remain responsible for payment during review. California Promise Grant (CCPG) may also apply; re-apply through the teaching college.</span>
        </div>
      </div>
      <div className="course-info-footer__item">
        <svg className="course-info-footer__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
        </svg>
        <div>
          <span className="course-info-footer__label">Transcripts</span>
          <span className="course-info-footer__text">The teaching college automatically sends an electronic transcript to your home college within ~3 weeks of term end. Need it sooner, or transferring to a 4-year school? Request it directly from the teaching college — your Teaching College ID is in your CVC Exchange profile at search.cvc.edu.</span>
        </div>
      </div>
    </div>
  )
}

function BotContent({ content, onSaveCourse, savedCourses, onSearchGE }) {
  const blocks = parseMessageContent(content)
  const hasCourses = blocks.some(b => {
    if (b.type !== 'course') return false
    const c = b.course
    return c.college || c.delivery || c.startDate || c.professor || c.seatsAvailable != null || (c.ge && c.ge.length > 0)
  })

  return (
    <div className="bot-content">
      {blocks.map((block, i) => {
        if (block.type === 'course') {
          const c = block.course
          const isCourse = c.college || c.delivery || c.startDate || c.professor || c.seatsAvailable != null || (c.ge && c.ge.length > 0)
          if (!isCourse) {
            const fallback = `**${c.index}. ${c.name}${c.code ? ` (${c.code})` : ''}**${c.units ? ` — ${c.units} units` : ''}`
            return <ReactMarkdown key={i}>{fallback}</ReactMarkdown>
          }
          const key = `${c.name}|${c.college}`
          const isSaved = savedCourses.some(s => `${s.name}|${s.college}` === key)
          return <CourseCard key={i} course={c} index={c.index} isSaved={isSaved} onSave={() => onSaveCourse(c)} onSearchGE={onSearchGE} />
        }
        if (!block.content.trim()) return null
        return (
          <ReactMarkdown
            key={i}
            components={{
              a: ({ href, children }) => (
                <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
              ),
            }}
          >
            {block.content}
          </ReactMarkdown>
        )
      })}
      {hasCourses && <CourseInfoFooter />}
    </div>
  )
}

export default function Message({ role, content, isTyping, onSaveCourse, savedCourses, onSearchGE }) {
  const isBot = role === 'assistant'

  return (
    <div className={`message ${isBot ? 'message--bot' : 'message--user'}`}>
      {isBot && <div className="message__avatar" aria-hidden="true">A</div>}
      <div className="message__bubble">
        {isTyping ? (
          <span className="message__typing">
            <span /><span /><span />
          </span>
        ) : isBot ? (
          <BotContent content={content} onSaveCourse={onSaveCourse} savedCourses={savedCourses || []} onSearchGE={onSearchGE} />
        ) : (
          <p>{content}</p>
        )}
      </div>
    </div>
  )
}
