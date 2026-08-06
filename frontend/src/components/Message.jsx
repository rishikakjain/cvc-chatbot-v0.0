import React from 'react'
import ReactMarkdown from 'react-markdown'
import CourseCard from './CourseCard'
import { parseMessageContent } from './parseCourses'

function BotContent({ content, onSaveCourse, savedCourses }) {
  const blocks = parseMessageContent(content)

  return (
    <div className="bot-content">
      {blocks.map((block, i) => {
        if (block.type === 'course') {
          const c = block.course
          const isCourse = c.delivery || c.startDate || c.professor || c.seatsAvailable != null || c.seatsTotal != null || (c.ge && c.ge.length > 0)
          if (!isCourse) {
            const fallback = `**${c.index}. ${c.name}${c.code ? ` (${c.code})` : ''}**${c.units ? ` — ${c.units} units` : ''}`
            return <ReactMarkdown key={i}>{fallback}</ReactMarkdown>
          }
          const key = `${c.name}|${c.college}`
          const isSaved = savedCourses.some(s => `${s.name}|${s.college}` === key)
          return <CourseCard key={i} course={c} index={c.index} isSaved={isSaved} onSave={() => onSaveCourse(c)} />
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
    </div>
  )
}

export default function Message({ role, content, isTyping, onSaveCourse, savedCourses }) {
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
          <BotContent content={content} onSaveCourse={onSaveCourse} savedCourses={savedCourses || []} />
        ) : (
          <p>{content}</p>
        )}
      </div>
    </div>
  )
}
