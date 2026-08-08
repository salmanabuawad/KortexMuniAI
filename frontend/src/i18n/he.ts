import type { Translation } from "./en";

export const he: Translation = {
  app: { name: "MuniAI", tagline: "בינה מלאכותית עירונית פרטית, מקומית תחילה" },
  nav: {
    chat: "צ׳אט",
    search: "חיפוש",
    knowledge: "ידע",
    documents: "מסמכים",
    agents: "סוכנים",
    vehicles: "רכבים",
    admin: "ניהול",
    systemHealth: "בריאות המערכת",
    audit: "יומן ביקורת",
  },
  login: {
    title: "כניסה ל-MuniAI",
    email: "דוא״ל",
    password: "סיסמה",
    submit: "כניסה",
    error: "דוא״ל או סיסמה שגויים.",
    localNotice: "הנתונים שלך נשארים מקומיים. שום מידע עירוני לא נשלח לבינה מלאכותית בענן.",
  },
  chat: {
    newConversation: "שיחה חדשה",
    placeholder: "שאל את MuniAI…",
    send: "שליחה",
    empty: "התחל שיחה. התשובות מגיעות מהבינה המלאכותית המקומית שלך.",
    localBadge: "בינה מקומית",
    externalBadge: "בינה חיצונית — יובאה ע״י המשתמש",
    sources: "מקורות",
    thinking: "חושב…",
    unavailable: "שירות הבינה המקומית אינו זמין. ודא ש-Ollama פועל.",
  },
  common: {
    logout: "יציאה",
    language: "שפה",
    comingLater: "בקרוב",
    loading: "טוען…",
  },
  comingLater: {
    body: "מודול זה נמצא במפת הדרכים של MuniAI ועדיין לא מיושם.",
  },
};
