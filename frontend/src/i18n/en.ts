export const en = {
  app: { name: "MuniAI", tagline: "Private, local-first municipal AI" },
  nav: {
    chat: "Chat",
    search: "Search",
    knowledge: "Knowledge",
    documents: "Documents",
    agents: "Agents",
    vehicles: "Vehicles",
    admin: "Administration",
    systemHealth: "System Health",
    audit: "Audit",
  },
  login: {
    title: "Sign in to MuniAI",
    email: "Email",
    password: "Password",
    submit: "Sign in",
    error: "Invalid email or password.",
    localNotice: "Your data stays local. No municipal data is sent to any cloud AI.",
  },
  chat: {
    newConversation: "New conversation",
    placeholder: "Ask MuniAI…",
    send: "Send",
    empty: "Start a conversation. Answers come from your local AI.",
    localBadge: "LOCAL AI",
    externalBadge: "EXTERNAL AI — USER IMPORTED",
    sources: "Sources",
    thinking: "Thinking…",
    unavailable: "The local AI service is unavailable. Check that Ollama is running.",
  },
  common: {
    logout: "Sign out",
    language: "Language",
    comingLater: "Coming later",
    loading: "Loading…",
  },
  comingLater: {
    body: "This module is part of the MuniAI roadmap and is not implemented yet.",
  },
};

export type Translation = typeof en;
