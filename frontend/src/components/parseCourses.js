/**
 * Parse course blocks out of the LLM markdown reply.
 *
 * Strategy: collect every numbered/bold heading + its following bullet lines,
 * then decide if it's a course by checking whether any course-specific bullets
 * (College, Delivery, Professor, Seats, GE, Start Date) are present.
 * This tolerates format drift in the heading (units missing, code position varies).
 */

// Heading with bold:   "1. **Name (CODE)** — N units"
// Heading without bold: "1. Name (CODE)"  or  "1. Name: Subtitle and More"
const HEADING_RE = /^(?:(\d+)\.\s+)?\*\*(.+?)\*\*(?:\s*[—–-]\s*(\d+(?:\.\d+)?)\s*units?)?/i
const HEADING_PLAIN_RE = /^(\d+)\.\s+([^*\n]{4,})$/
// Bullet with bold key:  "- **College:** value"
// Bullet without bold key: "- College: value"
const BOLD_LABEL_RE = /^[\s]*[-•◦*]\s+\*\*([^:*]+):\*\*\s*(.*)/
const PLAIN_LABEL_RE = /^[\s]*[-•◦*]\s+([A-Za-z ]{2,24}):\s+(.*)/

// All recognised field labels (lowercased)
const FIELD_MAP = {
  college: 'college',
  'teaching college': 'college',
  delivery: 'delivery',
  'delivery method': 'delivery',
  'start date': 'startDate',
  start: 'startDate',
  'end date': 'endDate',
  end: 'endDate',
  professor: 'professor',
  instructor: 'professor',
  teacher: 'professor',
  faculty: 'professor',
  'taught by': 'professor',
  'professor name': 'professor',
  'instructor name': 'professor',
  'available seats': 'seats',
  seats: 'seats',
  'seats available': 'seats',
  ge: 'ge',
  'ge credit': 'ge',
  'ge tags': 'ge',
  'ge areas': 'ge',
  'transfer credit': 'ge',
  note: 'note',
  notes: 'note',
  units: 'units',
  'time commitment': 'note',
}

const COURSE_FIELDS = new Set(['college', 'delivery', 'startDate', 'professor', 'seats', 'ge'])

function parseSeatString(str) {
  const m = str.match(/(\d+)\s*(?:out of|\/|of)\s*(\d+)/)
  if (m) return { seatsAvailable: parseInt(m[1]), seatsTotal: parseInt(m[2]) }
  const n = str.match(/(\d+)/)
  if (n) return { seatsAvailable: parseInt(n[1]), seatsTotal: null }
  return {}
}

function parseGeString(str) {
  return str.split(/[,;]/).map(s => s.trim()).filter(Boolean)
}

function extractCodeFromName(raw) {
  // "College Algebra (MATH 232)" → { name: "College Algebra", code: "MATH 232" }
  const parenMatch = raw.match(/^(.*?)\s*\(([A-Z]{2,8}\s*\d+[A-Z]?)\)\s*$/)
  if (parenMatch) return { name: parenMatch[1].trim(), code: parenMatch[2].trim() }
  // "KIN 201: Introduction to Exercise Physiology" → { name: "Introduction to Exercise Physiology", code: "KIN 201" }
  const colonMatch = raw.match(/^([A-Z]{2,8}\s*\d+[A-Z]?):\s*(.+)$/)
  if (colonMatch) return { name: colonMatch[2].trim(), code: colonMatch[1].trim() }
  return { name: raw.trim(), code: null }
}

export function parseMessageContent(markdown) {
  if (!markdown) return [{ type: 'text', content: '' }]

  const lines = markdown.split('\n')
  const blocks = []
  let currentText = []
  let currentHeading = null  // { idx, raw, lineText }
  let currentBullets = {}    // accumulated field values

  function flushText() {
    const text = currentText.join('\n').trim()
    if (text) blocks.push({ type: 'text', content: text })
    currentText = []
  }

  function flushHeading() {
    if (!currentHeading) return
    const hasCourseField = Object.keys(currentBullets).some(k => COURSE_FIELDS.has(k))

    if (hasCourseField) {
      // Build course object
      const { name, code } = extractCodeFromName(currentHeading.raw)
      const autoIdx = blocks.filter(b => b.type === 'course').length + 1
      const course = {
        index: currentHeading.idx ?? autoIdx,
        name,
        code: currentBullets.code || code,
        units: currentBullets.units ? parseFloat(currentBullets.units) : currentHeading.units,
        college: currentBullets.college || null,
        delivery: currentBullets.delivery || null,
        startDate: currentBullets.startDate || null,
        endDate: currentBullets.endDate || null,
        professor: currentBullets.professor || null,
        note: currentBullets.note || null,
        ge: currentBullets.ge || [],
        ...(currentBullets.seats ? parseSeatString(currentBullets.seats) : {}),
      }
      blocks.push({ type: 'course', course })
    } else {
      // Not a course — push heading line back as text
      currentText.push(currentHeading.lineText)
    }

    currentHeading = null
    currentBullets = {}
  }

  for (const line of lines) {
    // Try bold heading first, then plain numbered heading
    let headingIdx = null, headingRaw = null, headingUnits = null
    const boldMatch = line.match(HEADING_RE)
    if (boldMatch) {
      const [, idx, rawName, units] = boldMatch
      const isLikelyHeader = idx || units || rawName.length > 8
      if (isLikelyHeader) {
        headingIdx = idx ? parseInt(idx) : null
        headingRaw = rawName
        headingUnits = units ? parseFloat(units) : null
      }
    }
    // Plain numbered heading: "1. KIN 201: Introduction to Exercise Physiology"
    if (!headingRaw) {
      const plainMatch = line.match(HEADING_PLAIN_RE)
      if (plainMatch) {
        const candidate = plainMatch[2].trim()
        // Reject lines that end in colon (e.g. "1. Course Info:") — those are section headers
        // Reject lines that look like sentences (period mid-text)
        if (!candidate.endsWith(':') && !/\.\s/.test(candidate)) {
          headingIdx = parseInt(plainMatch[1])
          headingRaw = candidate
          headingUnits = null
        }
      }
    }

    if (headingRaw) {
      flushText()
      flushHeading()
      currentHeading = {
        idx: headingIdx,
        raw: headingRaw,
        units: headingUnits,
        lineText: line,
      }
      continue
    }

    if (currentHeading) {
      // Try bold label first, then plain label
      const bulletMatch = line.match(BOLD_LABEL_RE) || line.match(PLAIN_LABEL_RE)
      if (bulletMatch) {
        const [, key, val] = bulletMatch
        const mapped = FIELD_MAP[key.toLowerCase().trim()]
        if (mapped) {
          if (mapped === 'ge') {
            currentBullets.ge = parseGeString(val)
          } else {
            currentBullets[mapped] = val.trim()
          }
        }
        // Stay in card even for unrecognised bullet keys (e.g. "Time Commitment:", "Next Steps:")
        continue
      }
      // Blank line → stay in course context
      if (line.trim() === '') continue
      // Non-bullet non-blank line → end of course block
      flushHeading()
    }

    currentText.push(line)
  }

  flushHeading()
  flushText()

  return blocks
}
