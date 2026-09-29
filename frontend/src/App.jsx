import React, { useState, useEffect, useRef } from 'react'
import Message from './components/Message'
import CollegeTypeahead from './components/CollegeTypeahead'
import { sendMessage, clearSession, isMockMode } from './api'
import { useLang, LANGUAGES } from './i18n'
import { useTheme } from './theme'

function CVCLandingPage() {
  return (
    <div className="cvc-page">
      {/* Nav */}
      <header className="cvc-nav">
        <div className="cvc-nav__logo">
          <svg width="36" height="36" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="22" cy="22" r="20" stroke="white" strokeWidth="2" fill="none"/>
            <path d="M22 8 C14 8 8 14 8 22 C8 30 14 36 22 36 C30 36 36 30 36 22" stroke="white" strokeWidth="2" fill="none"/>
            <path d="M16 22 Q22 14 28 22 Q22 30 16 22Z" fill="white" opacity="0.85"/>
          </svg>
          <div className="cvc-nav__logo-text">
            <span className="cvc-nav__logo-name">California Virtual Campus</span>
            <span className="cvc-nav__logo-sub">California Community Colleges</span>
          </div>
        </div>
        <nav className="cvc-nav__links">
          <a href="#">Eligibility</a>
          <a href="#">Courses</a>
          <a href="#">Transcripts</a>
          <a href="#">Financial Aid</a>
          <a href="#">Support</a>
        </nav>
        <div className="cvc-nav__actions">
          <button className="cvc-btn cvc-btn--educators">For Educators</button>
          <button className="cvc-btn cvc-btn--login">Log In</button>
        </div>
      </header>

      {/* Hero */}
      <section className="cvc-hero">
        <div className="cvc-hero__bg-shapes">
          <div className="cvc-hero__shape cvc-hero__shape--1"/>
          <div className="cvc-hero__shape cvc-hero__shape--2"/>
          <div className="cvc-hero__shape cvc-hero__shape--3"/>
        </div>
        <div className="cvc-hero__content">
          <div className="cvc-hero__badge">California Community Colleges</div>
          <h1 className="cvc-hero__title">
            Take online courses.<br/>
            Transfer your credits.
          </h1>
          <p className="cvc-hero__subtitle">
            Access thousands of online courses from over 115 California Community Colleges — all in one place, fully transferable.
          </p>
          <div className="cvc-hero__ctas">
            <button className="cvc-btn cvc-btn--primary">Check Eligibility</button>
            <button className="cvc-btn cvc-btn--ghost">Browse Courses →</button>
          </div>
        </div>
        <div className="cvc-hero__visual">
          <div className="cvc-hero__stats">
            <div className="cvc-hero__stat">
              <span className="cvc-hero__stat-num">115+</span>
              <span className="cvc-hero__stat-label">Colleges</span>
            </div>
            <div className="cvc-hero__stat-divider"/>
            <div className="cvc-hero__stat">
              <span className="cvc-hero__stat-num">2M+</span>
              <span className="cvc-hero__stat-label">Students Served</span>
            </div>
            <div className="cvc-hero__stat-divider"/>
            <div className="cvc-hero__stat">
              <span className="cvc-hero__stat-num">100%</span>
              <span className="cvc-hero__stat-label">Online</span>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="cvc-steps">
        <div className="cvc-steps__inner">
          <div className="cvc-section-label">How it works</div>
          <h2 className="cvc-section-title">Enroll in four simple steps</h2>
          <div className="cvc-steps__grid">
            {[
              { n: '01', title: 'Check eligibility', body: "Confirm you're enrolled at a CVC Exchange member college." },
              { n: '02', title: 'Find your course', body: 'Search by GE requirement, subject, delivery method, or start date.' },
              { n: '03', title: 'Enroll instantly', body: 'Register through CVC with a single click — no separate application.' },
              { n: '04', title: 'Earn your credit', body: 'Complete the course and credit transfers automatically to your home college.' },
            ].map(s => (
              <div key={s.n} className="cvc-step">
                <div className="cvc-step__num">{s.n}</div>
                <h3 className="cvc-step__title">{s.title}</h3>
                <p className="cvc-step__body">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="cvc-features">
        <div className="cvc-features__inner">
          <div className="cvc-section-label">Why CVC</div>
          <h2 className="cvc-section-title">Everything you need to transfer</h2>
          <div className="cvc-features__grid">
            {[
              {
                icon: (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                  </svg>
                ),
                title: 'GE credit guaranteed',
                body: 'Every course is pre-approved for CSU, UC, or Cal-GETC credit — no guesswork.',
              },
              {
                icon: (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                  </svg>
                ),
                title: 'Flexible scheduling',
                body: 'Hundreds of async courses with no set meeting times — study on your schedule.',
              },
              {
                icon: (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                  </svg>
                ),
                title: 'Free for eligible students',
                body: 'California residents enrolled at a member college pay no additional fees.',
              },
              {
                icon: (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                  </svg>
                ),
                title: 'AI-powered advising',
                body: 'Our AI advisor helps you find the right course for your transfer pathway in seconds.',
              },
            ].map(f => (
              <div key={f.title} className="cvc-feature">
                <div className="cvc-feature__icon">{f.icon}</div>
                <h3 className="cvc-feature__title">{f.title}</h3>
                <p className="cvc-feature__body">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA banner */}
      <section className="cvc-cta">
        <div className="cvc-cta__inner">
          <h2 className="cvc-cta__title">Ready to find your next course?</h2>
          <p className="cvc-cta__sub">Talk to Cali, our AI advisor — it takes 30 seconds.</p>
          <button className="cvc-btn cvc-btn--primary cvc-btn--lg">Get Started Free</button>
        </div>
      </section>

      {/* Footer */}
      <footer className="cvc-footer">
        <div className="cvc-footer__inner">
          <div className="cvc-footer__brand">
            <svg width="28" height="28" viewBox="0 0 44 44" fill="none">
              <circle cx="22" cy="22" r="20" stroke="rgba(255,255,255,0.5)" strokeWidth="2" fill="none"/>
              <path d="M22 8 C14 8 8 14 8 22 C8 30 14 36 22 36 C30 36 36 30 36 22" stroke="rgba(255,255,255,0.5)" strokeWidth="2" fill="none"/>
              <path d="M16 22 Q22 14 28 22 Q22 30 16 22Z" fill="white" opacity="0.6"/>
            </svg>
            <span>California Virtual Campus · California Community Colleges</span>
          </div>
          <div className="cvc-footer__links">
            <a href="#">Privacy</a>
            <a href="#">Accessibility</a>
            <a href="#">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  )
}

// Branching onboarding tree.
// Each node: { id, questionKey, options: [{ labelKey, value, next }] }
// All text is looked up via t(key) at render time so it respects the active language.
const ONBOARDING = {
  student_type: {
    id: 'student_type',
    questionKey: 'ob_student_type_q',
    options: [
      { labelKey: 'ob_student_type_cc', value: 'cc', next: 'visa_status' },
      { labelKey: 'ob_student_type_ucscu', value: 'ucscu', next: 'visa_status_ucscu' },
      { labelKey: 'ob_student_type_other', value: 'other', next: 'exit_other' },
    ],
  },
  visa_status: {
    id: 'visa_status',
    questionKey: 'ob_visa_q',
    options: [
      { labelKey: 'ob_visa_domestic', value: 'domestic', next: 'age_check' },
      { labelKey: 'ob_visa_f1', value: 'f1', next: 'exit_f1' },
    ],
  },
  visa_status_ucscu: {
    id: 'visa_status_ucscu',
    questionKey: 'ob_visa_q',
    options: [
      { labelKey: 'ob_visa_domestic', value: 'domestic', next: 'ucscu_type' },
      { labelKey: 'ob_visa_f1', value: 'f1', next: 'exit_f1' },
    ],
  },
  age_check: {
    id: 'age_check',
    questionKey: 'ob_age_q',
    options: [
      { labelKey: 'ob_age_yes', value: 'yes', next: 'gpa_check' },
      { labelKey: 'ob_age_no', value: 'no', next: 'exit_underage' },
    ],
  },
  gpa_check: {
    id: 'gpa_check',
    questionKey: 'ob_gpa_q',
    options: [
      { labelKey: 'ob_gpa_yes', value: 'yes', next: 'transfer_goal' },
      { labelKey: 'ob_gpa_first', value: 'first_term', next: 'transfer_goal' },
      { labelKey: 'ob_gpa_no', value: 'no', next: 'exit_gpa' },
    ],
  },
  transfer_goal: {
    id: 'transfer_goal',
    questionKey: 'ob_transfer_q',
    options: [
      { labelKey: 'ob_transfer_csu', value: 'csu', next: 'home_college' },
      { labelKey: 'ob_transfer_uc', value: 'uc', next: 'home_college' },
      { labelKey: 'ob_transfer_unsure', value: 'unsure', next: 'home_college' },
    ],
  },
  ucscu_type: {
    id: 'ucscu_type',
    questionKey: 'ob_ucscu_type_q',
    options: [
      { labelKey: 'ob_transfer_csu', value: 'csu', next: 'home_college' },
      { labelKey: 'ob_transfer_uc', value: 'uc', next: 'home_college' },
    ],
  },
  home_college: {
    id: 'home_college',
    questionKey: 'ob_home_q',
    type: 'text_input',
    placeholderKey: 'ob_home_placeholder',
    next: 'done',
  },
}

const FIRST_STEP = 'student_type'

const LANG_INSTRUCTION = {
  es: '[Respond entirely in Spanish / Responde completamente en español]',
  vi: '[Respond entirely in Vietnamese / Trả lời hoàn toàn bằng tiếng Việt]',
  zh: '[Respond entirely in Chinese (Simplified) / 请用简体中文回复]',
  tl: '[Respond entirely in Tagalog / Sagutin nang buo sa Tagalog]',
}

function withLang(text, lang) {
  const hint = LANG_INSTRUCTION[lang]
  return hint ? `${hint}\n${text}` : text
}

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

function profileSummary(answers, t) {
  if (!answers) return []
  const rows = []
  const typeMap = { cc: t('profile_type_cc'), ucscu: t('profile_type_ucscu'), other: t('profile_type_other') }
  if (answers.student_type) rows.push({ label: t('profile_student_type'), value: typeMap[answers.student_type] || answers.student_type })
  const visaVal = answers.visa_status || answers.visa_status_ucscu
  if (visaVal) rows.push({ label: t('profile_visa'), value: visaVal === 'f1' ? t('profile_visa_f1') : t('profile_visa_domestic') })
  if (answers.age_check) rows.push({ label: t('profile_age'), value: answers.age_check === 'yes' ? 'Yes' : 'No' })
  if (answers.gpa_check) {
    const gpaMap = { yes: '2.0+', first_term: 'First term', no: 'Below 2.0' }
    rows.push({ label: t('profile_gpa'), value: gpaMap[answers.gpa_check] || answers.gpa_check })
  }
  if (answers.transfer_goal) {
    const goalMap = { csu: t('profile_goal_csu'), uc: t('profile_goal_uc'), unsure: t('profile_goal_unsure') }
    rows.push({ label: t('profile_transfer_goal'), value: goalMap[answers.transfer_goal] || answers.transfer_goal })
  }
  if (answers.ucscu_type) {
    const typeMap2 = { csu: 'CSU', uc: 'UC' }
    rows.push({ label: t('profile_current_school'), value: typeMap2[answers.ucscu_type] || answers.ucscu_type })
  }
  if (answers.home_college) rows.push({ label: t('profile_home_college'), value: answers.home_college })
  return rows
}

function makeInitialMessages(hasProfile) {
  if (hasProfile) return [{ role: 'assistant', content: null, isWelcome: true }]
  return [
    { role: 'assistant', content: null, isOnboarding: true, stepId: FIRST_STEP },
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
  const [maxDistance, setMaxDistance] = useState(null)
  const [distancePopover, setDistancePopover] = useState(false)
  const distanceRef = useRef(null)
  const [ztcFilter, setZtcFilter] = useState(false)
  const [maxDurationWeeks, setMaxDurationWeeks] = useState(null)
  const [durationPopover, setDurationPopover] = useState(false)
  const durationRef = useRef(null)
  const [region, setRegion] = useState(null)
  const [regionPopover, setRegionPopover] = useState(false)
  const regionRef = useRef(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  function handleClear() {
    clearSession()
    setSavedCourses([])
    setHomeCollege(null)
    setMaxDistance(null)
    setZtcFilter(false)
    setMaxDurationWeeks(null)
    setRegion(null)
    setInput('')
    // Re-prime the backend with profile context on the fresh session
    const profile = loadProfile()
    setMessages([{ role: 'assistant', content: null, isWelcome: true }])
    if (profile) {
      const contextMsg = buildProfileMessage(profile)
      setLoading(true)
      sendMessage(withLang(contextMsg, lang))
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
        const data = await sendMessage(withLang(contextMsg, lang))
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

    setMessages(prev => [...prev, { role: 'user', content: t(option.labelKey) }])

    if (option.next === 'exit_other') {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: null,
        contentKey: 'ob_exit_other',
        isOnboarding: true,
      }])
      setOnboarding({ stepId, done: true, answers: newAnswers })
      saveProfile(newAnswers)
      return
    }

    if (option.next === 'exit_f1') {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: null,
        contentKey: 'ob_exit_f1',
        isOnboarding: true,
      }])
      setOnboarding({ stepId, done: true, answers: newAnswers })
      saveProfile(newAnswers)
      return
    }

    if (option.next === 'exit_underage') {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: null,
        contentKey: 'ob_exit_underage',
        isOnboarding: true,
      }])
      setOnboarding({ stepId, done: true, answers: newAnswers })
      saveProfile(newAnswers)
      return
    }

    if (option.next === 'exit_gpa') {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: null,
        contentKey: 'ob_exit_gpa',
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
        const data = await sendMessage(withLang(contextMsg, lang))
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
        content: null,
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
    sendMessage(withLang(contextMsg, lang))
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
    if (!distancePopover) return
    function close(e) {
      if (!e.target.closest('.distance-chip-wrap')) setDistancePopover(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [distancePopover])

  useEffect(() => {
    if (!durationPopover) return
    function close(e) {
      if (!e.target.closest('.distance-chip-wrap')) setDurationPopover(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [durationPopover])

  useEffect(() => {
    if (!regionPopover) return
    function close(e) {
      if (!e.target.closest('.distance-chip-wrap')) setRegionPopover(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [regionPopover])

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
      const filters = {
        ...(maxDistance != null ? { max_distance_miles: maxDistance } : {}),
        ...(ztcFilter ? { ztc_filter: true } : {}),
        ...(maxDurationWeeks != null ? { max_duration_weeks: maxDurationWeeks } : {}),
        ...(region ? { region } : {}),
      }
      const data = await sendMessage(withLang(text, lang), filters)
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
    const exclusion = homeCollege ? `, excluding ${homeCollege}` : ''
    const text = `Show me all available courses that satisfy ${geTag}${exclusion}`
    // Push a silent chip-search bubble instead of a full user message
    setMessages(prev => [...prev, { role: 'user', content: geTag, isChipSearch: true }])
    setLoading(true)
    try {
      const filters = {
        ...(maxDistance != null ? { max_distance_miles: maxDistance } : {}),
        ...(ztcFilter ? { ztc_filter: true } : {}),
        ...(maxDurationWeeks != null ? { max_duration_weeks: maxDurationWeeks } : {}),
        ...(region ? { region } : {}),
      }
      const data = await sendMessage(withLang(text, lang), filters)
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
            <div className="header__avatar">🌴</div>
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
                  <div className="profile-popover__title">{t('profile_title')}</div>
                  {onboarding.done && profileSummary(onboarding.answers, t).length > 0 ? (
                    <ul className="profile-popover__list">
                      {profileSummary(onboarding.answers, t).map(row => (
                        <li key={row.label} className="profile-popover__row">
                          <span className="profile-popover__label">{row.label}</span>
                          <span className="profile-popover__value">{row.value}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="profile-popover__empty">{t('profile_empty')}</p>
                  )}
                  <button className="profile-popover__reset" onClick={handleResetProfile}>
                    {t('profile_reset')}
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
                    content={msg.isWelcome ? t('welcome') : msg.contentKey ? t(msg.contentKey) : msg.stepId && msg.isOnboarding ? t(ONBOARDING[msg.stepId]?.questionKey) : msg.content}
                    courses={msg.courses}
                    isChipSearch={msg.isChipSearch}
                    onSaveCourse={handleSaveCourse}
                    savedCourses={savedCourses}
                    onSearchGE={handleSearchGE}
                  />
                  {stepForMsg && stepForMsg.type === 'text_input' ? (
                    <form
                      className="quick-replies quick-replies--text"
                      onSubmit={e => { e.preventDefault(); handleOnboardingTextSubmit(msg.stepId, onboardingTextInput) }}
                    >
                      {stepForMsg.id === 'home_college' ? (
                        <CollegeTypeahead
                          value={onboardingTextInput}
                          onChange={setOnboardingTextInput}
                          onSelect={name => {
                            setOnboardingTextInput(name)
                            handleOnboardingTextSubmit(msg.stepId, name)
                          }}
                          placeholder={t(stepForMsg.placeholderKey) || 'Type your college…'}
                          disabled={loading}
                        />
                      ) : (
                        <input
                          className="quick-reply-input"
                          type="text"
                          placeholder={t(stepForMsg.placeholderKey) || 'Type your answer…'}
                          value={onboardingTextInput}
                          onChange={e => setOnboardingTextInput(e.target.value)}
                          disabled={loading}
                          autoFocus
                        />
                      )}
                      <button
                        type="submit"
                        className="quick-reply-btn quick-reply-btn--submit"
                        disabled={loading || !onboardingTextInput.trim()}
                      >
                        {t('ob_continue')}
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
                          {t(opt.labelKey)}
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
            {/* Filter chips row */}
            {(homeCollege || onboarding.answers?.home_college || ztcFilter || maxDurationWeeks != null || region) && (
              <div className="filter-chips-row">
                {/* ZTC chip */}
                <button
                  className={`filter-toggle-chip${ztcFilter ? ' filter-toggle-chip--active' : ''}`}
                  onClick={() => setZtcFilter(f => !f)}
                  title={t('ztc_filter_tooltip')}
                  type="button"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
                  </svg>
                  {t('ztc_filter_chip')}
                </button>

                {/* Duration chip */}
                <div className="distance-chip-wrap" ref={durationRef}>
                  <button
                    className={`distance-chip${maxDurationWeeks != null ? ' distance-chip--active' : ''}`}
                    onClick={() => setDurationPopover(p => !p)}
                    title={t('duration_tooltip')}
                    type="button"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                    </svg>
                    {maxDurationWeeks != null
                      ? t(`duration_${maxDurationWeeks}`)
                      : t('duration_chip_any')}
                    <svg className="distance-chip__caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9"/>
                    </svg>
                  </button>
                  {durationPopover && (
                    <div className="distance-popover">
                      {[6, 8, 10].map(w => (
                        <button
                          key={w}
                          className={`distance-popover__option${maxDurationWeeks === w ? ' distance-popover__option--selected' : ''}`}
                          onClick={() => { setMaxDurationWeeks(w); setDurationPopover(false) }}
                          type="button"
                        >
                          {t(`duration_${w}`)}
                        </button>
                      ))}
                      <button
                        className={`distance-popover__option${maxDurationWeeks == null ? ' distance-popover__option--selected' : ''}`}
                        onClick={() => { setMaxDurationWeeks(null); setDurationPopover(false) }}
                        type="button"
                      >
                        {t('duration_chip_any')}
                      </button>
                    </div>
                  )}
                </div>

                {/* Distance chip — only shown once we know the student's home college */}
                {(homeCollege || onboarding.answers?.home_college) && <div className="distance-chip-wrap" ref={distanceRef}>
              <button
                className={`distance-chip${maxDistance != null ? ' distance-chip--active' : ''}`}
                onClick={() => setDistancePopover(p => !p)}
                title={t('distance_tooltip')}
                type="button"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 0-8 8c0 5.4 7.1 11.5 7.4 11.8a1 1 0 0 0 1.2 0C13 21.5 20 15.4 20 10a8 8 0 0 0-8-8z"/>
                </svg>
                {maxDistance != null
                  ? t('distance_chip').replace('{n}', maxDistance)
                  : t('distance_chip_any')}
                <svg className="distance-chip__caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>
              {distancePopover && (
                <div className="distance-popover">
                  {[25, 50, 100, 200].map(d => (
                    <button
                      key={d}
                      className={`distance-popover__option${maxDistance === d ? ' distance-popover__option--selected' : ''}`}
                      onClick={() => { setMaxDistance(d); setDistancePopover(false) }}
                      type="button"
                    >
                      {t(`distance_${d}`)}
                    </button>
                  ))}
                  <button
                    className={`distance-popover__option${maxDistance == null ? ' distance-popover__option--selected' : ''}`}
                    onClick={() => { setMaxDistance(null); setDistancePopover(false) }}
                    type="button"
                  >
                    {t('distance_no_limit')}
                  </button>
                </div>
              )}
                </div>}

                {/* Region chip — only shown once we know the student's home college */}
                {(homeCollege || onboarding.answers?.home_college) && <div className="distance-chip-wrap" ref={regionRef}>
                  <button
                    className={`distance-chip${region ? ' distance-chip--active' : ''}`}
                    onClick={() => setRegionPopover(p => !p)}
                    title={t('region_tooltip')}
                    type="button"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="3 11 22 2 13 21 11 13 3 11"/>
                    </svg>
                    {region || t('region_chip_any')}
                    <svg className="distance-chip__caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9"/>
                    </svg>
                  </button>
                  {regionPopover && (
                    <div className="distance-popover">
                      {['Bay Area','Los Angeles Metro','San Diego','Central Valley','Central Coast','Inland Empire','Sacramento/Sierra','North State'].map(r => (
                        <button
                          key={r}
                          className={`distance-popover__option${region === r ? ' distance-popover__option--selected' : ''}`}
                          onClick={() => { setRegion(r); setRegionPopover(false) }}
                          type="button"
                        >
                          {r}
                        </button>
                      ))}
                      <button
                        className={`distance-popover__option${region == null ? ' distance-popover__option--selected' : ''}`}
                        onClick={() => { setRegion(null); setRegionPopover(false) }}
                        type="button"
                      >
                        {t('region_chip_any')}
                      </button>
                    </div>
                  )}
                </div>}
              </div>
            )}

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
