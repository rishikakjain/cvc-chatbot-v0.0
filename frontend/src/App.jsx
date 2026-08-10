import React, { useState, useEffect, useRef } from 'react'
import Message from './components/Message'
import { sendMessage, clearSession, isMockMode } from './api'
import { useLang, LANGUAGES } from './i18n'
import { useTheme } from './theme'

function CVCLandingPage() {
  return (
    <div className="cvc-page">
      {/* Nav */}
      <header className="cvc-nav">
        <div className="cvc-nav__logo">
          <svg width="44" height="44" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="22" cy="22" r="20" stroke="white" strokeWidth="2" fill="none"/>
            <path d="M22 8 C14 8 8 14 8 22 C8 30 14 36 22 36 C30 36 36 30 36 22" stroke="white" strokeWidth="2" fill="none"/>
            <path d="M16 22 Q22 14 28 22 Q22 30 16 22Z" fill="white" opacity="0.7"/>
          </svg>
          <div className="cvc-nav__logo-text">
            <span className="cvc-nav__logo-ccc">California<br/>Community<br/>Colleges</span>
            <div className="cvc-nav__logo-divider"/>
            <span className="cvc-nav__logo-cvc">California<br/>Virtual Campus</span>
          </div>
        </div>
        <nav className="cvc-nav__links">
          <a href="#">Student Eligibility</a>
          <a href="#">Transcripts</a>
          <a href="#">Financial Aid</a>
          <a href="#">About</a>
          <a href="#">Support</a>
        </nav>
        <div className="cvc-nav__actions">
          <button className="cvc-btn cvc-btn--login">LOG IN</button>
          <button className="cvc-btn cvc-btn--educators">Educators Click Here &gt;</button>
        </div>
      </header>

      {/* Hero banner */}
      <div className="cvc-hero">
        <h1 className="cvc-hero__title">Students</h1>
      </div>

      {/* Content section */}
      <section className="cvc-content">
        <div className="cvc-content__left">
          <h2 className="cvc-content__heading">Check your eligibility</h2>
          <p className="cvc-content__body">
            To enroll in a course offered through the CVC, you must currently be enrolled at a California community college that is part of the CVC Exchange.
          </p>
          <button className="cvc-btn cvc-btn--check">CHECK YOUR ELIGIBILITY</button>
        </div>
        <div className="cvc-content__right">
          <div className="cvc-content__img-placeholder">
            <svg viewBox="0 0 480 320" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="480" height="320" fill="#c8d8e8"/>
              <ellipse cx="240" cy="280" rx="200" ry="60" fill="#a0bcd0" opacity="0.5"/>
              {/* Background trees */}
              <circle cx="360" cy="100" r="70" fill="#5a8a4a" opacity="0.7"/>
              <circle cx="410" cy="120" r="50" fill="#4a7a3a" opacity="0.6"/>
              <circle cx="300" cy="90" r="55" fill="#6a9a5a" opacity="0.5"/>
              {/* Bench/seating area */}
              <rect x="60" y="200" width="360" height="18" rx="4" fill="#d4c4a8"/>
              <rect x="80" y="218" width="320" height="30" rx="2" fill="#c4b498"/>
              {/* Person 1 - woman with laptop */}
              <ellipse cx="190" cy="165" rx="22" ry="26" fill="#c4956a"/>
              <rect x="155" y="188" width="70" height="55" rx="6" fill="#6b7c5a"/>
              {/* Hair */}
              <path d="M168 165 Q190 130 212 165 Q205 145 190 140 Q175 145 168 165Z" fill="#2a1a0a"/>
              <path d="M168 165 Q158 185 162 210" stroke="#2a1a0a" strokeWidth="8" fill="none"/>
              {/* Laptop */}
              <rect x="162" y="205" width="55" height="35" rx="3" fill="#e0e0e0"/>
              <rect x="165" y="208" width="49" height="28" rx="2" fill="#4a90d0"/>
              {/* Person 2 - man in background */}
              <ellipse cx="310" cy="175" rx="18" ry="20" fill="#8a6545"/>
              <rect x="288" y="193" width="44" height="45" rx="5" fill="#222"/>
              {/* Smile lines */}
              <path d="M304 178 Q310 183 316 178" stroke="#7a4a25" strokeWidth="1.5" fill="none"/>
            </svg>
          </div>
        </div>
      </section>

      {/* Second content row */}
      <section className="cvc-content cvc-content--alt">
        <div className="cvc-content__left">
          <h2 className="cvc-content__heading">Find courses that fit your goals</h2>
          <p className="cvc-content__body">
            Browse thousands of online courses from California Community Colleges. Filter by GE area, delivery method, start date, and more.
          </p>
          <button className="cvc-btn cvc-btn--check">SEARCH COURSES</button>
        </div>
        <div className="cvc-content__left" style={{paddingLeft: '40px'}}>
          <h2 className="cvc-content__heading">How CVC works</h2>
          <ol className="cvc-how-list">
            <li>Check your eligibility at your home college</li>
            <li>Find a course that meets your requirements</li>
            <li>Enroll with one click through CVC</li>
            <li>Complete the course — credit transfers automatically</li>
          </ol>
        </div>
      </section>
    </div>
  )
}

// Branching onboarding tree.
// Each node: { id, question, options: [{ label, value, next }] }
// next: node id string, 'done', or an 'exit_*' key handled in handleOnboardingAnswer
const ONBOARDING = {
  student_type: {
    id: 'student_type',
    question: "Hi! To find the right courses for you — what best describes you?",
    options: [
      { label: "CC student looking for courses at another CC", value: 'cc', next: 'visa_status' },
      { label: "UC or CSU student taking CC courses for credit", value: 'ucscu', next: 'visa_status_ucscu' },
      { label: "Just exploring", value: 'other', next: 'exit_other' },
    ],
  },
  visa_status: {
    id: 'visa_status',
    question: "Are you on an F-1 international student visa?",
    options: [
      { label: "No — I'm domestic", value: 'domestic', next: 'age_check' },
      { label: "Yes — F-1 visa", value: 'f1', next: 'exit_f1' },
    ],
  },
  visa_status_ucscu: {
    id: 'visa_status_ucscu',
    question: "Are you on an F-1 international student visa?",
    options: [
      { label: "No — I'm domestic", value: 'domestic', next: 'ucscu_type' },
      { label: "Yes — F-1 visa", value: 'f1', next: 'exit_f1' },
    ],
  },
  age_check: {
    id: 'age_check',
    question: "CVC requires students to be at least 18 years old. Are you 18 or older?",
    options: [
      { label: "Yes — I'm 18 or older", value: 'yes', next: 'gpa_check' },
      { label: "No — I'm under 18", value: 'no', next: 'exit_underage' },
    ],
  },
  gpa_check: {
    id: 'gpa_check',
    question: "Do you have a GPA of 2.0 or higher at your home college? (If this is your first term or you haven't completed a course yet, that's fine too.)",
    options: [
      { label: "Yes — 2.0 GPA or higher", value: 'yes', next: 'transfer_goal' },
      { label: "It's my first term / no GPA yet", value: 'first_term', next: 'transfer_goal' },
      { label: "No — my GPA is below 2.0", value: 'no', next: 'exit_gpa' },
    ],
  },
  transfer_goal: {
    id: 'transfer_goal',
    question: "Are you planning to transfer to a CSU or UC? This helps me recommend the right GE framework.",
    options: [
      { label: "CSU (Cal State)", value: 'csu', next: 'home_college' },
      { label: "UC (University of California)", value: 'uc', next: 'home_college' },
      { label: "Both / Not sure yet", value: 'unsure', next: 'home_college' },
    ],
  },
  ucscu_type: {
    id: 'ucscu_type',
    question: "Which type of school are you currently at?",
    options: [
      { label: "CSU (Cal State)", value: 'csu', next: 'home_college' },
      { label: "UC (University of California)", value: 'uc', next: 'home_college' },
    ],
  },
  home_college: {
    id: 'home_college',
    question: "What is your home college? (Type the name — this helps us exclude it from search results.)",
    type: 'text_input',
    placeholder: 'e.g. Victor Valley College',
    next: 'done',
  },
}

const FIRST_STEP = 'student_type'

function buildProfileMessage(answers) {
  const type = answers.student_type
  const goal = answers.transfer_goal
  const ucscu = answers.ucscu_type
  const homeCollege = answers.home_college

  const homePart = homeCollege ? ` My home college is ${homeCollege} — please exclude it from course search results.` : ''

  if (type === 'cc') {
    const goalLabel = { csu: 'a CSU (Cal State)', uc: 'a UC (University of California)', unsure: 'a CSU or UC (still deciding)' }
    return `My profile: I'm a domestic California Community College student (18+, GPA 2.0+) planning to transfer to ${goalLabel[goal] || 'a university'}.${homePart} I'm ready to find courses — let's get started.`
  }
  if (type === 'ucscu') {
    const schoolLabel = { csu: 'a CSU (Cal State)', uc: 'a UC (University of California)' }
    return `My profile: I'm a domestic student currently enrolled at ${schoolLabel[ucscu] || 'a UC or CSU'} and I want to take some courses at a California Community College through CVC for credit.${homePart} I'm ready to get started — what should I know first?`
  }
  return "I'm exploring how CVC works and what courses are available. Can you give me a quick overview?"
}

const PROFILE_KEY = 'cvc_profile'

function loadProfile() {
  try { return JSON.parse(localStorage.getItem(PROFILE_KEY)) } catch { return null }
}
function saveProfile(answers) {
  localStorage.setItem(PROFILE_KEY, JSON.stringify(answers))
}
function clearProfile() {
  localStorage.removeItem(PROFILE_KEY)
}

function profileSummary(answers) {
  if (!answers) return []
  const rows = []
  const typeMap = { cc: 'CC student (transfer)', ucscu: 'UC / CSU student', other: 'Exploring' }
  if (answers.student_type) rows.push({ label: 'Student type', value: typeMap[answers.student_type] || answers.student_type })
  const visaVal = answers.visa_status || answers.visa_status_ucscu
  if (visaVal) rows.push({ label: 'Visa status', value: visaVal === 'f1' ? 'F-1 international' : 'Domestic' })
  if (answers.age_check) rows.push({ label: 'Age 18+', value: answers.age_check === 'yes' ? 'Yes' : 'No' })
  if (answers.gpa_check) {
    const gpaMap = { yes: '2.0+', first_term: 'First term', no: 'Below 2.0' }
    rows.push({ label: 'GPA', value: gpaMap[answers.gpa_check] || answers.gpa_check })
  }
  if (answers.transfer_goal) {
    const goalMap = { csu: 'Transferring to CSU', uc: 'Transferring to UC', unsure: 'CSU or UC (undecided)' }
    rows.push({ label: 'Transfer goal', value: goalMap[answers.transfer_goal] || answers.transfer_goal })
  }
  if (answers.ucscu_type) {
    const typeMap2 = { csu: 'CSU', uc: 'UC' }
    rows.push({ label: 'Current school', value: typeMap2[answers.ucscu_type] || answers.ucscu_type })
  }
  if (answers.home_college) rows.push({ label: 'Home college', value: answers.home_college })
  return rows
}

function makeInitialMessages(hasProfile) {
  if (hasProfile) return [{ role: 'assistant', content: null, isWelcome: true }]
  return [
    { role: 'assistant', content: null, isWelcome: true },
    { role: 'assistant', content: ONBOARDING[FIRST_STEP].question, isOnboarding: true, stepId: FIRST_STEP },
  ]
}

export default function App() {
  const { t, lang, setLang } = useLang()
  const { theme, toggleTheme, fontSize, setFontSize } = useTheme()
  const [fontPopover, setFontPopover] = useState(false)
  const [profilePopover, setProfilePopover] = useState(false)

  const [open, setOpen] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)

  const savedAnswers = loadProfile()
  const [messages, setMessages] = useState(() => makeInitialMessages(!!savedAnswers))
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [homeCollege, setHomeCollege] = useState(null)
  const [unread, setUnread] = useState(1)
  const [savedCourses, setSavedCourses] = useState([])
  const [onboarding, setOnboarding] = useState(
    savedAnswers
      ? { stepId: FIRST_STEP, done: true, answers: savedAnswers }
      : { stepId: FIRST_STEP, done: false, answers: {} }
  )
  const [onboardingTextInput, setOnboardingTextInput] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  function handleClear() {
    clearSession()
    setSavedCourses([])
    setHomeCollege(null)
    setInput('')
    // Re-prime the backend with profile context on the fresh session
    const profile = loadProfile()
    setMessages([{ role: 'assistant', content: null, isWelcome: true }])
    if (profile) {
      const contextMsg = buildProfileMessage(profile)
      setLoading(true)
      sendMessage(contextMsg)
        .then(data => {
          setMessages(prev => [...prev, { role: 'assistant', content: data.reply, courses: data.courses || [] }])
          if (data.home_college) setHomeCollege(data.home_college)
        })
        .catch(() => {
          setMessages(prev => [...prev, { role: 'assistant', content: "Welcome back! What subject or GE area are you looking for today?" }])
        })
        .finally(() => setLoading(false))
    }
  }

  async function handleOnboardingTextSubmit(stepId, value) {
    const step = ONBOARDING[stepId]
    const trimmed = value.trim()
    if (!trimmed) return
    const newAnswers = { ...onboarding.answers, [step.id]: trimmed }
    setOnboardingTextInput('')
    setMessages(prev => [...prev, { role: 'user', content: trimmed }])

    if (step.next === 'done') {
      setOnboarding({ stepId, done: true, answers: newAnswers })
      saveProfile(newAnswers)
      const contextMsg = buildProfileMessage(newAnswers)
      setMessages(prev => [...prev, { role: 'user', content: contextMsg, isHidden: true }])
      setLoading(true)
      try {
        const data = await sendMessage(contextMsg)
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply, courses: data.courses || [] }])
        if (data.home_college) setHomeCollege(data.home_college)
      } catch {
        setMessages(prev => [...prev, { role: 'assistant', content: "Ready to help! What subject or GE area are you looking for?" }])
      } finally {
        setLoading(false)
        inputRef.current?.focus()
      }
    }
  }

  function handleResetProfile() {
    clearProfile()
    clearSession()
    setProfilePopover(false)
    const fresh = makeInitialMessages(false)
    setMessages(fresh)
    setSavedCourses([])
    setHomeCollege(null)
    setInput('')
    setOnboarding({ stepId: FIRST_STEP, done: false, answers: {} })
  }

  async function handleOnboardingAnswer(stepId, option) {
    const step = ONBOARDING[stepId]
    const newAnswers = { ...onboarding.answers, [step.id]: option.value }

    setMessages(prev => [...prev, { role: 'user', content: option.label }])

    if (option.next === 'exit_other') {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "No problem! CVC Exchange is open to California Community College students, but I can still walk you through what courses are available and how the system works. Feel free to ask anything.",
        isOnboarding: true,
      }])
      setOnboarding({ stepId, done: true, answers: newAnswers })
      saveProfile(newAnswers)
      return
    }

    if (option.next === 'exit_f1') {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Unfortunately, F-1 international students are not eligible to enroll through the CVC Exchange — enrolling at a second institution without prior approval could put your visa status at risk. You'd need to apply directly to each college via CCCApply. I can still help you understand available courses and general requirements. What would you like to know?",
        isOnboarding: true,
      }])
      setOnboarding({ stepId, done: true, answers: newAnswers })
      saveProfile(newAnswers)
      return
    }

    if (option.next === 'exit_underage') {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "CVC Exchange requires students to be at least 18 years old. Dual-enrolled high school students are not eligible for the Exchange — you'd need to apply directly to each college via CCCApply. Once you turn 18 and are enrolled at a CCC, come back and I can help you find courses!",
        isOnboarding: true,
      }])
      setOnboarding({ stepId, done: true, answers: newAnswers })
      saveProfile(newAnswers)
      return
    }

    if (option.next === 'exit_gpa') {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "CVC Exchange requires a GPA of 2.0 or higher to enroll. If your GPA is below 2.0, you'll need to raise it at your home college before using CVC. Your academic counselor can help you make a plan. I can still show you what courses exist so you know what to aim for — want to explore?",
        isOnboarding: true,
      }])
      setOnboarding({ stepId, done: true, answers: newAnswers })
      saveProfile(newAnswers)
      return
    }

    if (option.next === 'done') {
      setOnboarding({ stepId, done: true, answers: newAnswers })
      saveProfile(newAnswers)
      const contextMsg = buildProfileMessage(newAnswers)
      setMessages(prev => [...prev, { role: 'user', content: contextMsg, isHidden: true }])
      setLoading(true)
      try {
        const data = await sendMessage(contextMsg)
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply, courses: data.courses || [] }])
        if (data.home_college) setHomeCollege(data.home_college)
      } catch (err) {
        setMessages(prev => [...prev, { role: 'assistant', content: "Ready to help! What subject or GE area are you looking for?" }])
      } finally {
        setLoading(false)
        inputRef.current?.focus()
      }
      return
    }

    // Advance to next step
    const nextStep = ONBOARDING[option.next]
    if (nextStep) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: nextStep.question,
        isOnboarding: true,
        stepId: nextStep.id,
      }])
      setOnboarding({ stepId: nextStep.id, done: false, answers: newAnswers })
    }
  }

  function handleSaveCourse(course) {
    setSavedCourses(prev => {
      const key = `${course.name}|${course.college}`
      const already = prev.some(c => `${c.name}|${c.college}` === key)
      return already ? prev.filter(c => `${c.name}|${c.college}` !== key) : [...prev, course]
    })
  }

  function exportCourses() {
    if (!savedCourses.length) return
    const headers = ['Course Name', 'Code', 'College', 'Units', 'Delivery', 'Start Date', 'Professor', 'Seats Available', 'Seats Total', 'GE Tags', 'Note']
    const rows = savedCourses.map(c => [
      c.name || '',
      c.code || '',
      c.college || '',
      c.units || '',
      c.delivery || '',
      c.startDate || '',
      c.professor || '',
      c.seatsAvailable ?? '',
      c.seatsTotal ?? '',
      c.ge ? c.ge.join('; ') : '',
      c.note || '',
    ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))
    const csv = [headers.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'cvc-saved-courses.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  // On mount: if a profile already exists, prime the backend silently so the
  // model knows the student's context without them having to re-answer anything.
  useEffect(() => {
    if (!savedAnswers) return
    const contextMsg = buildProfileMessage(savedAnswers)
    setLoading(true)
    sendMessage(contextMsg)
      .then(data => {
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply, courses: data.courses || [] }])
        if (data.home_college) setHomeCollege(data.home_college)
      })
      .catch(() => {
        setMessages(prev => [...prev, { role: 'assistant', content: "Welcome back! What subject or GE area are you looking for today?" }])
      })
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (open) {
      setUnread(0)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  useEffect(() => {
    if (!fontPopover) return
    function close(e) {
      if (!e.target.closest('.header__fontsize-wrap')) setFontPopover(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [fontPopover])

  useEffect(() => {
    if (!profilePopover) return
    function close(e) {
      if (!e.target.closest('.header__profile-wrap')) setProfilePopover(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [profilePopover])

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, loading, open])

  async function handleSubmit(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)

    try {
      const data = await sendMessage(text)
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply, courses: data.courses || [] }])
      if (data.home_college) setHomeCollege(data.home_college)
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `${t('error_msg')}\n\n*${err.message}*`,
        },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  async function handleSearchGE(geTag) {
    if (loading) return
    const text = `Show me all available courses that satisfy ${geTag}`
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)
    try {
      const data = await sendMessage(text)
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply, courses: data.courses || [] }])
      if (data.home_college) setHomeCollege(data.home_college)
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: t('error_msg') }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e)
    }
  }

  const isDark = theme === 'dark'

  return (
    <>
      <CVCLandingPage />

      {/* Chat window */}
      <div
        className={`chat-window ${open ? 'chat-window--visible' : 'chat-window--hidden'} ${fullscreen ? 'chat-window--fullscreen' : ''}`}
        style={{ '--chat-font': `${fontSize}px` }}
        aria-hidden={!open}
      >
        {/* Header */}
        <header className="header">
          <div className="header__left">
            <div className="header__avatar">A</div>
            <div className="header__info">
              <span className="header__name">{t('advisor_name')}</span>
              <span className="header__status">
                {isMockMode() ? t('status_demo') : t('status_online')}
              </span>
            </div>
          </div>
          <div className="header__right">
            {/* Profile button */}
            <div className="header__profile-wrap">
              <button
                className={`header__profile${onboarding.done ? ' header__profile--set' : ''}`}
                onClick={() => setProfilePopover(p => !p)}
                aria-label="View or reset your profile"
                title="Your profile"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
              </button>
              {profilePopover && (
                <div className="profile-popover">
                  <div className="profile-popover__title">Your Profile</div>
                  {onboarding.done && profileSummary(onboarding.answers).length > 0 ? (
                    <ul className="profile-popover__list">
                      {profileSummary(onboarding.answers).map(row => (
                        <li key={row.label} className="profile-popover__row">
                          <span className="profile-popover__label">{row.label}</span>
                          <span className="profile-popover__value">{row.value}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="profile-popover__empty">No profile saved yet.</p>
                  )}
                  <button className="profile-popover__reset" onClick={handleResetProfile}>
                    Reset profile & start over
                  </button>
                </div>
              )}
            </div>

            {/* Export saved courses */}
            {savedCourses.length > 0 && (
              <button
                className="header__export"
                onClick={exportCourses}
                title={`Export ${savedCourses.length} saved course${savedCourses.length > 1 ? 's' : ''}`}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                <span>{savedCourses.length}</span>
              </button>
            )}

            {/* Language selector */}
            <div className="header__lang">
              <select
                value={lang}
                onChange={e => setLang(e.target.value)}
                aria-label="Select language"
              >
                {LANGUAGES.map(l => (
                  <option key={l.code} value={l.code}>
                    {l.flag} {l.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Font size */}
            <div className="header__fontsize-wrap">
              <button
                className="header__fontsize"
                onClick={() => setFontPopover(f => !f)}
                aria-label="Change font size"
                title="Adjust font size"
              >
                A
              </button>
              {fontPopover && (
                <div className="fontsize-popover">
                  <span className="fontsize-popover__label">Text size</span>
                  <div className="fontsize-popover__row">
                    <span className="fontsize-popover__sm">A</span>
                    <input
                      type="range"
                      min={12}
                      max={20}
                      step={1}
                      value={fontSize}
                      onChange={e => setFontSize(parseInt(e.target.value))}
                      className="fontsize-popover__slider"
                      aria-label="Font size"
                    />
                    <span className="fontsize-popover__lg">A</span>
                  </div>
                  <span className="fontsize-popover__value">{fontSize}px</span>
                </div>
              )}
            </div>

            {/* Theme toggle */}
            <button
              className="header__theme"
              onClick={toggleTheme}
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDark ? (
                /* Sun */
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="5"/>
                  <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                  <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                </svg>
              ) : (
                /* Moon */
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
              )}
            </button>

            <button
              className="header__expand"
              onClick={() => setFullscreen(f => !f)}
              aria-label={fullscreen ? t('exit_fullscreen') : t('fullscreen')}
            >
              {fullscreen ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="4 14 10 14 10 20" /><polyline points="20 10 14 10 14 4" />
                  <line x1="10" y1="14" x2="3" y2="21" /><line x1="21" y1="3" x2="14" y2="10" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="15 3 21 3 21 9" /><polyline points="9 21 3 21 3 15" />
                  <line x1="21" y1="3" x2="14" y2="10" /><line x1="3" y1="21" x2="10" y2="14" />
                </svg>
              )}
            </button>
            <button
              className="header__clear"
              onClick={handleClear}
              aria-label="Clear conversation"
              title="Clear conversation"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                <path d="M10 11v6"/>
                <path d="M14 11v6"/>
                <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
              </svg>
            </button>

            <button
              className="header__close"
              onClick={() => { setOpen(false); setFullscreen(false) }}
              aria-label={t('close')}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </header>

        {/* Messages */}
        <main className="chat">
          <div className="chat__messages">
            {messages.map((msg, i) => {
              if (msg.isHidden) return null
              const isLastOnboardingQ = msg.isOnboarding && msg.stepId && !onboarding.done && i === messages.length - 1
              const stepForMsg = isLastOnboardingQ ? ONBOARDING[msg.stepId] : null
              return (
                <React.Fragment key={i}>
                  <Message
                    role={msg.role}
                    content={msg.isWelcome ? t('welcome') : msg.content}
                    courses={msg.courses}
                    onSaveCourse={handleSaveCourse}
                    savedCourses={savedCourses}
                    onSearchGE={handleSearchGE}
                  />
                  {stepForMsg && stepForMsg.type === 'text_input' ? (
                    <form
                      className="quick-replies quick-replies--text"
                      onSubmit={e => { e.preventDefault(); handleOnboardingTextSubmit(msg.stepId, onboardingTextInput) }}
                    >
                      <input
                        className="quick-reply-input"
                        type="text"
                        placeholder={stepForMsg.placeholder || 'Type your answer…'}
                        value={onboardingTextInput}
                        onChange={e => setOnboardingTextInput(e.target.value)}
                        disabled={loading}
                        autoFocus
                      />
                      <button
                        type="submit"
                        className="quick-reply-btn quick-reply-btn--submit"
                        disabled={loading || !onboardingTextInput.trim()}
                      >
                        Continue →
                      </button>
                    </form>
                  ) : stepForMsg ? (
                    <div className="quick-replies">
                      {stepForMsg.options.map(opt => (
                        <button
                          key={opt.value}
                          className="quick-reply-btn"
                          onClick={() => handleOnboardingAnswer(msg.stepId, opt)}
                          disabled={loading}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </React.Fragment>
              )
            })}
            {loading && <Message role="assistant" isTyping />}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="chat__input-area">
            <form className="chat__form" onSubmit={handleSubmit}>
              <textarea
                ref={inputRef}
                className="chat__textarea"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('placeholder')}
                rows={1}
                disabled={loading}
                aria-label="Message"
              />
              <button
                type="submit"
                className="chat__send"
                disabled={!input.trim() || loading}
                aria-label="Send"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </form>
            <p className="chat__disclaimer">
              {t('disclaimer').split('{link}')[0]}
              <a href="https://cvc.edu" target="_blank" rel="noopener noreferrer">cvc.edu</a>
              {t('disclaimer').split('{link}')[1]}
            </p>
            <p className="chat__powered">
              {(() => {
                const str = t('powered_by')
                const parts = str.split('CVC')
                if (parts.length >= 2) {
                  return <>{parts[0]}<span>CVC</span>{parts.slice(1).join('CVC')}</>
                }
                return str
              })()}
            </p>
          </div>
        </main>
      </div>

      {/* Launcher bubble — hidden when fullscreen so it doesn't overlap the input */}
      <button
        className={`chat-launcher${fullscreen ? ' chat-launcher--hidden' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-label={open ? t('close') : 'Open CVC course advisor'}
      >
        {open ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
        {!open && unread > 0 && (
          <span className="chat-launcher__badge">{unread}</span>
        )}
      </button>
    </>
  )
}
