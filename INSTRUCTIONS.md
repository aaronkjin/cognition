# Technical Take Home Instructions

For next steps, we'd like for you to complete our technical take home project, shared below.

The goal is to get a sense of how you approach problem-solving, using AI tools, and communicating your work. The task is intentionally open-ended to allow you to showcase your skills.

## 📌 Your Task

You've just gotten off a discovery call with a prospective enterprise client. During the call, the client's VP of Engineering described one of the following pain points. Your job is to build a working automation using Devin + Devin API that solves their problem, then record a short video demo as if you're presenting it back to their team.

Pick one of the client scenarios below, or invent your own if you have a stronger idea.

### Client A: FinServ Co -- "We're drowning in GitHub issues"

"We've got 300+ open issues across our monorepo. Most of them are small-to-medium bugs and feature requests that sit there for months because our senior engineers are heads-down on platform work. We've tried issue triage rotations, but honestly, junior engineers spend more time understanding the issue than fixing it. We need a way to stop the bleeding."

Think about how you'd help this team go from a wall of stale issues to a system where things actually get resolved. You might consider how Devin could scope or triage issues, how a user could decide which ones to act on, and what it would look like for the team to be kept in the loop as work gets done. Get creative with how the automation surfaces information and communicates progress.

### Client B: ShopDirect -- "We have a mass migration we keep deferring"

"We've been saying we'll migrate our frontend to TypeScript for over a year. It's 200+ files, nobody wants to own it, and it never makes it into sprint planning because it doesn't move any product metric. But our type-safety issues are causing real production bugs. We need to just get it done."

Think about how you'd let the team kick off and track a large-scale migration without any one engineer having to own the whole thing. Consider what visibility looks like -- how does the team know what's been done, what's in flight, and what's left? How do results flow back to engineers in a way that doesn't create extra work for them?

### Client C: MedSecure -- "Our security backlog is a compliance risk"

"CodeQL flags dozens of new issues every week and they just pile up. Our security team files them, our engineers ignore them because they're not sprint work. Last audit, we got flagged for it. We need something that can actually make these go away."

The interesting challenge here is closing the loop between the security team that cares about the findings and the engineering team that needs to review the fixes. Think about how you'd go from a pile of scanner output to actual remediated code, and how you'd make sure the right people know what's happening at each step without anyone having to babysit the process.

### Client D: LogiOps -- "Onboarding takes forever because of tech debt"

"We've got feature flags from three years ago still in the codebase. Dead code everywhere. New engineers spend their first two weeks just figuring out what's real and what's abandoned. We need to clean it up but nobody has time."

There's a lot of room here to be creative about what "cleaning it up" looks like as an automated workflow. Think about how you'd help the team discover what needs cleaning, decide what to act on, and get the cleanup done without disrupting active development. Consider how you'd keep the team aware of progress without adding noise.

### Client E: DataStack -- "We can't keep our internal docs or API references up to date"

"Our API docs are six months out of date. Engineers change endpoints and never update the docs. New hires and partner teams constantly ping us asking how things work because the docs are wrong. We know it's a problem but writing docs is the first thing that gets cut from any sprint."

Think about how you'd detect when code and documentation have drifted apart, and what triggers the automation. Consider how Devin determines what the docs should say based on the actual code, and how you handle auto-generated API references versus conceptual docs that need human judgment. How do you surface proposed changes for review without overwhelming engineers with doc PRs?

## ✅ Deliverables

- Your working project (code or hosted demo)
- A 5-10 minute Loom video presenting what you've built to the prospective client you choose. Your video should include:
  - How your automation will address their problem and what makes Devin unique compared to other coding agents
  - What next steps you propose for addressing their immediate problem and for building the longer-term client relationship

## 🔧 Tooling and Access

- You will receive an invite to Devin in a separate email shortly.
- You can find the API documentation here: [https://docs.devin.ai/api-reference/overview](https://docs.devin.ai/api-reference/overview)
- If anything doesn't come through or you need help getting set up, just let us know.

---

## Notes For AI Agents Working In This Repo

- The assignment is intentionally open-ended. Prefer explicit tradeoff reasoning and clear communication artifacts.
- We will NOT be using one of the example client scenarios (A through E) that were given to us in this markdown. Instead, we will create an in-depth scenario using a hypothetical situation with a real Korean company, using the research that we found in @RESEARCH.md as background/context as well as @EXAMPLE_CLIENT_SCENARIO_REFERENCE.md for influence on what a client scenario + solutionizing looks like. Similar to the situation in @EXAMPLE_CLIENT_SCENARIO_REFERENCE.md, we should use a state-of-the-art agentic solution with Devin (e.g. using a parallelized agent swarm).
- Expected output includes both a working automation and a client-facing presentation narrative.
- Any chosen scenario should include:
  - Discovery assumptions
  - Proposed automation workflow
  - Progress visibility/reporting loop
  - Validation/rollout plan
- Keep implementation choices explainable to a VP Engineering audience.

