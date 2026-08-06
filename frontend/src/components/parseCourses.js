/**
 * Parse course blocks out of the LLM's markdown reply.
 *
 * Recognises the numbered-bold heading pattern the model reliably produces:
 *   "1. **Course Name (CODE)** — N units"
 *   bullet lines: Delivery, Start Date, Professor, Available Seats, GE, Note
 *
 * Returns { blocks: [{type:'text'|'course', ...}] }
 * so the renderer can interleave prose and cards.
 */

const HEADING_RE = /^(\d+)\.\s+\*\*(.+?)(?:\s*\(([A-Z]{2,6}\s*\d+[A-Z]?)\))?\*\*(?:\s*[—–-]\s*(\d+(?:\.\d+)?)\s*units?)?/i

const BULLET_RE = /^[\s]*[-•◦]\s+\*\*([^:*]+):\*\*\s*(.*)/

function parseSeatString(str) {
  // "33 out of 40"  or  "33"  or  "33 / 40"
  const m = str.match(/(\d+)\s*(?:out of|\/)\s*(\d+)/)
  if (m) return { seatsAvailable: parseInt(m[1]), seatsTotal: parseInt(m[2]) }
  const n = str.match(/(\d+)/)
  if (n) return { seatsAvailable: parseInt(n[1]), seatsTotal: null }
  return {}
}

function parseGeString(str) {
  // "CSU B4, IGETC 2A, Cal-GETC 2A"  →  ["CSU B4", "IGETC 2A", "Cal-GETC 2A"]
  return str.split(/[,;]/).map(s => s.trim()).filter(Boolean)
}

export function parseMessageContent(markdown) {
  if (!markdown) return [{ type: 'text', content: '' }]

  const lines = markdown.split('\n')
  const blocks = []
  let currentText = []
  let currentCourse = null

  function flushText() {
    const text = currentText.join('\n').trim()
    if (text) blocks.push({ type: 'text', content: text })
    currentText = []
  }

  function flushCourse() {
    if (currentCourse) {
      blocks.push({ type: 'course', course: currentCourse })
      currentCourse = null
    }
  }

  for (const line of lines) {
    const headingMatch = line.match(HEADING_RE)
    if (headingMatch) {
      flushText()
      flushCourse()
      const [, idx, rawName, codeInName, units] = headingMatch
      // code might be embedded in the name "Course Name (CODE)"
      const code = codeInName || null
      const name = rawName.replace(/\s*\([A-Z]{2,6}\s*\d+[A-Z]?\)\s*$/, '').trim()
      currentCourse = { index: parseInt(idx), name, code, units: units ? parseFloat(units) : null }
      continue
    }

    if (currentCourse) {
      const bulletMatch = line.match(BULLET_RE)
      if (bulletMatch) {
        const [, key, val] = bulletMatch
        const k = key.toLowerCase().trim()
        if (k.includes('college')) currentCourse.college = val.trim()
        else if (k.includes('delivery')) currentCourse.delivery = val.trim()
        else if (k.includes('start')) currentCourse.startDate = val.trim()
        else if (k.includes('professor') || k.includes('instructor')) currentCourse.professor = val.trim()
        else if (k.includes('seat') || k.includes('available')) {
          Object.assign(currentCourse, parseSeatString(val))
        }
        else if (k === 'ge' || k.includes('ge tag') || k.includes('ge area')) {
          currentCourse.ge = parseGeString(val)
        }
        else if (k.includes('note')) currentCourse.note = val.trim()
        continue
      }
      // Non-bullet line while inside a course — could be end of block
      if (line.trim() === '') continue
      // If it looks like prose (not a bullet), end the course block
      flushCourse()
    }

    currentText.push(line)
  }

  flushCourse()
  flushText()

  return blocks
}
