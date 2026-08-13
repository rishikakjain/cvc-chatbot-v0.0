/**
 * Local dev mock — no AWS credentials needed.
 * Simulates the POST /chat response with realistic CVC chatbot replies.
 *
 * Activated when VITE_API_URL is not set (i.e. running `npm run dev` locally
 * without a .env.local pointing at a real API Gateway URL).
 */

let mockTurn = 0

// Turn 0 = first user message (the welcome is already shown as the initial state)
const MOCK_RESPONSES = [
  {
    reply: "Got it! What are you looking for — a specific subject, or a GE requirement you need to fill? For example: *\"I need a science course with a lab\"* or *\"looking for a math class for CSU transfer.\"*",
  },
  {
    reply: `Here are some options that match:

**1. Introduction to Biology (BIO 101)**
- College: Victor Valley College
- GE tags: CSU: B2, IGETC: 5B, Cal-GETC: 5B
- Units: 4 | Delivery: Online – Asynchronous
- Starts: Aug 25, 2026 | Seats available: 31

**2. General Biology with Lab (BIO 110)**
- College: Cuesta College
- GE tags: CSU: B2, B3 | IGETC: 5B, 5C | Cal-GETC: 5B, 5C
- Units: 4 | Delivery: Online – Asynchronous
- Starts: Aug 18, 2026 | Seats available: 22

**3. Environmental Science (ENVS 101)**
- College: Cuesta College
- GE tags: CSU: B2 | IGETC: 5B | Cal-GETC: 5B
- Units: 3 | Delivery: Online – Asynchronous
- Starts: Aug 25, 2026 | Seats available: 18

> These courses are tagged for Life Science (B2/5B). I can't guarantee they'll satisfy a specific requirement at your home college — articulation varies. Check [assist.org](https://assist.org) or talk to your counselor before enrolling.

Want me to filter by delivery method, start date, or show courses with a lab component?`,
  },
  {
    reply: "Happy to help with that! The lab component is GE area **B3** (CSU Breadth) or **5C** (IGETC/Cal-GETC). Let me filter for courses that include both B2 and B3 so you get a lecture + lab in one course.\n\nWould you prefer async (no fixed meeting times) or sync (live Zoom sessions)?",
  },
  {
    reply: "I don't have a pre-written answer for that, but I'm happy to help. I can find courses, explain GE areas, or answer questions about how CVC enrollment works. What would you like to know?",
  },
]

export async function mockSendMessage(message) {
  // Simulate network delay
  await new Promise(r => setTimeout(r, 800 + Math.random() * 400))

  const response = MOCK_RESPONSES[mockTurn % MOCK_RESPONSES.length]
  mockTurn++

  return {
    reply: response.reply,
    session_id: 'mock-session-001',
    turn_count: mockTurn,
    home_college: mockTurn >= 1 ? 'Pasadena City College' : null,
  }
}
