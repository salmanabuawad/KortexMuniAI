import { Avatar, Box, IconButton, Tooltip, Typography, useTheme } from "@mui/material";
import DashboardIcon from "@mui/icons-material/GridView";
import ChatIcon from "@mui/icons-material/ChatBubbleOutline";
import SearchIcon from "@mui/icons-material/Search";
import KnowledgeIcon from "@mui/icons-material/MenuBook";
import DocumentsIcon from "@mui/icons-material/Description";
import AgentsIcon from "@mui/icons-material/SmartToy";
import VehiclesIcon from "@mui/icons-material/DirectionsCar";
import AdminIcon from "@mui/icons-material/Settings";
import LogoutIcon from "@mui/icons-material/Logout";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { DisplaySettings } from "../components/DisplaySettings";

const HEADER_H = 52;
const RAIL_W = 72;

interface NavItem {
  to: string;
  labelKey: string;
  icon: JSX.Element;
  later?: boolean;
}

const NAV: NavItem[] = [
  { to: "/dashboard", labelKey: "dashboard.title", icon: <DashboardIcon /> },
  { to: "/chat", labelKey: "nav.chat", icon: <ChatIcon /> },
  { to: "/search", labelKey: "nav.search", icon: <SearchIcon />, later: true },
  { to: "/knowledge", labelKey: "nav.knowledge", icon: <KnowledgeIcon />, later: true },
  { to: "/documents", labelKey: "nav.documents", icon: <DocumentsIcon /> },
  { to: "/agents", labelKey: "nav.agents", icon: <AgentsIcon />, later: true },
  { to: "/vehicles", labelKey: "nav.vehicles", icon: <VehiclesIcon /> },
  { to: "/admin", labelKey: "nav.admin", icon: <AdminIcon /> },
];

export function AppLayout() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const b = theme.brand;

  const initials = (user?.full_name ?? "?")
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <Box sx={{ height: "100vh", display: "flex", flexDirection: "column", bgcolor: b.appBg }}>
      {/* Thin top header */}
      <Box
        sx={{
          height: HEADER_H,
          flexShrink: 0,
          bgcolor: b.headerBg,
          color: b.headerText,
          display: "flex",
          alignItems: "center",
          px: 2,
          gap: 1.5,
          zIndex: 10,
        }}
      >
        <Typography sx={{ fontWeight: 800, fontSize: 20, letterSpacing: 0.3 }}>MuniAI</Typography>
        <Box
          sx={{
            px: 1, py: 0.25, borderRadius: 1, fontSize: 11, fontWeight: 700,
            border: "1px solid rgba(255,255,255,0.4)", opacity: 0.9,
          }}
        >
          {t("chat.localBadge")}
        </Box>
        <Box sx={{ flexGrow: 1 }} />
        <DisplaySettings />
        <LanguageSwitcher inHeader />
        <Tooltip title={user?.full_name ?? ""}>
          <Avatar sx={{ width: 30, height: 30, fontSize: 13, bgcolor: b.accent }}>{initials}</Avatar>
        </Tooltip>
        <Tooltip title={t("common.logout")}>
          <IconButton onClick={logout} size="small" sx={{ color: "inherit" }}>
            <LogoutIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Box sx={{ flexGrow: 1, display: "flex", minHeight: 0 }}>
        {/* Slim icon rail */}
        <Box
          sx={{
            width: RAIL_W,
            flexShrink: 0,
            bgcolor: b.railBg,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            py: 1,
            gap: 0.5,
            overflow: "hidden",
          }}
        >
          {NAV.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Tooltip
                key={item.to}
                title={t(item.labelKey) + (item.later ? ` · ${t("common.comingLater")}` : "")}
                placement="left"
              >
                <Box
                  onClick={() => navigate(item.to)}
                  sx={{
                    position: "relative",
                    width: 52,
                    height: 48,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: 2,
                    cursor: "pointer",
                    color: active ? b.railIndicator : b.railText,
                    opacity: item.later ? 0.55 : 1,
                    bgcolor: active ? b.railActive : "transparent",
                    transition: "background-color .15s, color .15s",
                    "&:hover": { bgcolor: b.railHover, color: "#fff" },
                    "&::before": active
                      ? {
                          content: '""',
                          position: "absolute",
                          insetInlineStart: 0,
                          top: 8,
                          bottom: 8,
                          width: 3,
                          borderRadius: 2,
                          bgcolor: b.railIndicator,
                        }
                      : undefined,
                  }}
                >
                  {item.icon}
                </Box>
              </Tooltip>
            );
          })}
        </Box>

        {/* Content */}
        <Box component="main" sx={{ flexGrow: 1, minWidth: 0, overflow: "auto", bgcolor: b.appBg }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
