import { Navigate, Route, Routes } from "react-router-dom";
import { CircularProgress, Box } from "@mui/material";
import { useAuth } from "./auth/AuthContext";
import { LoginPage } from "./pages/LoginPage";
import { AppLayout } from "./layouts/AppLayout";
import { ChatPage } from "./pages/ChatPage";
import { ComingLaterPage } from "./pages/ComingLaterPage";

export function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Box sx={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/search" element={<ComingLaterPage titleKey="nav.search" />} />
        <Route path="/knowledge" element={<ComingLaterPage titleKey="nav.knowledge" />} />
        <Route path="/documents" element={<ComingLaterPage titleKey="nav.documents" />} />
        <Route path="/agents" element={<ComingLaterPage titleKey="nav.agents" />} />
        <Route path="/vehicles" element={<ComingLaterPage titleKey="nav.vehicles" />} />
        <Route path="/admin" element={<ComingLaterPage titleKey="nav.admin" />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Route>
      <Route path="/login" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}
